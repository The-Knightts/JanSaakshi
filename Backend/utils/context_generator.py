import os
import json
from groq import Groq

# Lazy Groq client
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


def extract_keywords_from_query(user_query):
    """
    Extract search-relevant keywords from user's natural language query.

    Args:
        user_query (str): User's question

    Returns:
        dict: Extracted keywords for database search
    """
    prompt = f"""
Extract search parameters from this query about municipal projects:

Query: "{user_query}"

Return ONLY a JSON object with these fields (use null if not mentioned):
{{
    "ward_number": "string or null",
    "ward_name": "string or null",
    "project_type": "roads|water_supply|schools|parks|waste_management|healthcare|street_lighting|drainage|other|null",
    "corporator_name": "string or null",
    "status": "approved|ongoing|completed|delayed|pending|null",
    "keywords": ["array", "of", "relevant", "keywords"],
    "time_period": "string or null (e.g., 'last 6 months', '2024', 'recent')"
}}

Examples:
"What projects are delayed in Ward 123?" → {{"ward_number": "123", "status": "delayed", "keywords": ["delayed", "projects"]}}
"Show me all road work in Andheri" → {{"ward_name": "Andheri", "project_type": "roads", "keywords": ["road", "work"]}}
"""

    try:
        response = _get_client().chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
        )

        result = response.choices[0].message.content.strip()

        # Clean markdown
        if result.startswith("```json"):
            result = result.replace("```json", "").replace("```", "").strip()
        elif result.startswith("```"):
            result = result.replace("```", "").strip()

        return json.loads(result)

    except Exception as e:
        # Fallback: basic keyword extraction
        print(f"Keyword extraction failed: {e}")
        return {
            "keywords": user_query.lower().split(),
            "ward_number": None,
            "ward_name": None,
            "project_type": None,
            "status": None,
            "corporator_name": None,
            "time_period": None,
        }


def add_context_to_results(user_query, db_results):
    """
    Take raw database results and generate natural language response with context.

    Args:
        user_query (str): Original user question
        db_results (list): Raw project data from database

    Returns:
        str: Contextualized, natural language answer
    """
    if not db_results:
        return "No projects found matching your query. Try searching by ward number or project type."

    # Format results for LLM
    results_text = "\n\n".join(
        [
            f"Project {i+1}: {p['project_name']}\n"
            f"Ward: {p.get('ward_number')} - {p.get('ward_name')}\n"
            f"Budget: ₹{(p.get('budget_amount') or 0) / 100000:.2f} lakhs\n"
            f"Type: {p.get('project_type')}\n"
            f"Status: {p.get('status')}\n"
            f"Approved: {p.get('approval_date')}\n"
            f"Expected Completion: {p.get('expected_completion')}\n"
            f"Corporator: {p.get('corporator_name')}\n"
            f"Contractor: {p.get('contractor_name', 'Not assigned')}\n"
            f"Delay: {p.get('delay_days', 0)} days\n"
            for i, p in enumerate(db_results[:10])
        ]
    )

    prompt = f"""
You are a helpful assistant for JanSaakshi, a municipal accountability platform.

User asked: "{user_query}"

Here are the relevant projects found:

{results_text}

Provide a clear, conversational answer that:
1. Directly answers their question
2. Highlights key information (especially delays, budgets, responsible people)
3. Uses simple language citizens can understand
4. Mentions specific numbers and dates
5. If projects are delayed, clearly state who is responsible (corporator, contractor, official)

Keep it concise but informative (3-5 sentences).
"""

    try:
        response = _get_client().chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful municipal governance assistant. Provide clear, factual information about projects. Always cite specific numbers, dates, and responsible people.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        # Fallback: basic summary
        return f"Found {len(db_results)} projects. {db_results[0]['project_name']} in Ward {db_results[0].get('ward_number', 'N/A')} is {db_results[0].get('status', 'unknown')}."
