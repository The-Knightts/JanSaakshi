import pdfplumber
from PIL import Image
import pytesseract
import os
from groq import Groq
import json
from datetime import datetime

# Lazy Groq client (created on first use so imports don't fail without API key)
_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key or api_key == "your_groq_api_key_here":
            raise RuntimeError(
                "GROQ_API_KEY is not configured. Add it to your .env file."
            )
        _client = Groq(api_key=api_key)
    return _client


def extract_text_from_pdf(pdf_path):
    """
    Extract text from PDF using pdfplumber (fast, handles both text and scanned PDFs).

    Args:
        pdf_path (str): Path to PDF file

    Returns:
        str: Extracted text from all pages
    """
    text = ""

    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, 1):
                # Try direct text extraction first (fast path)
                page_text = page.extract_text()

                if page_text and len(page_text.strip()) > 50:
                    # Good text extraction
                    text += f"\n--- Page {page_num} ---\n{page_text}"
                else:
                    # Likely a scanned PDF, use OCR
                    print(f"Page {page_num} appears scanned, using OCR...")
                    img = page.to_image(resolution=300)
                    ocr_text = pytesseract.image_to_string(img.original)
                    text += f"\n--- Page {page_num} (OCR) ---\n{ocr_text}"

        return text.strip()

    except Exception as e:
        raise Exception(f"PDF extraction failed: {str(e)}")


def _extract_json_from_text(text):
    """Try hard to find a JSON array in the response text."""
    import re
    text = text.strip()

    # Remove markdown fences
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    text = text.strip()

    # Try direct parse
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else [data]
    except json.JSONDecodeError:
        pass

    # Find first [ ... ] block
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

    # Find first { ... } block (single object)
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
    """
    Extract structured municipal project data from PDF using Groq.

    Args:
        pdf_path (str): Path to PDF file

    Returns:
        list: Array of project dictionaries
    """
    pdf_text = extract_text_from_pdf(pdf_path)

    if not pdf_text or len(pdf_text) < 50:
        raise Exception("Insufficient text extracted from PDF")

    # Prompt designed for BMC Standing Committee meeting minutes format
    prompt = f"""I have text from a Brihanmumbai Municipal Corporation (BMC) Standing Committee meeting minutes PDF. The document contains:

- A header with meeting number, date, time, venue, and ward info
- An attendees list
- Multiple ITEM NO. sections, each describing a municipal project with:
  - Project Name, Location, Budget Approved, Budget Head
  - Budget Breakdown (itemized costs)
  - Project Timeline (commencement, completion target)
  - Responsible Officer / Project Manager
  - Contractor Details
  - Ward Corporator's Recommendation
  - DECISION (approved/rejected)

For EACH project item in the document, extract and return a JSON array like this:

[
  {{
    "project_name": "exact project name or item heading",
    "summary": "1-2 sentence citizen-friendly description",
    "ward_number": "ward code like H/W, R/S, K/E from the document header",
    "ward_name": "ward area name from the document, e.g. Bandra West",
    "budget_amount": 1575000,
    "corporator_name": "name of the ward corporator who recommended it",
    "contractor_name": "contractor/company name if mentioned, or null",
    "responsible_official": "responsible officer/project manager name",
    "approval_date": "2025-12-15",
    "expected_completion": "2026-04-30",
    "project_type": "parks",
    "status": "approved",
    "delay_days": 0,
    "location_details": "Linking Road, Khar West"
  }}
]

RULES:
- project_type must be one of: roads, water_supply, schools, parks, waste_management, healthcare, street_lighting, drainage, other
- status must be one of: approved, ongoing, completed, delayed, pending
- Convert ₹15,75,000 or "Fifteen Lakhs" to 1575000 (numeric rupees)
- Convert ₹42,50,000 or "Forty Two Lakhs" to 4250000
- Convert "2 crores" to 20000000
- Dates should be YYYY-MM-DD format
- Return ONLY the JSON array, nothing else — no explanations, no markdown

DOCUMENT TEXT:
{pdf_text[:15000]}"""

    try:
        response = _get_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a JSON extraction engine. You read Indian municipal meeting documents and return ONLY a valid JSON array of projects. Never return explanations or prose — only JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.05,
            max_tokens=4096,
        )

        result = response.choices[0].message.content.strip()
        print(f"[Groq raw response length: {len(result)} chars]")

        projects = _extract_json_from_text(result)

        if not projects:
            raise Exception(
                f"Could not find JSON in Groq response.\nFirst 500 chars: {result[:500]}"
            )

        # Post-process
        for project in projects:
            if project.get("expected_completion") and project.get("status") in ["ongoing", "delayed"]:
                try:
                    expected = datetime.fromisoformat(project["expected_completion"])
                    if datetime.now() > expected:
                        project["delay_days"] = (datetime.now() - expected).days
                        project["status"] = "delayed"
                    else:
                        project["delay_days"] = 0
                except Exception:
                    project["delay_days"] = project.get("delay_days", 0)
            else:
                project["delay_days"] = project.get("delay_days", 0)

            project["source_pdf"] = os.path.basename(pdf_path)
            project["extracted_at"] = datetime.now().isoformat()

        return projects

    except Exception as e:
        raise Exception(f"Project extraction failed: {str(e)}")


def generate_project_summary(project_data):
    """
    Generate citizen-friendly summary for a project using Groq.

    Args:
        project_data (dict): Project dictionary

    Returns:
        str: Human-readable summary
    """
    budget = project_data.get("budget_amount", 0) or 0
    prompt = f"""
Write a clear, concise 2-3 sentence summary that a regular citizen would understand.

Project Details:
- Name: {project_data.get('project_name')}
- Ward: {project_data.get('ward_number')} ({project_data.get('ward_name')})
- Budget: ₹{budget / 100000:.2f} lakhs
- Type: {project_data.get('project_type')}
- Approved: {project_data.get('approval_date')}
- Expected Completion: {project_data.get('expected_completion')}
- Status: {project_data.get('status')}

Write the summary in simple language. Focus on what matters to residents.
"""

    try:
        response = _get_client().chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=200,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        # Fallback to basic summary
        return f"{project_data.get('project_name')} in {project_data.get('ward_name')} with budget of ₹{budget / 100000:.2f} lakhs."
