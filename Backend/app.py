from flask import Flask, request, jsonify, g
from flask_cors import CORS
import os
import json
import sqlite3
import secrets
from datetime import datetime
from functools import wraps
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from wards_route import ward_bp


from utils.pdf_processor import extract_data_from_pdf, extract_projects_from_pdf, generate_project_summary
from utils.context_generator import extract_keywords_from_query, add_context_to_results
from utils.database import (
    init_database, get_city_id, get_all_cities,
    insert_projects, search_projects, get_ward_stats, get_statistics,
    get_meetings, create_user, authenticate_user, get_user_by_id,
    insert_complaint, get_complaints_for_user, get_all_complaints,
    update_complaint_status, add_follow_up, remove_follow_up,
    get_followed_projects, DATABASE_PATH,
    insert_review, get_reviews_for_contractor, get_contractor_rating, has_user_reviewed,
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

app.register_blueprint(ward_bp, url_prefix="/api/wards")

def allowed_file(fn):
    return "." in fn and fn.rsplit(".", 1)[1].lower() == "pdf"


def get_current_user():
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
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


def require_authorized(f):
    """Allow admins and authorized_users to proceed."""
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user or user.get("role") not in ("admin", "authorized_user"):
            return jsonify({"error": "Authorized user access required"}), 403
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
    token = request.headers.get("Authorization", "").replace("Bearer ", "").strip() or request.cookies.get("token", "")
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

        # Extract both meeting metadata and projects
        result = extract_data_from_pdf(filepath)
        meeting_data = result["meeting"]
        projects = result["projects"]

        for p in projects:
            if not p.get("summary"):
                p["summary"] = generate_project_summary(p)

        inserted = insert_projects(projects, city_id=city_id)
        elapsed = time.perf_counter() - start

        # Insert meeting with extracted metadata
        conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
        conn.execute("""
            INSERT INTO meetings (city_id, ward_no, ward_name, meet_date, meet_type,
                venue, objective, attendees, projects_discussed, source_pdf, project_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            city_id,
            meeting_data.get("ward_no") or (projects[0].get("ward_no") if projects else None),
            meeting_data.get("ward_name") or (projects[0].get("ward_name") if projects else None),
            meeting_data.get("meet_date") or datetime.now().strftime("%Y-%m-%d"),
            meeting_data.get("meet_type") or "ward_committee",
            meeting_data.get("venue"),
            meeting_data.get("objective"),
            meeting_data.get("attendees"),
            meeting_data.get("projects_discussed"),
            filename,
            len(projects),
        ))
        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "message": f"Extracted {len(projects)} projects + meeting details in {elapsed:.1f}s",
            "projects_extracted": len(projects),
            "projects_inserted": inserted,
            "meeting": meeting_data,
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


@app.route("/api/wards/stats")
def api_wards_stats():
    """Ward stats in the shape WardMap expects."""
    cid = resolve_city_id()
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    params = []
    w = ""
    if cid:
        w = " AND city_id=?"
        params.append(cid)
    rows = conn.execute(f"""
        SELECT
            ward_no,
            MAX(ward_name) as ward_name,
            MAX(corporator_name) as corporator_name,
            COUNT(*) as total,
            SUM(CASE WHEN LOWER(status)='completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN LOWER(status)='delayed'   THEN 1 ELSE 0 END) as delayed,
            SUM(CASE WHEN LOWER(status)='in progress' OR LOWER(status)='ongoing' THEN 1 ELSE 0 END) as active,
            SUM(CASE WHEN LOWER(status)='stalled'   THEN 1 ELSE 0 END) as stalled,
            COALESCE(SUM(budget), 0) as total_budget,
            COALESCE(AVG(CASE WHEN delay_days > 0 THEN delay_days END), 0) as avg_delay_days
        FROM projects
        WHERE ward_no IS NOT NULL AND ward_no != ''
        {w}
        GROUP BY ward_no
        ORDER BY ward_no
    """, params).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        result.append({
            "wardNumber": d["ward_no"],
            "wardName": d["ward_name"] or f"Ward {d['ward_no']}",
            "corporatorName": d["corporator_name"] or "",
            "total": d["total"],
            "completed": d["completed"],
            "delayed": d["delayed"],
            "active": d["active"],
            "stalled": d["stalled"],
            "total_budget": d["total_budget"],
            "avg_delay_days": round(d["avg_delay_days"] or 0, 1),
        })
    return jsonify(result)


@app.route("/api/wards/geojson")
def api_wards_geojson():
    """Serve ward GeoJSON with CORS headers."""
    geojson_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "wards.geojson")
    if not os.path.exists(geojson_path):
        return jsonify({"type": "FeatureCollection", "features": []}), 200
    with open(geojson_path, "r", encoding="utf-8") as f:
        import json as _json
        raw = _json.load(f)
    features = []
    for feat in raw.get("features", []):
        try:
            wn = int(feat["properties"].get("note", 0))
        except (ValueError, TypeError):
            wn = 0
        features.append({
            "type": "Feature",
            "properties": {"wardNumber": wn, "wardName": f"Ward {wn}"},
            "geometry": feat["geometry"],
        })
    return jsonify({"type": "FeatureCollection", "features": features})


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


# ==================== CONTRACTORS ====================


@app.route("/api/contractors")
def api_contractors():
    cid = resolve_city_id()
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    params = []
    w = ""
    if cid:
        w = " AND city_id=?"
        params.append(cid)
    rows = conn.execute(f"""
        SELECT
            contractor_name,
            COUNT(*) as total_projects,
            SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status='delayed' THEN 1 ELSE 0 END) as delayed,
            SUM(CASE WHEN status='in progress' THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN status='stalled' THEN 1 ELSE 0 END) as stalled,
            COALESCE(SUM(budget), 0) as total_budget,
            COALESCE(AVG(CASE WHEN delay_days > 0 THEN delay_days END), 0) as avg_delay_days,
            MAX(delay_days) as max_delay_days,
            COUNT(DISTINCT ward_no) as wards_count,
            GROUP_CONCAT(DISTINCT project_type) as project_types
        FROM projects
        WHERE contractor_name IS NOT NULL AND contractor_name != ''
        {w}
        GROUP BY contractor_name
        ORDER BY total_projects DESC
    """, params).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        total = d["total_projects"] or 1
        d["delay_pct"] = round((d["delayed"] / total) * 100, 1)
        d["completion_pct"] = round((d["completed"] / total) * 100, 1)
        d["project_types"] = [t for t in (d["project_types"] or "").split(",") if t]
        result.append(d)
    return jsonify({"contractors": result, "count": len(result)})


@app.route("/api/contractor-projects")
def api_contractor_projects():
    """Get projects for a specific contractor using ?name= query param."""
    contractor_name = request.args.get("name", "").strip()
    if not contractor_name:
        return jsonify({"error": "name parameter required"}), 400
    cid = resolve_city_id()
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    params = [contractor_name]
    w = ""
    if cid:
        w = " AND p.city_id=?"
        params.append(cid)
    projects_rows = conn.execute(f"""
        SELECT p.*, c.city_name FROM projects p
        JOIN city c ON p.city_id=c.city_id
        WHERE LOWER(p.contractor_name)=LOWER(?) {w}
        ORDER BY p.delay_days DESC, p.created_at DESC
    """, params).fetchall()
    conn.close()
    return jsonify({"projects": [dict(r) for r in projects_rows], "count": len(projects_rows)})


# ==================== CONTRACTOR REVIEWS ====================


@app.route("/api/contractors/reviews")
def api_get_contractor_reviews():
    """Get all reviews + aggregate rating for a contractor. ?name= required."""
    contractor_name = request.args.get("name", "").strip()
    if not contractor_name:
        return jsonify({"error": "name parameter required"}), 400
    reviews = get_reviews_for_contractor(contractor_name)
    rating_info = get_contractor_rating(contractor_name)
    # Check if current user already reviewed
    current_user = get_current_user()
    user_review = None
    if current_user:
        user_review = has_user_reviewed(contractor_name, current_user["id"])
    return jsonify({
        "reviews": reviews,
        "avg_rating": rating_info["avg_rating"],
        "review_count": rating_info["review_count"],
        "user_review": user_review,
    })


@app.route("/api/contractors/reviews", methods=["POST"])
@require_authorized
def api_submit_contractor_review():
    """Submit or update a review. Only admins and authorized_users allowed."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400
    contractor_name = (data.get("contractor_name") or "").strip()
    rating = data.get("rating")
    if not contractor_name:
        return jsonify({"error": "contractor_name required"}), 400
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return jsonify({"error": "rating must be integer 1–5"}), 400
    rid = insert_review(
        contractor_name=contractor_name,
        reviewer_id=g.user["id"],
        rating=rating,
        title=data.get("title"),
        body=data.get("body"),
    )
    if rid is None:
        return jsonify({"error": "Could not save review"}), 500
    return jsonify({"success": True, "review_id": rid})


@app.route("/api/admin/promote-user", methods=["POST"])
@require_admin
def api_promote_user():
    """Admin-only: set a user's role to authorized_user or user."""
    data = request.get_json()
    username = (data or {}).get("username", "").strip()
    role = (data or {}).get("role", "authorized_user")
    if not username:
        return jsonify({"error": "username required"}), 400
    if role not in ("user", "authorized_user", "admin"):
        return jsonify({"error": "invalid role"}), 400
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.execute("UPDATE users SET role=? WHERE username=?", (role, username))
    conn.commit()
    affected = conn.execute("SELECT changes()").fetchone()[0]
    conn.close()
    if not affected:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"success": True, "username": username, "new_role": role})


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
