import os
import zipfile
import json
from sarvamai import SarvamAI
from dotenv import load_dotenv

# =========================
# CONFIG
# =========================
load_dotenv()
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")
PDF_PATH = "document.pdf"   # change to your file

# Allow configuring document language; default to English-India (must be one of Sarvam's allowed codes).
SARVAM_DOC_LANGUAGE = os.getenv("SARVAM_DOC_LANGUAGE", "en-IN")

# Proper SarvamAI client initialization using the correct constructor argument.
if SARVAM_API_KEY:
    client = SarvamAI(api_subscription_key=SARVAM_API_KEY)
else:
    client = None

# =========================
# STEP 1 — OCR EXTRACTION
# =========================
def extract_text_from_pdf(pdf_path):
    print("Creating OCR job...")

    if client is None:
        raise RuntimeError("SARVAM_API_KEY is not configured; cannot run document intelligence OCR.")

    job = client.document_intelligence.create_job(
        language=SARVAM_DOC_LANGUAGE,
        output_format="md"
    )

    job.upload_file(pdf_path)
    print("File uploaded")

    job.start()
    print("Processing...")

    status = job.wait_until_complete()
    print("Completed:", status.job_state)

    job.download_output("output.zip")
    print("Downloaded output.zip")

    # unzip
    with zipfile.ZipFile("output.zip", 'r') as zip_ref:
        zip_ref.extractall("output")

    # read markdown
    for file in os.listdir("output"):
        if file.endswith(".md"):
            with open(os.path.join("output", file), "r", encoding="utf-8") as f:
                return f.read()

    raise Exception("No markdown file found!")


# =========================
# STEP 2 — CLASSIFY MEETING DATA
# =========================
def classify_meeting_data(extracted_text: str):
    """Extract structured meeting data from OCR text using AI classification"""
    print("Classifying meeting data...")
    
    if client is None:
        raise RuntimeError("SARVAM_API_KEY is not configured; cannot classify meeting data.")
    
    prompt = f"""You are a data extraction assistant for Mumbai Municipal Corporation meeting documents.

Extract structured information from the meeting document text below and return ONLY a valid JSON object with these exact fields:
- meeting_id: A unique identifier (generate one if not found, format: "MEET-YYYYMMDD-XXX")
- objective: Main purpose/objective of the meeting (string)
- meeting_date: Date in YYYY-MM-DD format (string, or null if not found)
- meeting_time: Time in HH:MM format (string, or null if not found)
- attendees_present: List of attendee names as a JSON array (array of strings, or empty array if not found)
- ward: Ward name or number (string, or null if not found)
- venue: Meeting venue/location (string, or null if not found)
- projects_discussed_list: List of project names discussed as a JSON array (array of strings, or empty array if not found)

Important:
- Return ONLY valid JSON, no markdown, no explanations, no code blocks
- Use null for missing fields (not empty strings)
- Extract dates in YYYY-MM-DD format
- Extract times in HH:MM format (24-hour)
- For arrays, use empty array [] if nothing found

DOCUMENT TEXT:
{extracted_text[:15000]}
"""
    
    response = client.chat.completions(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3  # Lower temperature for more consistent extraction
    )
    
    response_text = response.choices[0].message.content.strip()
    
    # Try to extract JSON from the response (handle cases where AI wraps it in markdown)
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0].strip()
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0].strip()
    
    try:
        classified_data = json.loads(response_text)
        return classified_data
    except json.JSONDecodeError as e:
        print(f"Failed to parse JSON from AI response: {e}")
        print(f"Response was: {response_text[:500]}")
        # Return a default structure with nulls
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


