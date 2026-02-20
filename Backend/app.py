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
    init_database, insert_projects, search_projects,
    get_ward_stats, get_statistics, get_meetings,
    create_user, authenticate_user, get_user_by_id,
    insert_complaint, get_complaints_for_user, get_all_complaints,
    update_complaint_status, add_follow_up, remove_follow_up,
    get_followed_projects, DATABASE_PATH,
)

load_dotenv()

app = Flask(__name__)
CORS(app, supports_credentials=True)

UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads")
ALLOWED_EXTENSIONS = {"pdf"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
init_database()

# Simple token store (in-memory for hackathon)
_sessions = {}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_current_user():
    """Get current user from auth token header."""
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


def get_city():
    """Get city from query param, header, or default to mumbai."""
    return request.args.get("city") or request.headers.get("X-City") or "mumbai"


# ==================== AUTH ====================


@app.route("/api/auth/signup", methods=["POST"])
def signup():
    data = request.get_json()
    if not data or not data.get("username") or not data.get("password"):
        return jsonify({"error": "Username and password required"}), 400

    user_id = create_user(
        username=data["username"],
        password=data["password"],
        display_name=data.get("display_name"),
        city=data.get("city", "mumbai"),
        ward_number=data.get("ward_number"),
    )

    if not user_id:
        return jsonify({"error": "Username already taken"}), 409

    token = secrets.token_hex(32)
    _sessions[token] = user_id
    user = get_user_by_id(user_id)

    resp = jsonify({"success": True, "token": token, "user": user})
    resp.set_cookie("token", token, httponly=True, samesite="Lax", max_age=86400 * 7)
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

    safe_user = {k: v for k, v in user.items() if k != "password_hash"}
    resp = jsonify({"success": True, "token": token, "user": safe_user})
    resp.set_cookie("token", token, httponly=True, samesite="Lax", max_age=86400 * 7)
    return resp


@app.route("/api/auth/me", methods=["GET"])
def get_me():
    user = get_current_user()
    if not user:
        return jsonify({"user": None})
    return jsonify({"user": user})


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    if not token:
        token = request.cookies.get("token", "")
    _sessions.pop(token, None)
    resp = jsonify({"success": True})
    resp.delete_cookie("token")
    return resp


# ==================== HEALTH ====================


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "jansaakshi-api"})


# ==================== ADMIN — PDF UPLOAD ====================


@app.route("/api/admin/upload-pdf", methods=["POST"])
@require_admin
def admin_upload_pdf():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file"}), 400

    try:
        import time
        start = time.perf_counter()

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        city = request.form.get("city", get_city())
        projects = extract_projects_from_pdf(filepath)

        for p in projects:
            if not p.get("summary"):
                p["summary"] = generate_project_summary(p)

        inserted = insert_projects(projects, city=city)
        elapsed = time.perf_counter() - start

        # Also create a meeting record
        conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
        conn.execute("""
            INSERT INTO meetings (city, ward_number, meeting_date, meeting_type, pdf_filename, projects_count)
            VALUES (?, ?, date('now'), 'ward_committee', ?, ?)
        """, (city, projects[0].get("ward_number") if projects else None, filename, len(projects)))
        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": f"Extracted {len(projects)} projects in {elapsed:.1f}s",
            "projects_extracted": len(projects),
            "projects_inserted": inserted,
            "processing_time_seconds": round(elapsed, 2),
            "projects": projects,
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== ADMIN — COMPLAINTS ====================


@app.route("/api/admin/complaints", methods=["GET"])
@require_admin
def admin_get_complaints():
    city = get_city()
    complaints = get_all_complaints(city=city)
    return jsonify({"complaints": complaints, "count": len(complaints)})


@app.route("/api/admin/complaints/<int:cid>", methods=["PATCH"])
@require_admin
def admin_update_complaint(cid):
    data = request.get_json()
    update_complaint_status(cid, data.get("status", "reviewed"), data.get("admin_notes"))
    return jsonify({"success": True})


# ==================== QUERY ====================


