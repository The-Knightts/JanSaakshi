from fastapi import FastAPI, HTTPException, UploadFile, File
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
import shutil
import tempfile
import time
from datetime import datetime
from ocr_detection import extract_text_from_pdf, classify_meeting_data, generate_summary_from_db, generate_meeting_summary_with_prompt

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

# -------------------- INITIALIZE MEETING_DATA TABLE --------------------
def init_meeting_data_table():
    """Create Meeting_data table if it doesn't exist"""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Meeting_data (
        meeting_id TEXT PRIMARY KEY,
        objective TEXT,
        meeting_date TEXT,
        meeting_time TEXT,
        attendees_present TEXT,
        ward TEXT,
        venue TEXT,
        projects_discussed_list TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        allocated_budget INTEGER,
        estimated_completion TEXT,
        corporator_responsible TEXT,
        timeline TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

# Initialize the table on module load
init_meeting_data_table()

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
                conn = sqlite3.connect(DB_PATH, timeout=30.0)
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


# -------------------- MEETING INTENT + FILTERS --------------------
def is_meeting_query(question: str) -> bool:
    """Return True if the user is likely asking about meetings/minutes rather than projects."""
    q = (question or "").lower()
    meeting_keywords = [
        "meeting",
        "minutes",
        "agenda",
        "standing committee",
        "committee meeting",
        "meeting date",
        "meeting time",
        "attendees",
        "venue",
    ]
    return any(k in q for k in meeting_keywords) or bool(re.search(r"\bMEET-\d{8}-[A-Z0-9]+\b", q.upper()))


def _normalize_date_to_yyyy_mm_dd(s: str) -> Optional[str]:
    """Best-effort date normalization for common formats."""
    if not s:
        return None
    s = s.strip()
    # Already ISO-like
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # dd/mm/yyyy or dd-mm-yyyy
    m = re.search(r"\b(\d{1,2})[\/\-](\d{1,2})[\/\-](\d{2,4})\b", s)
    if m:
        dd = int(m.group(1))
        mm = int(m.group(2))
        yy = int(m.group(3))
        if yy < 100:
            yy = 2000 + yy
        try:
            return datetime(yy, mm, dd).strftime("%Y-%m-%d")
        except Exception:
            return None

    # e.g. 16th December 2025 / 16 December 2025
    m = re.search(
        r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]{3,9})\s+(\d{4})\b",
        s,
        flags=re.IGNORECASE,
    )
    if m:
        dd = int(m.group(1))
        mon = m.group(2).lower()
        yy = int(m.group(3))
        month_map = {
            "jan": 1, "january": 1,
            "feb": 2, "february": 2,
            "mar": 3, "march": 3,
            "apr": 4, "april": 4,
            "may": 5,
            "jun": 6, "june": 6,
            "jul": 7, "july": 7,
            "aug": 8, "august": 8,
            "sep": 9, "sept": 9, "september": 9,
            "oct": 10, "october": 10,
            "nov": 11, "november": 11,
            "dec": 12, "december": 12,
        }
        mm = month_map.get(mon)
        if not mm:
            mm = month_map.get(mon[:3])
        if not mm:
            return None
        try:
            return datetime(yy, mm, dd).strftime("%Y-%m-%d")
        except Exception:
            return None

    return None


