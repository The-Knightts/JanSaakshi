import pdfplumber
from PIL import Image
import pytesseract
import os
import json
import re
from datetime import datetime
from sarvamai import SarvamAI

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("SARVAM_API_KEY")
        if not api_key or api_key == "your_sarvam_api_key_here":
            raise RuntimeError("SARVAM_API_KEY is not configured. Add it to your .env file.")
        _client = SarvamAI(api_subscription_key=api_key)
    return _client


def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using pdfplumber, OCR fallback for scanned pages."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()
                if page_text and len(page_text.strip()) > 50:
                    text += f"\n--- Page {page_num} ---\n{page_text}"
                else:
                    print(f"Page {page_num} appears scanned, using OCR...")
                    img = page.to_image(resolution=300)
                    ocr_text = pytesseract.image_to_string(img.original)
                    text += f"\n--- Page {page_num} (OCR) ---\n{ocr_text}"
        return text.strip()
    except Exception as e:
        raise Exception(f"PDF extraction failed: {str(e)}")


def _extract_json_from_text(text):
    """Find JSON object or array in response text."""
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find {...} block (top-level object with meeting + projects)
    start = text.find('{')
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '{': depth += 1
            elif text[i] == '}': depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i+1])
                except json.JSONDecodeError:
                    break

    # Fallback: find [...] array
    start = text.find('[')
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '[': depth += 1
            elif text[i] == ']': depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i+1])
                except json.JSONDecodeError:
                    break

    return None


def extract_data_from_pdf(pdf_path):
    """Extract BOTH meeting details and project data from PDF using Sarvam AI.

    Returns:
        dict: {"meeting": {...meeting details...}, "projects": [...project list...]}
    """
    pdf_text = extract_text_from_pdf(pdf_path)

    if not pdf_text or len(pdf_text) < 50:
        raise Exception("Insufficient text extracted from PDF")

    prompt = f"""I have text from a municipal meeting minutes PDF (likely BMC ward committee or MCD).

The document typically has:
- HEADER: meeting number, date, time, venue, ward number, ward name, zone
- ATTENDEES: chairperson, corporators, officers, citizens present
- AGENDA / OBJECTIVE: purpose of the meeting
- Multiple ITEM NO. sections each describing a project

Extract ALL information and return a single JSON object with TWO sections:

{{
  "meeting": {{
    "meet_date": "YYYY-MM-DD format, the actual meeting date from the document",
    "meet_type": "ward_committee or zone_committee or general_body or special",
    "ward_no": "numeric ward number, e.g. 77",
    "ward_name": "area name, e.g. Kandivali West",
    "venue": "meeting venue/location from document",
    "objective": "1-2 sentence summary of meeting purpose/agenda",
    "attendees": "comma-separated key attendees: chairperson, corporators, officers"
  }},
  "projects": [
    {{
      "project_name": "exact project name from the item",
      "summary": "1-2 sentence citizen-friendly description",
      "ward_no": "numeric ward number",
      "ward_name": "area name e.g. Bandra West",
      "ward_zone": "zone code like H/W, K/E, R/S if present",
      "budget": 1575000,
      "corporator_name": "corporator who recommended it",
      "contractor_name": "contractor company or null",
      "project_type": "roads",
      "status": "approved",
      "approval_date": "2025-12-15",
      "start_date": "2026-01-15",
      "expected_completion": "2026-04-30",
      "delay_days": 0,
      "location_details": "specific location from the document"
    }}
  ]
}}

RULES:
- meeting.meet_date: MUST be the actual date from the PDF header, NOT today's date
- meeting.attendees: extract key names (corporator, chairperson, ward officer)
- meeting.objective: summarize what was discussed overall
- project_type: roads, water_supply, schools, parks, waste_management, healthcare, street_lighting, drainage, other
- status: approved, ongoing, completed, delayed, stalled
- Convert Indian currency: ₹15,75,000 = 1575000, "2 crores" = 20000000
- ALL dates: YYYY-MM-DD format
- Return ONLY the JSON object, no explanations

DOCUMENT TEXT:
{pdf_text[:12000]}"""

    try:
        response = _get_client().chat.completions(
            messages=[
                {"role": "system", "content": "You are a JSON extraction engine for Indian municipal meeting documents. Return ONLY valid JSON with both meeting details and projects array."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.05,
            max_tokens=4096,
        )

        result = response.choices[0].message.content.strip()
        print(f"[Sarvam response: {len(result)} chars]")

        parsed = _extract_json_from_text(result)
        if not parsed:
            raise Exception(f"No JSON found in response. First 500 chars: {result[:500]}")

        # Handle both formats: {meeting, projects} or just [projects]
        if isinstance(parsed, dict) and "projects" in parsed:
            meeting = parsed.get("meeting", {})
            projects = parsed.get("projects", [])
        elif isinstance(parsed, list):
            # Fallback: old format returns just projects array
            meeting = {}
            projects = parsed
        elif isinstance(parsed, dict):
            # Single project returned as object
            meeting = {}
            projects = [parsed]
        else:
            raise Exception(f"Unexpected response format: {type(parsed)}")

        # Post-process projects
        for p in projects:
            if p.get("expected_completion") and p.get("status") in ["ongoing", "delayed"]:
                try:
                    exp = datetime.fromisoformat(p["expected_completion"])
                    if datetime.now() > exp:
                        p["delay_days"] = (datetime.now() - exp).days
                        p["status"] = "delayed"
                    else:
                        p["delay_days"] = 0
                except Exception:
                    p["delay_days"] = p.get("delay_days", 0)
            else:
                p["delay_days"] = p.get("delay_days", 0)

            p["source_pdf"] = os.path.basename(pdf_path)

        # Build projects_discussed summary for meeting record
        project_names = [p.get("project_name", "") for p in projects if p.get("project_name")]
        if project_names:
            meeting["projects_discussed"] = json.dumps(project_names)

        # Ensure meeting has ward info from projects if not extracted
        if not meeting.get("ward_no") and projects:
            meeting["ward_no"] = projects[0].get("ward_no")
        if not meeting.get("ward_name") and projects:
            meeting["ward_name"] = projects[0].get("ward_name")

        return {"meeting": meeting, "projects": projects}

    except Exception as e:
        raise Exception(f"Data extraction failed: {str(e)}")


# Keep backward compatibility
def extract_projects_from_pdf(pdf_path):
    """Legacy wrapper — extracts only projects (backward compat)."""
    result = extract_data_from_pdf(pdf_path)
    return result["projects"]


def generate_project_summary(project_data):
    """Generate citizen-friendly summary using Sarvam AI."""
    budget = project_data.get("budget", 0) or 0
    prompt = f"""Write a clear 2-3 sentence summary a regular citizen would understand.

Project: {project_data.get('project_name')}
Ward: {project_data.get('ward_no')} ({project_data.get('ward_name')})
Budget: ₹{budget / 100000:.2f} lakhs
Type: {project_data.get('project_type')}
Status: {project_data.get('status')}
Expected Completion: {project_data.get('expected_completion')}

Write in simple language focusing on what matters to residents."""

    try:
        response = _get_client().chat.completions(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        return f"{project_data.get('project_name')} in {project_data.get('ward_name')} with budget of ₹{budget/100000:.2f} lakhs."
