from flask import Flask, request, jsonify, g
from flask_cors import CORS
import os
import json
import sqlite3
import secrets
from functools import wraps
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

from utils.pdf_processor import extract_projects_from_pdf, generate_project_summary
from utils.context_generator import extract_keywords_from_query, add_context_to_results
from utils.database import (
    init_database, get_city_id, get_all_cities,
    insert_projects, search_projects, get_ward_stats, get_statistics,
    get_meetings, create_user, authenticate_user, get_user_by_id,
    insert_complaint, get_complaints_for_user, get_all_complaints,
    update_complaint_status, add_follow_up, remove_follow_up,
    get_followed_projects, DATABASE_PATH,
)

load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads")
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
init_database()

_sessions = {}


def allowed_file(fn):
    return "." in fn and fn.rsplit(".", 1)[1].lower() == "pdf"


def get_current_user():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        token = request.cookies.get("token", "")
    if token and token in _sessions:
        return get_user_by_id(_sessions[token])
    return None


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"error": "Login required"}), 401
        g.user = user
        return f(*args, **kwargs)
    return decorated


def require_admin(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user or user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        g.user = user
        return f(*args, **kwargs)
    return decorated


def resolve_city_id():
    """Resolve city_id from query param or header."""
    city_name = request.args.get("city") or request.headers.get("X-City") or "mumbai"
    return get_city_id(city_name)


# ==================== AUTH ====================


@app.route("/api/auth/signup", methods=["POST"])
def signup():
    data = request.get_json()
    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "Username and password required"}), 400

    city_id = get_city_id(data.get("city", "mumbai"))
    user_id = create_user(
        username=data["username"], password=data["password"],
        display_name=data.get("display_name"),
        city_id=city_id, ward=data.get("ward"),
    )
    if not user_id:
        return jsonify({"error": "Username already taken"}), 409

    token = secrets.token_hex(32)
    _sessions[token] = user_id
    user = get_user_by_id(user_id)
    resp = jsonify({"success": True, "token": token, "user": user})
    resp.set_cookie("token", token, httponly=True, samesite="Lax", max_age=604800)
    return resp


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Credentials required"}), 400
    user = authenticate_user(data.get("username", ""), data.get("password", ""))
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    token = secrets.token_hex(32)
    _sessions[token] = user["id"]
    safe = {k: v for k, v in user.items() if k != "password"}
    resp = jsonify({"success": True, "token": token, "user": safe})
    resp.set_cookie("token", token, httponly=True, samesite="Lax", max_age=604800)
    return resp


@app.route("/api/auth/me")
def get_me():
    user = get_current_user()
    return jsonify({"user": user})


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    token = request.headers.get("Authorization", "").replace("Bearer ", "") or request.cookies.get("token", "")
    _sessions.pop(token, None)
    resp = jsonify({"success": True})
    resp.delete_cookie("token")
    return resp


# ==================== HEALTH ====================


@app.route("/health")
def health():
    return jsonify({"status": "healthy"})


# ==================== ADMIN — PDF ====================


@app.route("/api/admin/upload-pdf", methods=["POST"])
@require_admin
def admin_upload():
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    file = request.files["file"]
    if not file.filename or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file"}), 400

    try:
        import time
        start = time.perf_counter()
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        city_name = request.form.get("city") or "mumbai"
        city_id = get_city_id(city_name)
        projects = extract_projects_from_pdf(filepath)

        for p in projects:
            if not p.get("summary"):
                p["summary"] = generate_project_summary(p)

        inserted = insert_projects(projects, city_id=city_id)
        elapsed = time.perf_counter() - start

        # Create meeting record
        conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
        conn.execute("""
            INSERT INTO meetings (city_id, ward_no, meet_date, meet_type, source_pdf, project_count)
            VALUES (?, ?, date('now'), 'ward_committee', ?, ?)
        """, (city_id, projects[0].get("ward_no") if projects else None, filename, len(projects)))
        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": f"Extracted {len(projects)} projects in {elapsed:.1f}s",
            "projects_extracted": len(projects),
            "projects_inserted": inserted,
            "projects": projects,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== ADMIN — COMPLAINTS ====================


@app.route("/api/admin/complaints")
@require_admin
def admin_complaints():
    cid = resolve_city_id()
    complaints = get_all_complaints(city_id=cid)
    return jsonify({"complaints": complaints, "count": len(complaints)})


@app.route("/api/admin/complaints/<int:complaint_id>", methods=["PATCH"])
@require_admin
def admin_update_complaint(complaint_id):
    data = request.get_json()
    update_complaint_status(complaint_id, data.get("status", "reviewed"), data.get("admin_notes"))
    return jsonify({"success": True})


# ==================== QUERY ====================


