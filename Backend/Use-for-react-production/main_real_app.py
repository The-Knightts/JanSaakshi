"""
JanSaakshi Production API - Self-Contained & Production Ready
Optimized for React frontend with built-in Sarvam AI integration
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3
import os
import json
import re
import tempfile
import shutil
import zipfile
from datetime import datetime
from dotenv import load_dotenv
from sarvamai import SarvamAI

# ==================== CONFIG ====================
load_dotenv()

# Sarvam AI Configuration
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_DOC_LANGUAGE = os.getenv("SARVAM_DOC_LANGUAGE", "en-IN")

# Initialize Sarvam client
sarvam_client = None
if SARVAM_API_KEY:
    sarvam_client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
else:
    print("⚠️ WARNING: SARVAM_API_KEY not found. AI features will be disabled.")

app = FastAPI(title="JanSaakshi API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "DATA_DB.db"

# ==================== MODELS ====================
class QueryRequest(BaseModel):
    question: str
    prompt: Optional[str] = None
    ward: Optional[str] = None

# ==================== DATABASE INIT ====================
def init_db():
    """Initialize Meeting_data table"""
    conn = sqlite3.connect(DB_PATH)
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

init_db()

# ==================== SARVAM AI FUNCTIONS ====================

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using Sarvam AI OCR"""
    if not sarvam_client:
        raise RuntimeError("Sarvam AI not configured. Set SARVAM_API_KEY in .env")
    
    # Create OCR job
    job = sarvam_client.document_intelligence.create_job(
        language=SARVAM_DOC_LANGUAGE,
        output_format="md"
    )
    
    job.upload_file(pdf_path)
    job.start()
    job.wait_until_complete()
    job.download_output("output.zip")
    
    # Extract markdown from zip
    with zipfile.ZipFile("output.zip", 'r') as zip_ref:
        zip_ref.extractall("output")
    
    for file in os.listdir("output"):
        if file.endswith(".md"):
            with open(os.path.join("output", file), "r", encoding="utf-8") as f:
                return f.read()
    
    raise Exception("No markdown file found in OCR output")


