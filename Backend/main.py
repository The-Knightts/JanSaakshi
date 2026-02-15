from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import sqlite3
import os
import json
from dotenv import load_dotenv
import ast
import requests
import re

# -------------------- CONFIG --------------------
load_dotenv()
# Prefer SARVAM API config
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
# Accept either SARVAM_API_URL or SARVAM_BASE_URL
SARVAM_API_URL = os.getenv("SARVAM_API_URL") or os.getenv("SARVAM_BASE_URL")
SARVAM_MODEL = os.getenv("SARVAM_MODEL")

# Choose provider (SARVAM only)
chosen_provider = None
chosen_api_key = None
chosen_api_url = None
chosen_model_default = None

if SARVAM_API_KEY and SARVAM_API_URL:
    chosen_provider = "SARVAM"
    chosen_api_key = SARVAM_API_KEY
    chosen_api_url = SARVAM_API_URL
    chosen_model_default = SARVAM_MODEL
else:
    print("⚠️  Warning: SARVAM API credentials not found in .env. AI calls will be disabled until configured.")

app = FastAPI(title="JanSaakshi Civic Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "DATA_DB.db"

# -------------------- REQUEST MODEL --------------------
class Question(BaseModel):
    question: str
    prompt: Optional[str] = None
    # `input` is an alias some frontends use for the prompt text
    input: Optional[str] = None
    model: Optional[str] = None
    # Optional explicit filters from the UI
    ward: Optional[str] = None
    contractor: Optional[str] = None
    project_name: Optional[str] = None
    body_text: Optional[str] = None

# -------------------- SIMPLE INTENT DETECTOR --------------------
def detect_filters(question: str):
    q = question.lower().strip()
    filters = {}

    # Try to detect plain ward number first (e.g., "37" or "45")
    try:
        ward_num = int(q)
        if 1 <= ward_num <= 70:
            filters["ward_no"] = ward_num
            return filters
    except ValueError:
        pass

    # ward number detection (check from high to low to avoid matching 3 in 37)
    for i in range(69, 0, -1):
        if f"ward {i}" in q or f"ward no {i}" in q or f"ward{i}" in q:
            filters["ward_no"] = i
            break

    # ward name detection (e.g., "ward Akurli" or "ward: Akurli")
    m = re.search(r"ward(?:\s*no)?[:\s]+([A-Za-z][A-Za-z\s&\-'']{1,40}?)(?=(?:\s+by\b|\s+about\b|\s+in\b|,|$))", question, flags=re.IGNORECASE)
    if m and 'ward_no' not in filters:
        wn = m.group(1).strip()
        # avoid capturing numeric ward matched above
        if not wn.isdigit():
            filters["ward"] = wn

    # Generic location detection: catch phrases like "in Akurli", "at Akurli".
    # This handles user queries that ask about a place without the word 'ward'.
    if 'ward' not in filters and 'ward_no' not in filters:
        loc = re.search(r"\b(?:in|at|around|near)\s+([A-Za-z][A-Za-z\s&\-']{1,40})", question, flags=re.IGNORECASE)
        if loc:
            place = loc.group(1).strip()
            if not place.isdigit():
                filters['ward'] = place

    # project keyword detection - check for all keywords
    keywords = {
        "road": "Road",
        "drain": "Drain", 
        "water": "Water",
        "repair": "Repair",
        "construction": "Construction",
        "park": "Park",
        "light": "Light",
        "sidewalk": "Sidewalk",
        "school": "School",
        "bus": "Bus",
        "waste": "Waste",
        "toilet": "Toilet",
        "traffic": "Traffic",
        "garden": "Garden",
        "storm": "Storm"
    }
    
    for k, _ in keywords.items():
        if k in q:
            filters["project_name"] = k
            break

    # If no filters found yet, try DB-backed keyword matching: check n-grams
    # (longer phrases first) then shorter tokens against project_name,
    # body_text, contractor, and ward. This lets arbitrary user keywords
    # (e.g., "gym", "open gym", "toilet renovation") match DB rows.
    if not filters:
        stopwords = {"what","is","happening","in","the","a","an","of","for","on","show","projects","about","please","give","me","here","there","near"}
        # tokenization keeping alphanumerics and simple punctuation removed
        words = [w for w in re.findall(r"\b[\w&'-]+\b", q.lower())]
        words = [w for w in words if w and w not in stopwords]
        if words:
            # build n-grams from longest to shortest (max 3 words)
            max_n = min(3, len(words))
            found = False
            conn = None
            try:
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                for n in range(max_n, 0, -1):
                    if found:
                        break
                    for i in range(0, len(words) - n + 1):
                        phrase = " ".join(words[i : i + n])
                        like = f"%{phrase}%"
                        # check columns in preferred order
                        cursor.execute("SELECT COUNT(*) FROM PROJECT_DATA WHERE LOWER(project_name) LIKE ?", (like,))
                        if cursor.fetchone()[0] > 0:
                            filters["project_name"] = phrase
                            found = True
                            break
                        cursor.execute("SELECT COUNT(*) FROM PROJECT_DATA WHERE LOWER(body_text) LIKE ?", (like,))
                        if cursor.fetchone()[0] > 0:
                            filters["body_text"] = phrase
                            found = True
                            break
                        cursor.execute("SELECT COUNT(*) FROM PROJECT_DATA WHERE LOWER(contractor) LIKE ?", (like,))
                        if cursor.fetchone()[0] > 0:
                            filters["contractor"] = phrase
                            found = True
                            break
                        cursor.execute("SELECT COUNT(*) FROM PROJECT_DATA WHERE LOWER(ward) LIKE ?", (like,))
                        if cursor.fetchone()[0] > 0:
                            filters["ward"] = phrase
                            found = True
                            break
                    if found:
                        break
            except Exception:
                pass
            finally:
                try:
                    if conn:
                        conn.close()
                except Exception:
                    pass

    # explicit project name provided like "project: Road Repair" or quoted phrase
    pm = re.search(r"project(?: name)?[:\s]+(.{3,120}?)(?=(?:\s+in\b|\s+by\b|\s+about\b|,|$))", question, flags=re.IGNORECASE)
    if pm:
        filters["project_name"] = pm.group(1).strip()

    # contractor detection: look for 'contractor' or 'by <Name>' patterns
    cm = re.search(r"contractor[:\s]+([A-Za-z0-9 &.\-']{3,60}?)(?=(?:\s+in\b|\s+ward\b|\s+about\b|,|$))", question, flags=re.IGNORECASE)
    if cm:
        filters["contractor"] = cm.group(1).strip()
    else:
        bym = re.search(r"\bby\s+([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+){0,3})(?=(?:\s+about\b|,|$))", question)
        if bym:
            filters["contractor"] = bym.group(1).strip()

    # body text / details search: "about drainage", "details: ..."
    bm = re.search(r"(?:about|details?|regarding)[:\s]+([\w\s\-,]{3,120})", question, flags=re.IGNORECASE)
    if bm:
        filters["body_text"] = bm.group(1).strip()
    
    # status detection
    if "delayed" in q:
        filters["status"] = "Delayed"
    elif "pending" in q:
        filters["status"] = "Pending"
    elif "progress" in q or "ongoing" in q or "in progress" in q:
        filters["status"] = "In Progress"

    return filters

# -------------------- FETCH DATA FROM SQLITE --------------------
def fetch_projects(filters: dict):
    # If no filters were detected, do not return a default set of projects.
    # Previously an empty `filters` resulted in returning the first 10 rows,
    # which made unrelated questions appear to find projects. Return an
    # empty list to avoid false positives and let the caller handle guidance.
    if not filters:
        print("[DEBUG] fetch_projects: no filters provided — returning empty list")
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    base_query = "SELECT * FROM PROJECT_DATA"
    conditions = []
    values = []

    if "ward_no" in filters:
        conditions.append("ward_no = ?")
        values.append(filters["ward_no"])

    if "project_name" in filters:
        conditions.append("LOWER(project_name) LIKE ?")
        values.append(f"%{filters['project_name']}%")
    # match ward name (string match on ward column)
    if "ward" in filters:
        conditions.append("LOWER(ward) LIKE ?")
        values.append(f"%{str(filters['ward']).lower()}%")
    # contractor name match
    if "contractor" in filters:
        conditions.append("LOWER(contractor) LIKE ?")
        values.append(f"%{str(filters['contractor']).lower()}%")
    # body_text / details search
    if "body_text" in filters:
        conditions.append("LOWER(body_text) LIKE ?")
        values.append(f"%{str(filters['body_text']).lower()}%")
    
    if "status" in filters:
        conditions.append("status = ?")
        values.append(filters["status"])

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    base_query += " LIMIT 10"

    print(f"[DEBUG] Query: {base_query}, Values: {values}")
    cursor.execute(base_query, values)
    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]