def detect_meeting_filters(question: str) -> dict:
    """Detect filters for Meeting_data queries."""
    q = (question or "").strip()
    filters: dict = {}

    # meeting_id
    mid = re.search(r"\bMEET-\d{8}-[A-Z0-9]+\b", q.upper())
    if mid:
        filters["meeting_id"] = mid.group(0)

    # date
    d = _normalize_date_to_yyyy_mm_dd(q)
    if d:
        filters["meeting_date"] = d
    else:
        # try to find a date substring inside the question
        m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", q)
        if m:
            filters["meeting_date"] = m.group(1)
        else:
            m = re.search(r"\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b", q)
            if m:
                nd = _normalize_date_to_yyyy_mm_dd(m.group(1))
                if nd:
                    filters["meeting_date"] = nd

    # ward: reuse existing ward parsing; map ward_no -> ward text filter
    base = detect_filters(q)
    if "ward" in base:
        filters["ward"] = base["ward"]
    if "ward_no" in base:
        filters["ward"] = str(base["ward_no"])

    # venue/objective keywords
    vm = re.search(r"\bvenue[:\s]+(.{3,80}?)(?=(?:,|$))", q, flags=re.IGNORECASE)
    if vm:
        filters["venue"] = vm.group(1).strip()
    om = re.search(r"\bobjective[:\s]+(.{3,120}?)(?=(?:,|$))", q, flags=re.IGNORECASE)
    if om:
        filters["objective"] = om.group(1).strip()

    return filters