def classify_meeting_data(text: str) -> dict:
    """Extract structured meeting data using Sarvam AI"""
    if not sarvam_client:
        raise RuntimeError("Sarvam AI not configured")
    
    prompt = f"""Extract structured information from this meeting document and return ONLY valid JSON with these fields:
- meeting_id: unique ID (format: "MEET-YYYYMMDD-XXX")
- objective: main purpose (string)
- meeting_date: date in YYYY-MM-DD format (string or null)
- meeting_time: time in HH:MM format (string or null)
- attendees_present: list of attendee names (array of strings)
- ward: ward name/number (string or null)
- venue: meeting location (string or null)
- projects_discussed_list: list of projects (array of strings)

Return ONLY valid JSON, no markdown, no explanations.

DOCUMENT TEXT:
{text[:15000]}"""
    
    response = sarvam_client.chat.completions(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    response_text = response.choices[0].message.content.strip()
    
    # Clean markdown formatting if present
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()
    
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        # Return default structure on parse error
        return {
            "meeting_id": None,
            "objective": None,
            "meeting_date": None,
            "meeting_time": None,
            "attendees_present": [],
            "ward": None,
            "venue": None,
            "projects_discussed_list": []
        }


def generate_summary(meetings: list, custom_prompt: Optional[str] = None) -> str:
    """Generate detailed summary using Sarvam AI"""
    if not sarvam_client:
        return "AI summary unavailable - Sarvam API not configured"
    
    if not meetings:
        return "No meeting data available to summarize"
    
    meetings_text = json.dumps(meetings, indent=2, default=str)
    
    if custom_prompt:
        # Custom prompt mode
        prompt = f"""You are a helpful civic assistant for Mumbai.

User's Question: {custom_prompt}

MEETING DATA:
{meetings_text}

Provide a DETAILED, THOROUGH answer based on the meeting data above.

INSTRUCTIONS:
- Analyze ALL meeting data thoroughly
- Be comprehensive and detailed
- Write in a warm, conversational, friendly tone
- Use clear paragraph breaks
- Base answer ONLY on provided data
- Do NOT use markdown, bullet points, or HTML tags
- Make answer as LONG and DETAILED as needed
- If data contains lists, mention all items"""
    else:
        # Default summary mode
        prompt = f"""You are a helpful civic assistant for Mumbai.

Based on the meeting data below, provide a DETAILED, COMPREHENSIVE summary covering:

1. Meeting Overview: date, location, attendees, objective
2. Key Issues Discussed: all projects, concerns, details
3. Decisions and Actions: budgets, deadlines, responsibilities
4. Impact on Residents: benefits, changes expected

MEETING DATA:
{meetings_text}

INSTRUCTIONS:
- Be THOROUGH - analyze ALL data
- Write in warm, conversational tone
- Use clear paragraph breaks
- Do NOT use markdown, bullet points, asterisks, or HTML
- Make it as DETAILED and LONG as needed"""
    
    response = sarvam_client.chat.completions(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=2500
    )
    
    return response.choices[0].message.content


# ==================== HELPER FUNCTIONS ====================

def search_meetings(question: str, ward_filter: Optional[str] = None) -> list:
    """Smart search for meetings using keywords"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Extract keywords from question
    words = re.findall(r'\b[a-z]{3,}\b', question.lower())
    stopwords = {'what', 'when', 'where', 'who', 'how', 'tell', 'show', 'give', 'about', 'with', 'from', 'planned', 'happening'}
    keywords = [w for w in words if w not in stopwords]
    
    # Build search query
    conditions = []
    values = []
    
    for keyword in keywords[:5]:
        pattern = f"%{keyword}%"
        conditions.append("(LOWER(objective) LIKE ? OR LOWER(venue) LIKE ? OR LOWER(ward) LIKE ? OR LOWER(projects_discussed_list) LIKE ?)")
        values.extend([pattern] * 4)
    
    if ward_filter:
        conditions.append("LOWER(ward) LIKE ?")
        values.append(f"%{ward_filter.lower()}%")
    
    if conditions:
        query = f"SELECT * FROM Meeting_data WHERE {' OR '.join(conditions)} ORDER BY created_at DESC LIMIT 10"
        cursor.execute(query, values)
    else:
        cursor.execute("SELECT * FROM Meeting_data ORDER BY created_at DESC LIMIT 10")
    
    rows = cursor.fetchall()
    conn.close()
    
    # Parse JSON fields
    meetings = []
    for r in rows:
        d = dict(r)
        for k in ("attendees_present", "projects_discussed_list"):
            try:
                d[k] = json.loads(d.get(k) or "[]")
            except:
                d[k] = []
        meetings.append(d)
    
    return meetings


# ==================== API ENDPOINTS ====================

@app.get("/")
def root():
    """Health check"""
    return {
        "status": "JanSaakshi API Running",
        "version": "1.0",
        "sarvam_ai": "configured" if sarvam_client else "not configured"
    }


@app.get("/health")
def health():
    """Health check for monitoring"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Meeting_data")
        count = cursor.fetchone()[0]
        conn.close()
        
        return {
            "status": "healthy",
            "meetings_count": count,
            "sarvam_ai": "ready" if sarvam_client else "disabled"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ask")
def ask_question(req: QueryRequest):
    """
    Main endpoint for React frontend
    Handles any question and returns meeting summaries
    """
    try:
        # Search meetings
        meetings = search_meetings(req.question, req.ward)
        
        if not meetings:
            return {
                "success": False,
                "message": "No meeting data found for your query",
                "summary": "",
                "meetings": [],
                "count": 0
            }
        
        # Generate summary
        try:
            summary = generate_summary(meetings, req.prompt)
        except Exception as e:
            summary = f"Summary generation failed: {str(e)}"
        
        return {
            "success": True,
            "summary": summary,
            "meetings": meetings,
            "count": len(meetings)
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/upload-pdf")
async def upload_meeting_pdf(file: UploadFile = File(...)):
    """
    Upload PDF meeting minutes
    Extracts text, classifies data, stores in DB
    """
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files allowed")
    
    if not sarvam_client:
        raise HTTPException(status_code=503, detail="Sarvam AI not configured. Set SARVAM_API_KEY in .env")
    
    temp_dir = None
    try:
        # Save uploaded file
        temp_dir = tempfile.mkdtemp()
        temp_pdf = os.path.join(temp_dir, file.filename)
        
        with open(temp_pdf, "wb") as f:
            shutil.copyfileobj(file.file, f)
        
        # Extract and classify
        text = extract_text_from_pdf(temp_pdf)
        data = classify_meeting_data(text)
        
        # Generate meeting ID if missing
        if not data.get("meeting_id"):
            data["meeting_id"] = f"MEET-{datetime.now().strftime('%Y%m%d')}-{file.filename[:10].upper().replace('.', '')}"
        
        # Store in database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT OR REPLACE INTO Meeting_data 
        (meeting_id, objective, meeting_date, meeting_time, attendees_present, ward, venue, projects_discussed_list)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get("meeting_id"),
            data.get("objective"),
            data.get("meeting_date"),
            data.get("meeting_time"),
            json.dumps(data.get("attendees_present", [])),
            data.get("ward"),
            data.get("venue"),
            json.dumps(data.get("projects_discussed_list", []))
        ))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "message": "PDF processed successfully",
            "meeting_id": data.get("meeting_id"),
            "data": data
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")
    
    finally:
        # Cleanup
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        for cleanup_path in ["output.zip", "output"]:
            if os.path.exists(cleanup_path):
                try:
                    if os.path.isdir(cleanup_path):
                        shutil.rmtree(cleanup_path)
                    else:
                        os.remove(cleanup_path)
                except:
                    pass