@app.route("/api/query", methods=["POST"])
def query_projects():
    data = request.get_json()
    if not data or not data.get("query"):
        return jsonify({"error": "Query required"}), 400

    user_query = data["query"]
    city = data.get("city") or get_city()

    try:
        keywords = extract_keywords_from_query(user_query)
        keyword_str = " ".join(keywords.get("keywords", []))

        results = search_projects(
            city=city,
            ward_number=keywords.get("ward_number"),
            ward_name=keywords.get("ward_name"),
            project_type=keywords.get("project_type"),
            status=keywords.get("status"),
            corporator=keywords.get("corporator_name"),
            keyword=keyword_str if keyword_str.strip() else None,
        )

        if not results:
            results = search_projects(city=city, keyword=user_query)

        answer = add_context_to_results(user_query, results)
        return jsonify({
            "success": True, "query": user_query, "answer": answer,
            "keywords_extracted": keywords,
            "projects_count": len(results), "projects": results[:10],
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== PROJECTS ====================


@app.route("/api/projects", methods=["GET"])
def get_all_projects():
    city = get_city()
    results = search_projects(
        city=city,
        ward_number=request.args.get("ward"),
        project_type=request.args.get("type"),
        status=request.args.get("status"),
        keyword=request.args.get("q"),
    )
    return jsonify({"projects": results, "count": len(results)})


@app.route("/api/projects/delayed", methods=["GET"])
def get_delayed():
    city = get_city()
    projects = search_projects(city=city, status="delayed")
    projects.sort(key=lambda x: x.get("delay_days", 0), reverse=True)
    return jsonify(projects)


@app.route("/api/projects/<int:pid>", methods=["GET"])
def get_project(pid):
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "Not found"}), 404
    return jsonify(dict(row))


# ==================== FOLLOW-UPS ====================


@app.route("/api/follow", methods=["POST"])
@require_auth
def follow_project():
    data = request.get_json()
    pid = data.get("project_id")
    if not pid:
        return jsonify({"error": "project_id required"}), 400
    ok = add_follow_up(g.user["id"], pid)
    return jsonify({"success": ok})


@app.route("/api/unfollow", methods=["POST"])
@require_auth
def unfollow_project():
    data = request.get_json()
    remove_follow_up(g.user["id"], data.get("project_id"))
    return jsonify({"success": True})


@app.route("/api/following", methods=["GET"])
@require_auth
def get_following():
    projects = get_followed_projects(g.user["id"])
    return jsonify({"projects": projects, "count": len(projects)})


# ==================== WARDS ====================


@app.route("/api/wards", methods=["GET"])
def api_wards():
    city = get_city()
    return jsonify(get_ward_stats(city=city))


@app.route("/api/projects/ward/<ward_number>", methods=["GET"])
def api_ward_projects(ward_number):
    city = get_city()
    projects = search_projects(city=city, ward_number=ward_number)
    return jsonify({"ward_number": ward_number, "projects": projects, "count": len(projects)})


# ==================== MEETINGS ====================


@app.route("/api/meetings", methods=["GET"])
def api_meetings():
    city = get_city()
    ward = request.args.get("ward")
    meetings = get_meetings(city=city, ward_number=ward)
    return jsonify({"meetings": meetings, "count": len(meetings)})


# ==================== COMPLAINTS ====================


@app.route("/api/complaints", methods=["POST"])
def submit_complaint():
    data = request.get_json()
    if not data or not data.get("description"):
        return jsonify({"error": "Description required"}), 400

    user = get_current_user()
    city = data.get("city") or get_city()
    cid = insert_complaint(data, user_id=user["id"] if user else None, city=city)
    return jsonify({"success": True, "complaint_id": cid})


@app.route("/api/complaints", methods=["GET"])
def get_complaints():
    user = get_current_user()
    if user:
        complaints = get_complaints_for_user(user["id"])
    else:
        complaints = []
    return jsonify({"complaints": complaints, "count": len(complaints)})


# ==================== STATS ====================


@app.route("/api/stats", methods=["GET"])
def api_stats():
    city = get_city()
    return jsonify(get_statistics(city=city))


# ==================== SEARCH ====================


@app.route("/api/search", methods=["GET"])
def api_search():
    city = get_city()
    results = search_projects(
        city=city,
        ward_number=request.args.get("ward"),
        project_type=request.args.get("type"),
        status=request.args.get("status"),
        keyword=request.args.get("q"),
        corporator=request.args.get("corporator"),
        min_delay=request.args.get("min_delay", type=int),
    )
    return jsonify({"results": results, "count": len(results)})


# ==================== CITIES ====================


@app.route("/api/cities", methods=["GET"])
def get_cities():
    """Return supported cities with map centers."""
    cities = [
        {"id": "mumbai", "name": "Mumbai", "lat": 19.076, "lng": 72.8777, "zoom": 11},
        {"id": "delhi", "name": "Delhi", "lat": 28.6139, "lng": 77.209, "zoom": 11},
    ]
    return jsonify(cities)


# ==================== MAIN ====================


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  JanSaakshi API — http://localhost:{port}")
    print(f"  DB: {DATABASE_PATH}  |  Uploads: {UPLOAD_FOLDER}\n")
    app.run(host="0.0.0.0", port=port, debug=True)