def fetch_meetings(filters: dict):
    """Fetch meeting records from Meeting_data with best-effort filtering."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    base_query = "SELECT * FROM Meeting_data"
    conditions = []
    values = []

    if filters.get("meeting_id"):
        conditions.append("meeting_id = ?")
        values.append(filters["meeting_id"])

    if filters.get("meeting_date"):
        conditions.append("meeting_date = ?")
        values.append(filters["meeting_date"])

    if filters.get("ward"):
        conditions.append("LOWER(ward) LIKE ?")
        values.append(f"%{str(filters['ward']).lower()}%")

    if filters.get("venue"):
        conditions.append("LOWER(venue) LIKE ?")
        values.append(f"%{str(filters['venue']).lower()}%")

    if filters.get("objective"):
        conditions.append("LOWER(objective) LIKE ?")
        values.append(f"%{str(filters['objective']).lower()}%")

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    base_query += " ORDER BY created_at DESC LIMIT 20"

    print(f"[DEBUG] Meeting Query: {base_query}, Values: {values}")
    cursor.execute(base_query, values)
    rows = cursor.fetchall()
    conn.close()

    results = []
    for r in rows:
        d = dict(r)
        # parse JSON list fields
        for k in ("attendees_present", "projects_discussed_list"):
            try:
                raw = d.get(k)
                if raw is None:
                    d[k] = []
                elif isinstance(raw, str):
                    d[k] = json.loads(raw) if raw.strip() else []
                else:
                    d[k] = raw
            except Exception:
                d[k] = []
        results.append(d)

    return results


def format_meeting_html(question: str, meetings: list, answer_text: str):
    """Simple HTML wrapper for meeting answers to match existing UI patterns."""
    header = f"<h3 style='color: #d4a574; margin-bottom: 20px;'>🗓️ Meeting Answer</h3>"
    answer_html = f"<p style='background-color: #252525; padding: 15px; border-left: 3px solid #d4a574; margin-bottom: 20px;'>{str(answer_text).replace(chr(10), '<br>')}</p>"
    if not meetings:
        return header + answer_html + f"<p style='color: #ff9999;'>No meeting records found for: <strong>{question}</strong></p>"

    cards = f"<h4 style='color: #d4a574; margin-bottom: 12px;'>Records used ({len(meetings)})</h4>"
    for i, m in enumerate(meetings[:10], 1):
        cards += f"""
        <div style='border: 2px solid #d4a574; padding: 14px; margin-bottom: 14px; border-radius: 6px; background-color: #252525;'>
          <div style='color:#e0e0e0;'><strong style='color:#d4a574;'>{i}. Meeting ID:</strong> {m.get('meeting_id','')}</div>
          <div style='color:#e0e0e0;'><strong style='color:#d4a574;'>Date/Time:</strong> {m.get('meeting_date','') or 'N/A'} {m.get('meeting_time','') or ''}</div>
          <div style='color:#e0e0e0;'><strong style='color:#d4a574;'>Ward:</strong> {m.get('ward','') or 'N/A'}</div>
          <div style='color:#e0e0e0;'><strong style='color:#d4a574;'>Venue:</strong> {m.get('venue','') or 'N/A'}</div>
          <div style='color:#e0e0e0;'><strong style='color:#d4a574;'>Objective:</strong> {m.get('objective','') or 'N/A'}</div>
        </div>
        """

    return header + answer_html + cards

# -------------------- FETCH DATA FROM SQLITE --------------------
def fetch_projects(filters: dict):
    # If no filters were detected, do not return a default set of projects.
    # Previously an empty `filters` resulted in returning the first 10 rows,
    # which made unrelated questions appear to find projects. Return an
    # empty list to avoid false positives and let the caller handle guidance.
    if not filters:
        print("[DEBUG] fetch_projects: no filters provided — returning empty list")
        return []

    conn = sqlite3.connect(DB_PATH, timeout=30.0)
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
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
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
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
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
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
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
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
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
        # Route meeting queries to Meeting_data
        if is_meeting_query(req.question):
            meeting_filters = detect_meeting_filters(req.question)
            # Merge explicit filters from request body (take precedence)
            if getattr(req, 'ward', None):
                meeting_filters['ward'] = req.ward

            records = fetch_meetings(meeting_filters)
            return {
                "query": req.question,
                "source": "Meeting_data",
                "filters_used": meeting_filters,
                "results": records,
                "count": len(records),
            }

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
        # Accept both `prompt` and `input` as the user-provided prompt
        custom_prompt = req.prompt
        if getattr(req, 'input', None) and not custom_prompt:
            custom_prompt = req.input
        
        # Check if this is an explicit meeting query
        is_explicit_meeting = is_meeting_query(req.question)
        
        if is_explicit_meeting:
            # Explicit meeting query - route directly to meetings
            meeting_filters = detect_meeting_filters(req.question)
            if getattr(req, 'ward', None):
                meeting_filters['ward'] = req.ward

            meetings = fetch_meetings(meeting_filters)
            
            if not meetings:
                answer = format_meeting_html(req.question, [], "No matching meeting record found in the database.")
            else:
                try:
                    if custom_prompt:
                        answer_text = generate_meeting_summary_with_prompt(meetings, custom_prompt)
                    else:
                        answer_text = generate_summary_from_db(meetings)
                except Exception as e:
                    answer_text = f"⚠️ Meeting summary generation failed: {str(e)}"
                answer = format_meeting_html(req.question, meetings, answer_text)

            return {
                "source": "Meeting_data",
                "filters_used": meeting_filters,
                "records_found": len(meetings),
                "answer": answer,
                "data": meetings,
            }
        
        # Not an explicit meeting query - search BOTH projects and meetings
        # First, try to find projects
        project_filters = detect_filters(req.question)
        if getattr(req, 'ward', None):
            project_filters['ward'] = req.ward
        if getattr(req, 'contractor', None):
            project_filters['contractor'] = req.contractor
        if getattr(req, 'project_name', None):
            project_filters['project_name'] = req.project_name
        if getattr(req, 'body_text', None):
            project_filters['body_text'] = req.body_text
        
        project_records = fetch_projects(project_filters)
        
        # Also search meetings using the same filters
        meeting_filters = detect_meeting_filters(req.question)
        if getattr(req, 'ward', None):
            meeting_filters['ward'] = req.ward
        
        # Extract keywords from question to search meeting data
        # Look for any meaningful words that might be in meeting data
        question_lower = req.question.lower()
        words = re.findall(r'\b[a-z]{3,}\b', question_lower)
        stopwords = {'what', 'when', 'where', 'who', 'how', 'tell', 'show', 'give', 'about', 'with', 'from', 'planned', 'happening', 'discussed'}
        keywords = [w for w in words if w not in stopwords]
        
        # Search meeting data for these keywords in various fields
        meetings = []
        if keywords:
            conn = sqlite3.connect(DB_PATH, timeout=30.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Build a search query that looks in multiple fields
            search_conditions = []
            search_values = []
            
            for keyword in keywords[:5]:  # Limit to first 5 keywords
                like_pattern = f"%{keyword}%"
                search_conditions.append("(LOWER(objective) LIKE ? OR LOWER(venue) LIKE ? OR LOWER(ward) LIKE ? OR LOWER(projects_discussed_list) LIKE ? OR LOWER(attendees_present) LIKE ?)")
                search_values.extend([like_pattern] * 5)
            
            if search_conditions:
                query = f"SELECT * FROM Meeting_data WHERE {' OR '.join(search_conditions)} ORDER BY created_at DESC LIMIT 10"
                print(f"[DEBUG] Meeting search query: {query[:200]}...")
                cursor.execute(query, search_values)
                rows = cursor.fetchall()
                
                for r in rows:
                    d = dict(r)
                    # Parse JSON list fields
                    for k in ("attendees_present", "projects_discussed_list"):
                        try:
                            raw = d.get(k)
                            if raw is None:
                                d[k] = []
                            elif isinstance(raw, str):
                                d[k] = json.loads(raw) if raw.strip() else []
                            else:
                                d[k] = raw
                        except Exception:
                            d[k] = []
                    meetings.append(d)
            
            conn.close()
        
        # Decide which data source to use
        # Priority: meetings if found, otherwise projects
        if meetings:
            # Found meeting data - use it!
            try:
                if custom_prompt:
                    answer_text = generate_meeting_summary_with_prompt(meetings, custom_prompt)
                else:
                    answer_text = generate_summary_from_db(meetings)
            except Exception as e:
                answer_text = f"⚠️ Meeting summary generation failed: {str(e)}"
            answer = format_meeting_html(req.question, meetings, answer_text)
            
            return {
                "source": "Meeting_data",
                "filters_used": meeting_filters,
                "records_found": len(meetings),
                "answer": answer,
                "data": meetings,
            }
        else:
            # No meetings found - use project data
            answer = explain(req.question, project_records, user_prompt=custom_prompt, user_model=getattr(req, 'model', None))
            data = [dict(r) if hasattr(r, 'keys') else r for r in project_records]
            
            return {
                "source": "PROJECT_DATA",
                "filters_used": project_filters,
                "records_found": len(project_records),
                "answer": answer,
                "data": data
            }

    except Exception as e:
        import traceback
        print(f"ERROR in /ask: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# -------------------- PDF UPLOAD ENDPOINT --------------------
@app.get("/", response_class=HTMLResponse)
def serve_ui():
    """Serve the PDF upload UI - embedded in index.html via FastAPI"""
    # The actual UI is served via index.html, this is a fallback
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>JanSaakshi</title>
        <meta http-equiv="refresh" content="0; url=/static/index.html" />
    </head>
    <body>
        <p>Redirecting to JanSaakshi...</p>
    </body>
    </html>
    """