@app.route("/api/query", methods=["POST"])
def query_projects():
    data = request.get_json()
    if not data or not data.get("query"):
        return jsonify({"error": "Query required"}), 400

    user_query = data["query"]
    city_id = get_city_id(data.get("city") or request.headers.get("X-City") or "mumbai")

    try:
        keywords = extract_keywords_from_query(user_query)
        keyword_str = " ".join(keywords.get("keywords", []))

        # First: structured search with extracted parameters
        results = search_projects(
            city_id=city_id,
            ward_no=keywords.get("ward_no"),
            ward_name=keywords.get("ward_name"),
            project_type=keywords.get("project_type"),
            status=keywords.get("status"),
            corporator=keywords.get("corporator_name"),
            keyword=keyword_str if keyword_str.strip() else None,
        )

        # Second: raw keyword search as fallback
        if not results:
            results = search_projects(city_id=city_id, keyword=user_query)

        # Third: try without city filter (maybe user means a different city)
        if not results:
            results = search_projects(keyword=user_query)

        context = add_context_to_results(user_query, results)

        # context is now a dict with {found, answer, suggestions}
        if isinstance(context, dict):
            return jsonify({
                "success": True, "query": user_query,
                "found": context.get("found", bool(results)),
                "answer": context.get("answer", ""),
                "suggestions": context.get("suggestions", []),
                "keywords_extracted": keywords,
                "projects_count": len(results),
                "projects": results[:10],
            })
        else:
            # Fallback for old-style string response
            return jsonify({
                "success": True, "query": user_query,
                "found": bool(results), "answer": context,
                "suggestions": [],
                "keywords_extracted": keywords,
                "projects_count": len(results),
                "projects": results[:10],
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== PROJECTS ====================


@app.route("/api/projects")
def api_projects():
    cid = resolve_city_id()
    results = search_projects(
        city_id=cid,
        ward_no=request.args.get("ward"),
        project_type=request.args.get("type"),
        status=request.args.get("status"),
        keyword=request.args.get("q"),
    )
    return jsonify({"projects": results, "count": len(results)})


@app.route("/api/projects/delayed")
def api_delayed():
    cid = resolve_city_id()
    projects = search_projects(city_id=cid, status="delayed")
    projects.sort(key=lambda x: x.get("delay_days", 0), reverse=True)
    return jsonify(projects)


@app.route("/api/projects/<int:pid>")
def api_project(pid):
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    row = conn.execute("""
        SELECT p.*, c.city_name FROM projects p
        JOIN city c ON p.city_id=c.city_id WHERE p.id=?
    """, (pid,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify(dict(row))


# ==================== FOLLOW-UPS ====================


@app.route("/api/follow", methods=["POST"])
@require_auth
def follow():
    data = request.get_json()
    ok = add_follow_up(g.user["id"], data.get("project_id"))
    return jsonify({"success": ok})


@app.route("/api/unfollow", methods=["POST"])
@require_auth
def unfollow():
    data = request.get_json()
    remove_follow_up(g.user["id"], data.get("project_id"))
    return jsonify({"success": True})


@app.route("/api/following")
@require_auth
def following():
    projects = get_followed_projects(g.user["id"])
    return jsonify({"projects": projects, "count": len(projects)})


# ==================== WARDS ====================


@app.route("/api/wards")
def api_wards():
    cid = resolve_city_id()
    return jsonify(get_ward_stats(city_id=cid))


@app.route("/api/projects/ward/<ward_no>")
def api_ward_projects(ward_no):
    cid = resolve_city_id()
    projects = search_projects(city_id=cid, ward_no=ward_no)
    return jsonify({"ward_no": ward_no, "projects": projects, "count": len(projects)})


# ==================== MEETINGS ====================


@app.route("/api/meetings")
def api_meetings():
    cid = resolve_city_id()
    ward = request.args.get("ward")
    meetings = get_meetings(city_id=cid, ward_no=ward)
    return jsonify({"meetings": meetings, "count": len(meetings)})


# ==================== COMPLAINTS ====================


@app.route("/api/complaints", methods=["POST"])
def submit_complaint():
    data = request.get_json()
    if not data or not data.get("description"):
        return jsonify({"error": "Description required"}), 400
    user = get_current_user()
    cid = get_city_id(data.get("city") or "mumbai")
    complaint_id = insert_complaint(data, user_id=user["id"] if user else None, city_id=cid)
    return jsonify({"success": True, "complaint_id": complaint_id})


@app.route("/api/complaints")
def api_complaints():
    user = get_current_user()
    if user:
        complaints = get_complaints_for_user(user["id"])
    else:
        complaints = []
    return jsonify({"complaints": complaints, "count": len(complaints)})


# ==================== STATS ====================


@app.route("/api/stats")
def api_stats():
    cid = resolve_city_id()
    return jsonify(get_statistics(city_id=cid))


# ==================== SEARCH ====================


@app.route("/api/search")
def api_search():
    cid = resolve_city_id()
    results = search_projects(
        city_id=cid,
        ward_no=request.args.get("ward"),
        project_type=request.args.get("type"),
        status=request.args.get("status"),
        keyword=request.args.get("q"),
        corporator=request.args.get("corporator"),
        min_delay=request.args.get("min_delay", type=int),
    )
    return jsonify({"results": results, "count": len(results)})


# ==================== CITIES ====================


@app.route("/api/cities")
def api_cities():
    cities = get_all_cities()
    config = {
        "mumbai": {"lat": 19.076, "lng": 72.8777, "zoom": 11},
        "delhi": {"lat": 28.6139, "lng": 77.209, "zoom": 11},
    }
    return jsonify([
        {**c, **config.get(c["city_name"], {"lat": 20, "lng": 78, "zoom": 5})}
        for c in cities
    ])


# ==================== MAIN ====================


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  JanSaakshi API — http://localhost:{port}")
    print(f"  DB: {DATABASE_PATH}  |  Uploads: {UPLOAD_FOLDER}\n")
    app.run(host="0.0.0.0", port=port, debug=True)
