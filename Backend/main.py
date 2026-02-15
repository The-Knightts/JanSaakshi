from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import sqlite3
import os
import json
from dotenv import load_dotenv
from mistralai import Mistral

# -------------------- CONFIG --------------------
load_dotenv()
API_KEY = os.getenv("MISTRAL_API_KEY")

# Initialize Mistral client only if API key exists
client = None
if API_KEY:
    try:
        client = Mistral(api_key=API_KEY)
    except Exception as e:
        print(f"⚠️  Warning: Could not initialize Mistral: {e}")
        client = None
else:
    print("⚠️  Warning: MISTRAL_API_KEY not found in .env file")

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

def explain(question, records):
    """Generate AI explanation of project records"""
    if not records:
        return "<p style='color: #ff9999;'>📭 No official government project record found related to your question.</p>"

    try:
        # Convert records to plain dicts if needed
        plain_records = []
        for r in records:
            if hasattr(r, 'keys'):
                plain_records.append(dict(r))
            else:
                plain_records.append(r)
        
        # Try to use Mistral for better explanation
        if client:
            try:
                # Format records nicely for the prompt
                formatted_records = json.dumps(plain_records, indent=2, default=str)
                
                prompt = f"""You are a helpful government civic assistant in Mumbai who provides detailed, informative responses.

Question: {question}

Project Data:
{formatted_records}

Provide a DETAILED and COMPREHENSIVE summary in simple Indian English explaining:

1. **Project Overview** - Describe what each project is about in detail
2. **Current Status** - Explain what stage each project is at
3. **Budget Details** - How much money has been allocated
4. **Timeline** - When each project is expected to be completed
5. **Responsibility** - Who is overseeing and responsible for each project
6. **Impact** - What benefits will these projects bring to the community

Write in 3-4 paragraphs with detailed information about each project. Be specific and informative.
Do NOT invent information - only use the data provided.
Write as if explaining to a local resident who wants to understand what's happening in their ward."""

                response = client.chat.complete(
                    model="mistral-small",
                    messages=[{"role": "user", "content": prompt}]
                )
                
                # Return as HTML with nice formatting
                answer = response.choices[0].message.content
                return f"<h3 style='color: #d4a574; margin-bottom: 20px;'>🤖 AI Analysis</h3><p style='background-color: #252525; padding: 15px; border-left: 3px solid #d4a574; margin-bottom: 20px;'>{answer.replace(chr(10), '<br>')}</p>" + format_html_response(question, plain_records)
            
            except Exception as e:
                print(f"Mistral error: {e}")
                import traceback
                traceback.print_exc()
                # Fallback to just formatted records
                return format_html_response(question, plain_records)
        else:
            # No Mistral, just format the records
            return format_html_response(question, plain_records)
    
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
        records = fetch_projects(filters)
        answer = explain(req.question, records)

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