# -------------------- AI EXPLAINER --------------------
def format_html_response(question, records):
    """Format records as nice HTML cards"""
    if not records:
        return "<p style='color: #ff9999;'>No official government project record found related to your question.</p>"
    
    html = f"<h3 style='color: #d4a574; margin-bottom: 20px;'>📋 Projects found for: <strong>{question}</strong></h3><div style='margin-top: 20px;'>"
    
    for i, record in enumerate(records, 1):
        # Handle both dict and string records
        if isinstance(record, dict):
            proj_name = record.get("project_name", "Unknown Project")
            ward = record.get("ward_no", "N/A")
            budget = record.get("budget", "N/A")
            deadline = record.get("deadline", "N/A")
            status = record.get("status", "Pending")
            description = record.get("body_text", "")
            # If AI provided an enhanced detail, append it under details
            ai_extra = record.get("ai_detail")
            if ai_extra:
                if description:
                    description = f"{description}<br><br><strong style='color: #d4a574;'>AI-enhanced details:</strong> {ai_extra}"
                else:
                    description = f"<strong style='color: #d4a574;'>AI-enhanced details:</strong> {ai_extra}"
            responsible = record.get("responsible_person", "N/A")
        else:
            proj_name = str(record).split("'")[3] if "'" in str(record) else "Unknown"
            ward = "N/A"
            budget = "N/A"
            deadline = "N/A"
            status = "Pending"
            description = ""
            responsible = "N/A"
        
        # Color code status
        if status.lower() == "delayed" or "overdue" in str(status).lower():
            status_color = "#ff6b6b"
            status_icon = "⚠️"
        elif status.lower() == "in progress" or "ongoing" in str(status).lower():
            status_color = "#ffd93d"
            status_icon = "🔨"
        else:
            status_color = "#a8dadc"
            status_icon = "📅"
        
        html += f"""
        <div style='border: 2px solid #d4a574; padding: 18px; margin-bottom: 18px; border-radius: 6px; background-color: #252525;'>
            <h4 style='color: #d4a574; margin: 0 0 15px 0; font-size: 17px;'>{i}. {proj_name}</h4>
            <div style='display: grid; grid-template-columns: 1fr 1fr; gap: 15px;'>
                <p style='margin: 5px 0;'><strong style='color: #d4a574;'>Ward:</strong> <span style='font-weight: bold;'>{ward}</span></p>
                <p style='margin: 5px 0;'><strong style='color: #d4a574;'>Status:</strong> <span style='color: {status_color}; font-weight: bold;'>{status_icon} {status}</span></p>
                <p style='margin: 5px 0;'><strong style='color: #d4a574;'>Budget:</strong> ₹{budget}</p>
                <p style='margin: 5px 0;'><strong style='color: #d4a574;'>Deadline:</strong> {deadline}</p>
                <p style='margin: 5px 0; grid-column: 1/-1;'><strong style='color: #d4a574;'>Responsible:</strong> {responsible}</p>
            </div>
            <p style='margin: 12px 0 0 0; padding-top: 12px; border-top: 1px solid #444; color: #e0e0e0;'><strong style='color: #d4a574;'>Details:</strong> {description}</p>
        </div>
        """
    
    html += "</div>"
    return html

