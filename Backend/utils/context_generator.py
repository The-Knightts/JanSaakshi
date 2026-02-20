import os
import json
import re
from sarvamai import SarvamAI

_client = None


def _get_client():
    global _client
    if _client is None:
        api_key = os.environ.get("SARVAM_API_KEY")
        if not api_key or api_key == "your_sarvam_api_key_here":
            return None
        _client = SarvamAI(api_subscription_key=api_key)
    return _client


def extract_keywords_locally(user_query):
    """Fast local keyword extraction — no API call needed."""
    q = user_query.lower().strip()
    result = {"ward_no": None, "ward_name": None, "project_type": None,
              "status": None, "corporator_name": None, "keywords": []}

    # Extract ward number
    ward_match = re.search(r'\bward\s*(?:no\.?\s*)?(\d+)', q)
    if ward_match:
        result["ward_no"] = ward_match.group(1)

    # Detect status
    status_map = {"delayed": "delayed", "delay": "delayed", "stalled": "stalled",
                  "completed": "completed", "done": "completed", "finished": "completed",
                  "ongoing": "ongoing", "progress": "ongoing", "approved": "approved"}
    for word, stat in status_map.items():
        if word in q:
            result["status"] = stat
            break

    # Detect project type
    type_map = {"road": "roads", "highway": "roads", "bridge": "roads", "flyover": "roads",
                "water": "water_supply", "pipeline": "water_supply", "pipe": "water_supply",
                "school": "schools", "education": "schools", "park": "parks", "garden": "parks",
                "drain": "drainage", "sewer": "drainage", "flood": "drainage", "nallah": "drainage",
                "health": "healthcare", "hospital": "healthcare", "dispensary": "healthcare",
                "light": "street_lighting", "lamp": "street_lighting", "led": "street_lighting",
                "waste": "waste_management", "garbage": "waste_management", "trash": "waste_management"}
    for word, ptype in type_map.items():
        if word in q:
            result["project_type"] = ptype
            break

    # Detect ward names (common Mumbai/Delhi areas)
    areas = {
        "kandivali": "Kandivali", "andheri": "Andheri", "bandra": "Bandra",
        "dadar": "Dadar", "worli": "Worli", "mulund": "Mulund", "kurla": "Kurla",
        "borivali": "Borivali", "malad": "Malad", "ghatkopar": "Ghatkopar",
        "versova": "Andheri West", "charkop": "Kandivali West",
        "chandni chowk": "Chandni Chowk", "dwarka": "Dwarka", "rohini": "Rohini",
        "saket": "Saket", "lajpat nagar": "Lajpat Nagar", "pitampura": "Pitampura",
        "okhla": "Okhla", "janakpuri": "Janakpuri", "karol bagh": "Karol Bagh",
        "mayur vihar": "Mayur Vihar", "shahdara": "Shahdara",
    }
    for kw, area in areas.items():
        if kw in q:
            result["ward_name"] = area
            break

    # Extract meaningful keywords (remove stop words)
    stop = {"the", "is", "in", "at", "of", "on", "for", "to", "and", "or", "an",
            "what", "how", "which", "where", "when", "show", "tell", "me", "my",
            "are", "has", "have", "with", "about", "update", "status", "projects",
            "any", "all", "latest", "current", "give", "list", "find", "search",
            "can", "you", "please", "want", "need", "know", "get"}
    words = [w for w in re.findall(r'[a-z]+', q) if w not in stop and len(w) >= 3]
    result["keywords"] = words

    return result