@app.get("/meetings")
def list_meetings(limit: int = 20, ward: Optional[str] = None):
    """
    List all meetings (for React frontend)
    Optional ward filter
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if ward:
            cursor.execute("SELECT * FROM Meeting_data WHERE LOWER(ward) LIKE ? ORDER BY created_at DESC LIMIT ?", 
                         (f"%{ward.lower()}%", limit))
        else:
            cursor.execute("SELECT * FROM Meeting_data ORDER BY created_at DESC LIMIT ?", (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        meetings = []
        for r in rows:
            d = dict(r)
            for k in ("attendees_present", "projects_discussed_list"):
                try:
                    d[k] = json.loads(d.get(k) or "[]")
                except:
                    d[k] = []
            meetings.append(d)
        
        return {"success": True, "meetings": meetings, "count": len(meetings)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/meeting/{meeting_id}")
def get_meeting(meeting_id: str):
    """Get specific meeting by ID"""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM Meeting_data WHERE meeting_id = ?", (meeting_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        meeting = dict(row)
        for k in ("attendees_present", "projects_discussed_list"):
            try:
                meeting[k] = json.loads(meeting.get(k) or "[]")
            except:
                meeting[k] = []
        
        return {"success": True, "meeting": meeting}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== RUN ====================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)







""" 
MADE THIS CODE AS HUMAN AS POSSIBLE

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3, os, json, re, tempfile, shutil, zipfile
from datetime import datetime
from dotenv import load_dotenv
from sarvamai import SarvamAI

# ===== basic setup =====
load_dotenv()
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
SARVAM_DOC_LANGUAGE = os.getenv("SARVAM_DOC_LANGUAGE", "en-IN")
DB_PATH = "DATA_DB.db"

sarvam_client = SarvamAI(api_subscription_key=SARVAM_API_KEY) if SARVAM_API_KEY else None