# =========================
# STEP 3 — SMART SUMMARY (from database)
# =========================
def generate_summary_from_db(meeting_records):
    """Generate detailed, comprehensive summary from Meeting_data table records"""
    print("Generating detailed human summary from database...")

    if client is None:
        raise RuntimeError("SARVAM_API_KEY is not configured; cannot generate summary.")
    
    if not meeting_records:
        return "No meeting records found in the database to summarize."

    # Format meeting records for the prompt
    meetings_text = json.dumps(meeting_records, indent=2, default=str)

    prompt = f"""
You are a helpful, friendly civic assistant for Mumbai who explains things clearly to local residents.

Always reply in clear, natural English, even if the original document was in another language.
Write in a warm, conversational tone like you're explaining to a neighbor.

Based ONLY on the meeting data below, provide a DETAILED, COMPREHENSIVE summary that covers:

1. Meeting Overview:
   - When and where the meeting took place
   - Who attended (list all attendees if available)
   - What was the main objective or purpose

2. Key Issues Discussed:
   - Go through ALL projects mentioned in the data
   - Explain each issue or topic in detail
   - Include any concerns raised by attendees

3. Decisions and Actions:
   - What specific decisions were made
   - Any budgets allocated or approved
   - Deadlines or timelines set
   - Who is responsible for what

4. Impact on Residents:
   - Why these decisions matter to local people
   - What changes residents can expect
   - Any benefits or improvements coming

IMPORTANT INSTRUCTIONS:
- Be THOROUGH - analyze ALL the data provided, don't skip details
- Use clear paragraph breaks for readability
- Write in complete sentences, be conversational and friendly
- Do NOT use markdown formatting, bullet points, asterisks, or headings
- Do NOT include HTML tags like <br> or <p>
- Just use plain English text with paragraph breaks
- Don't invent information - only use what's in the data
- Make it as DETAILED and LONG as needed to cover everything

MEETING DATA FROM DATABASE:
{meetings_text}
"""

    # SarvamAI Python SDK exposes `chat.completions` as a callable function.
    # Increased max_tokens for longer, more detailed responses
    response = client.chat.completions(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=2500
    )

    return response.choices[0].message.content


def generate_meeting_summary_with_prompt(meeting_records, user_prompt: str):
    """Generate detailed summary from Meeting_data table records using a custom user prompt"""
    print("Generating detailed custom summary from database with user prompt...")

    if client is None:
        raise RuntimeError("SARVAM_API_KEY is not configured; cannot generate summary.")
    
    if not meeting_records:
        return "No meeting records found in the database to summarize."

    # Format meeting records for the prompt
    meetings_text = json.dumps(meeting_records, indent=2, default=str)

    prompt = f"""You are a helpful, friendly civic assistant for Mumbai.

User's Question: {user_prompt}

MEETING DATA FROM DATABASE:
{meetings_text}

Please provide a DETAILED, THOROUGH answer to the user's question based on the meeting data above.

IMPORTANT INSTRUCTIONS:
- Analyze ALL the meeting data thoroughly - don't skip any relevant details
- Be comprehensive and detailed in your response
- Write in a warm, conversational, friendly tone
- Use clear paragraph breaks for readability
- Base your answer ONLY on the meeting data provided - don't invent information
- Do NOT use markdown formatting, bullet points, asterisks, or headings
- Do NOT include HTML tags like <br>, <p>, or table markup
- Just use plain English text with paragraph breaks
- Make your answer as LONG and DETAILED as needed to fully address the question
- If the data contains lists (attendees, projects), mention all of them
"""

    # SarvamAI Python SDK exposes `chat.completions` as a callable function.
    # Increased max_tokens for longer, more detailed responses
    response = client.chat.completions(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=2500
    )

    return response.choices[0].message.content



# =========================
# MAIN (for testing)
# =========================
if __name__ == "__main__":
    import sqlite3
    
    text = extract_text_from_pdf(PDF_PATH)
    print("\nExtracted text length:", len(text))
    
    # Classify meeting data
    classified = classify_meeting_data(text)
    print("\n\n===== CLASSIFIED DATA =====\n")
    print(json.dumps(classified, indent=2))
    
    # Store in database (for testing)
    conn = sqlite3.connect("../DATA_DB.db")
    cursor = conn.cursor()
    
    # Ensure table exists
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
    
    # Store data
    attendees_json = json.dumps(classified.get("attendees_present", []) or [])
    projects_json = json.dumps(classified.get("projects_discussed_list", []) or [])
    
    cursor.execute('''
    INSERT OR REPLACE INTO Meeting_data 
    (meeting_id, objective, meeting_date, meeting_time, attendees_present, ward, venue, projects_discussed_list)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        classified.get("meeting_id"),
        classified.get("objective"),
        classified.get("meeting_date"),
        classified.get("meeting_time"),
        attendees_json,
        classified.get("ward"),
        classified.get("venue"),
        projects_json
    ))
    
    conn.commit()
    
    # Fetch and generate summary
    cursor.execute("SELECT * FROM Meeting_data WHERE meeting_id = ?", (classified.get("meeting_id"),))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        meeting_dict = dict(row)
        meeting_dict["attendees_present"] = json.loads(meeting_dict.get("attendees_present", "[]"))
        meeting_dict["projects_discussed_list"] = json.loads(meeting_dict.get("projects_discussed_list", "[]"))
        summary = generate_summary_from_db([meeting_dict])
        
        print("\n\n===== FINAL SUMMARY =====\n")
        print(summary)
        
        with open("summary.txt", "w", encoding="utf-8") as f:
            f.write(summary)
        
        print("\nSaved to summary.txt")