def explain(question, records, user_prompt: Optional[str] = None, user_model: Optional[str] = None):
    """Generate AI explanation of project records.

    If SARVAM credentials are configured, call the external API.
    Otherwise produce a helpful mock long-form explanation so the UI can be tested.
    """
    # If there are no DB records but the user supplied a custom prompt,
    # allow the AI call to proceed (the prompt may not require DB data).
    if not records and not user_prompt:
        return "<p style='color: #ff9999;'>📭 No official government project record found related to your question.</p>"

    try:
        # Normalize records to plain dicts
        plain_records = [dict(r) if hasattr(r, 'keys') else r for r in records]

        # Offline/mock generation removed: AI explanations require a configured SARVAM API.

        # Do not augment records locally; present original DB fields only.

        # If no provider configured, return guidance
        if not chosen_provider:
            return "<p style='color: #ff9999;'>⚠️ AI service not configured. Set SARVAM_API_KEY and SARVAM_API_URL in .env to enable online answers.</p>"

        try:
            formatted_records = json.dumps(plain_records, indent=2, default=str)

            # If user provided a custom prompt, prefer it (but still attach project data)
            if user_prompt:
                prompt_text = f"{user_prompt}\n\nProject Data:\n{formatted_records}"
            else:
                prompt_text = f"""You are a helpful civic assistant for Mumbai.

Question: {question}

Project Data:
{formatted_records}

Provide a detailed, factual, and helpful summary for a local resident. Do NOT invent facts — only use the data provided. Explain project overviews, current status, budgets, timelines, responsibilities, and local impact. Keep language simple and concrete.
"""

            # Build payload: some providers expect chat-style `messages`,
            # while others accept a `prompt` field. Detect chat endpoints by URL.
            chosen_model = user_model or chosen_model_default
            is_chat_endpoint = False
            if chosen_api_url and ("/chat" in chosen_api_url or "chat/completions" in chosen_api_url):
                is_chat_endpoint = True

                if is_chat_endpoint:
                    # Ask the model to reply using natural plain text only.
                    messages = [
                        {"role": "system", "content": "You are a helpful civic assistant for Mumbai. Use ONLY the provided project data. Respond in natural, plain text only — do NOT return JSON, dictionaries, or code blocks. Keep answers concise, in paragraphs."},
                        {"role": "user", "content": prompt_text}
                    ]
                payload = {"messages": messages, "max_tokens": 800}
                if chosen_model:
                    payload["model"] = chosen_model
            else:
                payload = {"prompt": prompt_text, "max_tokens": 800}
                if chosen_model:
                    payload["model"] = chosen_model

            headers = {"Authorization": f"Bearer {chosen_api_key}", "Content-Type": "application/json"}

            # Chat-style endpoints usually require an explicit model identifier
            if is_chat_endpoint and not chosen_model:
                return f"<p style='color: #ff9999;'>⚠️ Chat endpoint requires a `model`. Set {chosen_provider}_MODEL in .env or pass `model` in the request.</p>" + format_html_response(question, plain_records)

            # Use the selected provider's URL/key
            resp = requests.post(chosen_api_url, headers=headers, json=payload, timeout=25)
            try:
                resp.raise_for_status()
            except requests.exceptions.HTTPError as http_e:
                # Log and return provider error body to help debugging
                body = None
                try:
                    body = resp.text
                except Exception:
                    body = str(http_e)
                print(f"{chosen_provider} HTTP error:", resp.status_code, body)
                return f"<p style='color: #ff9999;'>⚠️ AI service call failed: {resp.status_code} {body}</p>" + format_html_response(question, plain_records)

            jr = resp.json()

            # Try common response shapes and prefer textual fields; handle nested chat shapes
            answer_text = None
            if isinstance(jr, dict):
                if jr.get("text"):
                    answer_text = jr.get("text")
                elif jr.get("output"):
                    answer_text = jr.get("output")
                elif "choices" in jr and isinstance(jr["choices"], list) and jr["choices"]:
                    c = jr["choices"][0]
                    if isinstance(c, dict):
                        # Prefer message.content (chat-style)
                        msg = c.get("message")
                        if isinstance(msg, dict) and msg.get("content"):
                            answer_text = msg.get("content")
                        else:
                            # fallback to common fields inside choice
                            answer_text = c.get("text") or c.get("output") or c.get("content") or c.get("message")

            # If answer_text is still a dict (some providers return nested dict), try to extract 'content'
            if isinstance(answer_text, dict):
                answer_text = answer_text.get("content") or answer_text.get("text") or str(answer_text)

            # If model returned a string that looks like a Python dict, try to parse it and extract 'content'
            if isinstance(answer_text, str):
                s = answer_text.strip()
                if (s.startswith("{") and ("'content'" in s or '"content"' in s)) or s.startswith("{'content'"):
                    try:
                        parsed = ast.literal_eval(s)
                        if isinstance(parsed, dict) and ("content" in parsed or 'text' in parsed):
                            answer_text = parsed.get("content") or parsed.get("text") or str(parsed)
                    except Exception:
                        pass

            if not answer_text:
                # If still nothing usable, log the response and return an error note
                print(f"Unexpected {chosen_provider} response shape:", jr)
                answer_text = f"⚠️ {chosen_provider} returned an unexpected response format. Check server logs for details."

            # Clean up simple markdown bold markers for natural text
            if isinstance(answer_text, str):
                answer_text = answer_text.replace('**', '')

            answer_html = f"<h3 style='color: #d4a574; margin-bottom: 20px;'>🤖 {chosen_provider} Analysis</h3><p style='background-color: #252525; padding: 15px; border-left: 3px solid #d4a574; margin-bottom: 20px;'>{str(answer_text).replace(chr(10), '<br>')}</p>"
            return answer_html + format_html_response(question, plain_records)

        except Exception as e:
            print(f"{chosen_provider} call error: {e}")
            import traceback
            traceback.print_exc()
            # Return a clear, user-visible error when the external AI call fails
            return f"<p style='color: #ff9999;'>⚠️ AI service call failed: {str(e)}</p>" + format_html_response(question, plain_records)

    except Exception as e:
        print(f"Error in explain(): {e}")
        import traceback
        traceback.print_exc()
        return f"<p style='color: #ff9999;'>⚠️ Error processing your query: {str(e)}</p>"