@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    """Handle PDF upload, extract text, classify data, store in Meeting_data table, and generate summary from database"""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Please upload a PDF file")
    
    temp_dir = None
    conn = None
    try:
        overall_start = time.perf_counter()

        # Save uploaded file to temporary location
        temp_dir = tempfile.mkdtemp()
        temp_pdf_path = os.path.join(temp_dir, file.filename)
        
        with open(temp_pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"Processing PDF: {file.filename}")
        
        # Step 1: Extract text from PDF using OCR
        ocr_start = time.perf_counter()
        extracted_text = extract_text_from_pdf(temp_pdf_path)
        ocr_duration = time.perf_counter() - ocr_start
        print("Text extracted successfully")
        
        # Step 2: Classify meeting data from extracted text
        classify_start = time.perf_counter()
        classified_data = classify_meeting_data(extracted_text)
        classify_duration = time.perf_counter() - classify_start
        print("Meeting data classified successfully")
        
        # Step 3: Store classified data - Create ONE Meeting_data row per PROJECT
        store_start = time.perf_counter()
        
        # Generate base meeting_id if not provided
        if not classified_data.get("meeting_id"):
            from datetime import datetime
            base_meeting_id = f"MEET-{datetime.now().strftime('%Y%m%d')}-{file.filename[:10].upper().replace('.', '')}"
        else:
            base_meeting_id = classified_data.get("meeting_id")
        
        # Convert attendees list to JSON string
        attendees_json = json.dumps(classified_data.get("attendees_present", []) or [])
        
        # Extract projects
        projects = classified_data.get("projects", [])
        
        # Use connection with timeout to prevent locking
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        cursor = conn.cursor()
        
        # Insert ONE row per project into Meeting_data
        projects_inserted = 0
        for idx, project in enumerate(projects, 1):
            if not project.get("project_name"):
                continue
            
            # Create unique meeting_id for each project
            meeting_id = f"{base_meeting_id}-P{idx}"
            
            # Create projects_discussed_list with just this project
            projects_json = json.dumps([project.get("project_name")])
            
            cursor.execute('''
            INSERT OR REPLACE INTO Meeting_data 
            (meeting_id, objective, meeting_date, meeting_time, attendees_present, ward, venue, projects_discussed_list,
             allocated_budget, estimated_completion, corporator_responsible, timeline)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                meeting_id,
                classified_data.get("objective"),
                classified_data.get("meeting_date"),
                classified_data.get("meeting_time"),
                attendees_json,
                classified_data.get("ward"),
                classified_data.get("venue"),
                projects_json,
                project.get("allocated_budget"),
                project.get("estimated_completion"),
                classified_data.get("corporator_responsible"),
                project.get("timeline")
            ))
            projects_inserted += 1
        
        conn.commit()
        conn.close()
        conn = None
        store_duration = time.perf_counter() - store_start
        print(f"Inserted {projects_inserted} project records into Meeting_data table")
        
        # Use the base meeting_id for summary
        meeting_id = base_meeting_id
        
        # Step 4: Generate summary from database
        summary_start = time.perf_counter()
        # Fetch ALL project records for this meeting (all rows with meeting_id starting with base_meeting_id)
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Meeting_data WHERE meeting_id LIKE ?", (f"{meeting_id}%",))
        meeting_records = cursor.fetchall()
        conn.close()
        conn = None
        
        if meeting_records:
            # Convert rows to dicts and parse JSON fields
            meeting_dicts = []
            for record in meeting_records:
                meeting_dict = dict(record)
                meeting_dict["attendees_present"] = json.loads(meeting_dict.get("attendees_present", "[]"))
                meeting_dict["projects_discussed_list"] = json.loads(meeting_dict.get("projects_discussed_list", "[]"))
                meeting_dicts.append(meeting_dict)
            summary = generate_summary_from_db(meeting_dicts)
        else:
            summary = "Meeting data stored but could not be retrieved for summary generation."
        
        summary_duration = time.perf_counter() - summary_start
        total_duration = time.perf_counter() - overall_start
        
        return {
            "status": "success",
            "filename": file.filename,
            "meeting_id": meeting_id,
            "classified_data": classified_data,
            "summary": summary,
            "timings": {
                "ocr_seconds": round(ocr_duration, 2),
                "classification_seconds": round(classify_duration, 2),
                "storage_seconds": round(store_duration, 2),
                "summary_seconds": round(summary_duration, 2),
                "total_seconds": round(total_duration, 2),
            },
        }
    
    except Exception as e:
        print(f"Error processing PDF: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")
    
    finally:
        # Ensure database connection is closed
        if conn:
            try:
                conn.close()
            except:
                pass
        
        # Clean up temporary files
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Clean up OCR output files
        if os.path.exists("output.zip"):
            try:
                os.remove("output.zip")
            except:
                pass
        if os.path.exists("output"):
            try:
                shutil.rmtree("output")
            except:
                pass