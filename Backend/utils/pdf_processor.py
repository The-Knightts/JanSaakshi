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
    """Find JSON array or object in response text."""
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    try:
        data = json.loads(text)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        pass

    # Find [...] block
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

    # Find {...} block
    start = text.find('{')
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == '{': depth += 1
            elif text[i] == '}': depth -= 1
            if depth == 0:
                try:
                    return [json.loads(text[start:i+1])]
                except json.JSONDecodeError:
                    break

    return None


def extract_projects_from_pdf(pdf_path):
    """Extract structured project data from PDF using Sarvam AI."""
    pdf_text = extract_text_from_pdf(pdf_path)

    if not pdf_text or len(pdf_text) < 50:
        raise Exception("Insufficient text extracted from PDF")

    prompt = f"""I have text from a municipal meeting minutes PDF (likely BMC or MCD). The document has:
- Header with meeting number, date, time, venue, ward info
- Attendees list
- Multiple ITEM NO. sections each describing a project with:
  Project Name, Location, Budget, Timeline, Contractor, Responsible Officer, Decision

For EACH project, return a JSON array:

[
  {{
    "project_name": "exact project name",
    "summary": "1-2 sentence citizen-friendly description",
    "ward_no": "numeric ward number from document",
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
    "location_details": "specific location"
  }}
]

RULES:
- project_type: roads, water_supply, schools, parks, waste_management, healthcare, street_lighting, drainage, other
- status: approved, ongoing, completed, delayed, stalled
- Convert Indian currency: ₹15,75,000 = 1575000, "2 crores" = 20000000
- Dates: YYYY-MM-DD format
- Return ONLY JSON array, no explanations

DOCUMENT TEXT:
{pdf_text[:12000]}"""

    try:
        response = _get_client().chat.completions(
            messages=[
                {"role": "system", "content": "You are a JSON extraction engine for Indian municipal documents. Return ONLY valid JSON arrays."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.05,
            max_tokens=4096,
        )

        result = response.choices[0].message.content.strip()
        print(f"[Sarvam response: {len(result)} chars]")

        projects = _extract_json_from_text(result)
        if not projects:
            raise Exception(f"No JSON found in response. First 500 chars: {result[:500]}")

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

        return projects

    except Exception as e:
        raise Exception(f"Project extraction failed: {str(e)}")


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