app = FastAPI(title="JanSaakshi API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== request model =====
class QueryRequest(BaseModel):
    question: str
    prompt: Optional[str] = None
    ward: Optional[str] = None

# ===== db =====
def init_db():
    conn = sqlite3.connect(DB_PATH)
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
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    conn.commit()
    conn.close()

init_db()

# ===== pdf -> text =====
def extract_text_from_pdf(pdf_path: str) -> str:
    if not sarvam_client:
        raise RuntimeError("Sarvam key missing")

    job = sarvam_client.document_intelligence.create_job(language=SARVAM_DOC_LANGUAGE, output_format="md")
    job.upload_file(pdf_path)
    job.start()
    job.wait_until_complete()
    job.download_output("output.zip")

    with zipfile.ZipFile("output.zip", 'r') as z:
        z.extractall("output")

    for f in os.listdir("output"):
        if f.endswith(".md"):
            with open(os.path.join("output", f), encoding="utf-8") as file:
                return file.read()

    raise Exception("no text found")

# ===== text -> structured json =====
def classify_meeting_data(text: str) -> dict:
    if not sarvam_client:
        raise RuntimeError("Sarvam not ready")

    prompt = f"""Return only JSON with meeting details from this text:
{text[:15000]}"""

    res = sarvam_client.chat.completions(messages=[{"role": "user", "content": prompt}], temperature=0.3)
    txt = res.choices[0].message.content.strip()

    txt = txt.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(txt)
    except:
        return {
            "meeting_id": None,
            "objective": None,
            "meeting_date": None,
            "meeting_time": None,
            "attendees_present": [],
            "ward": None,
            "venue": None,
            "projects_discussed_list": []
        }

# ===== ai summary =====
def generate_summary(meetings: list, custom_prompt: Optional[str] = None) -> str:
    if not sarvam_client:
        return "AI not configured"

    data = json.dumps(meetings, indent=2, default=str)

    if custom_prompt:
        prompt = f"Answer based on this civic data:\n{data}\nUser question: {custom_prompt}"
    else:
        prompt = f"Explain these meetings clearly for citizens:\n{data}"

    res = sarvam_client.chat.completions(messages=[{"role": "user", "content": prompt}], temperature=0.6, max_tokens=2500)
    return res.choices[0].message.content

# ===== search =====
def search_meetings(question: str, ward_filter: Optional[str] = None) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    words = re.findall(r'\b[a-z]{3,}\b', question.lower())
    stop = {'what','when','where','who','how','tell','show','give','about','with','from','planned','happening'}
    keys = [w for w in words if w not in stop][:5]

    cond, vals = [], []
    for k in keys:
        p = f"%{k}%"
        cond.append("(LOWER(objective) LIKE ? OR LOWER(venue) LIKE ? OR LOWER(ward) LIKE ? OR LOWER(projects_discussed_list) LIKE ?)")
        vals += [p]*4

    if ward_filter:
        cond.append("LOWER(ward) LIKE ?")
        vals.append(f"%{ward_filter.lower()}%")

    if cond:
        cur.execute(f"SELECT * FROM Meeting_data WHERE {' OR '.join(cond)} ORDER BY created_at DESC LIMIT 10", vals)
    else:
        cur.execute("SELECT * FROM Meeting_data ORDER BY created_at DESC LIMIT 10")

    rows = cur.fetchall()
    conn.close()

    out = []
    for r in rows:
        d = dict(r)
        for k in ("attendees_present","projects_discussed_list"):
            try: d[k]=json.loads(d.get(k) or "[]")
            except: d[k]=[]
        out.append(d)
    return out

# ===== routes =====
@app.get("/")
def root():
    return {"status":"running","sarvam":"on" if sarvam_client else "off"}

@app.post("/ask")
def ask(req: QueryRequest):
    meetings = search_meetings(req.question, req.ward)
    if not meetings:
        return {"success":False,"summary":"","meetings":[],"count":0}

    try:
        summary = generate_summary(meetings, req.prompt)
    except Exception as e:
        summary = str(e)

    return {"success":True,"summary":summary,"meetings":meetings,"count":len(meetings)}

@app.post("/upload-pdf")
async def upload(file: UploadFile = File(...)):
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400,"pdf only")
    if not sarvam_client:
        raise HTTPException(503,"ai missing")

    temp = tempfile.mkdtemp()
    try:
        path = os.path.join(temp,file.filename)
        with open(path,"wb") as f: shutil.copyfileobj(file.file,f)

        text = extract_text_from_pdf(path)
        data = classify_meeting_data(text)

        if not data.get("meeting_id"):
            data["meeting_id"] = f"MEET-{datetime.now().strftime('%Y%m%d')}"

        conn=sqlite3.connect(DB_PATH)
        cur=conn.cursor()
        cur.execute('''INSERT OR REPLACE INTO Meeting_data VALUES(?,?,?,?,?,?,?, ?,CURRENT_TIMESTAMP)''',(
            data.get("meeting_id"),data.get("objective"),data.get("meeting_date"),data.get("meeting_time"),
            json.dumps(data.get("attendees_present",[])),data.get("ward"),data.get("venue"),json.dumps(data.get("projects_discussed_list",[]))
        ))
        conn.commit(); conn.close()

        return {"success":True,"meeting_id":data.get("meeting_id")}
    finally:
        shutil.rmtree(temp,ignore_errors=True)
        for p in ["output","output.zip"]:
            if os.path.exists(p): shutil.rmtree(p,ignore_errors=True) if os.path.isdir(p) else os.remove(p)

@app.get("/meetings")
def list_meetings(limit:int=20, ward:Optional[str]=None):
    conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row; cur=conn.cursor()
    if ward:
        cur.execute("SELECT * FROM Meeting_data WHERE LOWER(ward) LIKE ? ORDER BY created_at DESC LIMIT ?",(f"%{ward.lower()}%",limit))
    else:
        cur.execute("SELECT * FROM Meeting_data ORDER BY created_at DESC LIMIT ?",(limit,))
    rows=cur.fetchall(); conn.close()

    out=[]
    for r in rows:
        d=dict(r)
        for k in ("attendees_present","projects_discussed_list"):
            try:d[k]=json.loads(d.get(k) or "[]")
            except:d[k]=[]
        out.append(d)
    return {"success":True,"meetings":out,"count":len(out)}

@app.get("/meeting/{meeting_id}")
def one(meeting_id:str):
    conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row; cur=conn.cursor()
    cur.execute("SELECT * FROM Meeting_data WHERE meeting_id=?",(meeting_id,))
    r=cur.fetchone(); conn.close()
    if not r: raise HTTPException(404,"not found")

    d=dict(r)
    for k in ("attendees_present","projects_discussed_list"):
        try:d[k]=json.loads(d.get(k) or "[]")
        except:d[k]=[]
    return {"success":True,"meeting":d}

if __name__=="__main__":
    import uvicorn
    uvicorn.run(app,host="0.0.0.0",port=8000)
 """