def extract_keywords_from_query(user_query):
    """Smart keyword extraction — uses local parsing first, AI only for complex queries."""
    local = extract_keywords_locally(user_query)

    # If local parsing found structured info, use it
    if local["ward_no"] or local["ward_name"] or local["project_type"] or local["status"]:
        return local

    # For complex queries, try AI if available
    client = _get_client()
    if not client:
        return local  # Fall back to local parsing

    prompt = f"""Extract search parameters from this query about municipal projects:

Query: "{user_query}"

Return ONLY a JSON object:
{{
    "ward_no": "string or null",
    "ward_name": "string or null",
    "project_type": "roads|water_supply|schools|parks|waste_management|healthcare|street_lighting|drainage|other|null",
    "corporator_name": "string or null",
    "status": "approved|ongoing|completed|delayed|stalled|null",
    "keywords": ["array", "of", "relevant", "keywords"]
}}

Examples:
"What projects are delayed in Ward 68?" → {{"ward_no": "68", "status": "delayed", "keywords": ["delayed"]}}
"Show me road work in Andheri" → {{"ward_name": "Andheri", "project_type": "roads", "keywords": ["road"]}}
"Eastern Freeway Extension update" → {{"keywords": ["eastern", "freeway", "extension"]}}
"""

    try:
        response = client.chat.completions(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
        )
        result = response.choices[0].message.content.strip()
        if result.startswith("```"):
            result = result.replace("```json", "").replace("```", "").strip()
        return json.loads(result)
    except Exception as e:
        print(f"AI keyword extraction failed, using local: {e}")
        return local


def generate_no_data_response(user_query, keywords):
    """Professional no-data message with helpful suggestions."""
    query_clean = user_query.strip().rstrip("?.")

    suggestions = []
    if keywords.get("ward_name"):
        suggestions.append(f'Try searching for other projects in {keywords["ward_name"]}')
    if keywords.get("ward_no"):
        suggestions.append(f'Check ward {keywords["ward_no"]} for related projects')
    suggestions.append("Try broader terms like 'road projects' or 'water supply'")
    suggestions.append("Browse the Projects tab for all available data")

    return {
        "found": False,
        "answer": (
            f"We don't have data on \"{query_clean}\" in our records yet. "
            f"This could mean the project hasn't been documented in uploaded meeting minutes, "
            f"or it may be known by a different name in official records."
        ),
        "suggestions": suggestions[:3],
    }


def add_context_to_results(user_query, db_results):
    """Generate concise, relevant summary from search results."""
    if not db_results:
        return generate_no_data_response(user_query, extract_keywords_locally(user_query))

    # Build a concise local summary (no API needed)
    top = db_results[:5]
    lines = []
    for p in top:
        budget_str = f"₹{(p.get('budget') or 0) / 100000:.1f}L" if p.get('budget') else ''
        delay_str = f", delayed by {p['delay_days']} days" if p.get('delay_days', 0) > 0 else ''
        status = p.get('status', 'unknown')
        lines.append(
            f"**{p['project_name']}** (Ward {p.get('ward_no', '?')}, {p.get('ward_name', '')}): "
            f"{status}{delay_str}. {budget_str}. "
            f"Contractor: {p.get('contractor_name', 'Not assigned')}."
        )

    local_summary = " ".join(lines)

    # Try AI for a more natural answer
    client = _get_client()
    if not client:
        return {
            "found": True,
            "answer": local_summary,
            "suggestions": [],
        }

    results_text = "\n".join([
        f"• {p['project_name']} | Ward {p.get('ward_no')} ({p.get('ward_name')}) | "
        f"Status: {p.get('status')} | Budget: ₹{(p.get('budget') or 0)/100000:.1f}L | "
        f"Delay: {p.get('delay_days', 0)}d | Contractor: {p.get('contractor_name', 'N/A')} | "
        f"Corporator: {p.get('corporator_name', 'N/A')} | Expected: {p.get('expected_completion', 'N/A')}"
        for p in top
    ])

    prompt = f"""User asked: "{user_query}"

Data found:
{results_text}

Write a SHORT (2-4 sentences max), direct answer:
- Answer the specific question
- Mention status, delays, budget, who is responsible
- Use ₹ amounts and specific dates
- Be conversational but factual
- If delayed, state the delay clearly
Do NOT add disclaimers or meta-commentary. Just answer."""

    try:
        response = client.chat.completions(
            messages=[
                {"role": "system", "content": "You are a concise municipal data assistant. Give direct, factual answers using the provided data. Never hallucinate."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=300,
        )
        return {
            "found": True,
            "answer": response.choices[0].message.content.strip(),
            "suggestions": [],
        }
    except Exception:
        return {
            "found": True,
            "answer": local_summary,
            "suggestions": [],
        }