# -------------------- ROUTES --------------------
@app.get("/", response_class=HTMLResponse)
def home():
    """Serve the main UI"""
    ui_file_path = os.path.join(os.path.dirname(__file__), "index.html")
    if os.path.exists(ui_file_path):
        with open(ui_file_path, 'r', encoding='utf-8') as f:
            return f.read()
    return {"status": "JanSaakshi Running"}

@app.get("/test")
def serve_test_page():
    """Serve the testing.html file"""
    test_file_path = os.path.join(os.path.dirname(__file__), "testing.html")
    if os.path.exists(test_file_path):
        with open(test_file_path, 'r') as f:
            return HTMLResponse(content=f.read())
    return {"error": "testing.html not found"}

@app.get("/home")
def get_home():
    """Home/dashboard endpoint"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as total_projects FROM PROJECT_DATA")
        total = cursor.fetchone()["total_projects"]
        
        cursor.execute("SELECT COUNT(*) as delayed FROM PROJECT_DATA WHERE status = 'Delayed'")
        delayed = cursor.fetchone()["delayed"]
        
        conn.close()
        
        return {
            "status": "ok",
            "total_projects": total,
            "delayed_projects": delayed,
            "message": "JanSaakshi Civic Transparency Dashboard"
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/ward/{ward_no}")
def get_ward(ward_no: int):
    """Get projects for a specific ward"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM PROJECT_DATA WHERE ward_no = ? LIMIT 10", (ward_no,))
        rows = cursor.fetchall()
        conn.close()
        
        return {
            "ward_no": ward_no,
            "projects": [dict(row) for row in rows],
            "count": len(rows)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/backend/{project_id}")
def get_project(project_id: int):
    """Get details of a specific project"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM PROJECT_DATA WHERE id = ?", (project_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {"error": "Project not found"}
        
        return {"project": dict(row)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/backend/delayed")
def get_delayed():
    """Get all delayed projects"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM PROJECT_DATA WHERE status = 'Delayed' LIMIT 20")
        rows = cursor.fetchall()
        conn.close()
        
        return {
            "status": "delayed",
            "projects": [dict(row) for row in rows],
            "count": len(rows)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
def search_projects(req: Question):
    """Search projects by question (uses AI filtering)"""
    try:
        filters = detect_filters(req.question)
        # Accept both `prompt` and `input` as the user-provided prompt
        if getattr(req, 'input', None) and not req.prompt:
            req.prompt = req.input
        # Merge explicit filters from request body (take precedence)
        if getattr(req, 'ward', None):
            filters['ward'] = req.ward
        if getattr(req, 'contractor', None):
            filters['contractor'] = req.contractor
        if getattr(req, 'project_name', None):
            filters['project_name'] = req.project_name
        if getattr(req, 'body_text', None):
            filters['body_text'] = req.body_text
        records = fetch_projects(filters)
        
        # Convert records to plain dicts for JSON serialization
        data = [dict(r) if hasattr(r, 'keys') else r for r in records]
        
        return {
            "query": req.question,
            "filters_used": filters,
            "results": data,
            "count": len(data)
        }
    except Exception as e:
        import traceback
        print(f"ERROR in /search: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ask")
def ask_ai(req: Question):
    """Main AI-powered question answering endpoint"""
    try:
        filters = detect_filters(req.question)
        # Accept both `prompt` and `input` as the user-provided prompt
        if getattr(req, 'input', None) and not req.prompt:
            req.prompt = req.input
        # Merge explicit filters from request body (take precedence)
        if getattr(req, 'ward', None):
            filters['ward'] = req.ward
        if getattr(req, 'contractor', None):
            filters['contractor'] = req.contractor
        if getattr(req, 'project_name', None):
            filters['project_name'] = req.project_name
        if getattr(req, 'body_text', None):
            filters['body_text'] = req.body_text
        records = fetch_projects(filters)
        answer = explain(req.question, records, user_prompt=req.prompt, user_model=getattr(req, 'model', None))

        # Convert records to plain dicts for JSON serialization
        data = [dict(r) if hasattr(r, 'keys') else r for r in records]

        return {
            "filters_used": filters,
            "records_found": len(records),
            "answer": answer,
            "data": data
        }

    except Exception as e:
        import traceback
        print(f"ERROR in /ask: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))