import sqlite3
from datetime import datetime
import os
import hashlib
import secrets

DATABASE_PATH = os.environ.get("DATABASE_PATH", "jansaakshi.db")


def get_db():
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_database():
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    c = conn.cursor()

    # Schema migration: drop old tables if city table doesn't exist
    try:
        c.execute("SELECT 1 FROM city LIMIT 1")
    except sqlite3.OperationalError:
        print("Schema migration: dropping old tables...")
        for t in ["follow_ups", "complaints", "meetings", "projects", "users", "city"]:
            c.execute(f"DROP TABLE IF EXISTS {t}")
        conn.commit()

    # City table (FK source)
    c.execute("""
        CREATE TABLE IF NOT EXISTS city (
            city_id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_name TEXT NOT NULL UNIQUE,
            state TEXT NOT NULL
        )
    """)

    # Users
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            display_name TEXT,
            city_id INTEGER,
            ward TEXT,
            role TEXT DEFAULT 'user',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (city_id) REFERENCES city(city_id)
        )
    """)

    # Projects
    c.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_id INTEGER NOT NULL,
            project_name TEXT NOT NULL,
            summary TEXT,
            ward_no TEXT,
            ward_name TEXT,
            ward_zone TEXT,
            status TEXT,
            budget REAL,
            corporator_name TEXT,
            contractor_name TEXT,
            project_type TEXT,
            approval_date TEXT,
            start_date TEXT,
            expected_completion TEXT,
            actual_completion TEXT,
            delay_days INTEGER DEFAULT 0,
            location_details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
            source_pdf TEXT,
            FOREIGN KEY (city_id) REFERENCES city(city_id)
        )
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_proj_city ON projects(city_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_proj_ward ON projects(ward_no)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_proj_status ON projects(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_proj_type ON projects(project_type)")

    # Meetings
    c.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_id INTEGER NOT NULL,
            ward_no TEXT,
            ward_name TEXT,
            meet_date TEXT,
            meet_type TEXT,
            venue TEXT,
            objective TEXT,
            attendees TEXT,
            projects_discussed TEXT,
            source_pdf TEXT,
            project_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (city_id) REFERENCES city(city_id)
        )
    """)

    # Complaints
    c.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city_id INTEGER,
            user_id INTEGER,
            ward_no TEXT,
            category TEXT,
            description TEXT,
            location TEXT,
            citizen_name TEXT,
            user_phone TEXT,
            status TEXT DEFAULT 'submitted',
            admin_notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (city_id) REFERENCES city(city_id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Follow-ups
    c.execute("""
        CREATE TABLE IF NOT EXISTS follow_ups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            project_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (project_id) REFERENCES projects(id),
            UNIQUE(user_id, project_id)
        )
    """)

    # Contractor Reviews
    c.execute("""
        CREATE TABLE IF NOT EXISTS contractor_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contractor_name TEXT NOT NULL,
            reviewer_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            title TEXT,
            body TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (reviewer_id) REFERENCES users(id),
            UNIQUE(contractor_name, reviewer_id)
        )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_review_contractor ON contractor_reviews(contractor_name)")

    # Seed cities
    c.execute("INSERT OR IGNORE INTO city (city_name, state) VALUES ('mumbai', 'Maharashtra')")
    c.execute("INSERT OR IGNORE INTO city (city_name, state) VALUES ('delhi', 'Delhi')")

    conn.commit()
    conn.close()
    print("Database initialized")


# ==================== CITY ====================


def get_city_id(city_name):
    conn = get_db()
    row = conn.execute("SELECT city_id FROM city WHERE city_name=?", (city_name,)).fetchone()
    conn.close()
    return row["city_id"] if row else None


def get_all_cities():
    conn = get_db()
    rows = conn.execute("SELECT * FROM city").fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==================== AUTH ====================


def hash_password(password):
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"


def verify_password(password, stored):
    salt, h = stored.split(":")
    return hashlib.sha256((salt + password).encode()).hexdigest() == h


def create_user(username, password, display_name=None, city_id=None, ward=None, role="user"):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password, display_name, city_id, ward, role) VALUES (?,?,?,?,?,?)",
            (username, hash_password(password), display_name or username, city_id, ward, role),
        )
        conn.commit()
        uid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return uid
    except sqlite3.IntegrityError:
        conn.close()
        return None


def authenticate_user(username, password):
    conn = get_db()
    row = conn.execute("""
        SELECT u.*, c.city_name FROM users u
        LEFT JOIN city c ON u.city_id = c.city_id
        WHERE u.username = ?
    """, (username,)).fetchone()
    conn.close()
    if row and verify_password(password, row["password"]):
        return dict(row)
    return None


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute("""
        SELECT u.id, u.username, u.display_name, u.city_id, c.city_name, u.ward, u.role, u.created_at
        FROM users u LEFT JOIN city c ON u.city_id = c.city_id
        WHERE u.id = ?
    """, (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ==================== PROJECTS ====================


def insert_projects(projects_list, city_id):
    conn = get_db()
    inserted = 0
    for p in projects_list:
        try:
            conn.execute("""
                INSERT INTO projects (
                    city_id, project_name, summary, ward_no, ward_name, ward_zone,
                    status, budget, corporator_name, contractor_name, project_type,
                    approval_date, start_date, expected_completion, actual_completion,
                    delay_days, location_details, source_pdf, created_at, updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                city_id, p.get("project_name"), p.get("summary"),
                p.get("ward_no"), p.get("ward_name"), p.get("ward_zone"),
                p.get("status"), p.get("budget"), p.get("corporator_name"),
                p.get("contractor_name"), p.get("project_type"),
                p.get("approval_date"), p.get("start_date"),
                p.get("expected_completion"), p.get("actual_completion"),
                p.get("delay_days", 0), p.get("location_details"),
                p.get("source_pdf"), datetime.now().isoformat(), datetime.now().isoformat(),
            ))
            inserted += 1
        except Exception as e:
            print(f"Insert error: {e}")
    conn.commit()
    conn.close()
    return inserted


def search_projects(city_id=None, ward_no=None, ward_name=None,
                    project_type=None, status=None, keyword=None,
                    corporator=None, min_delay=None):
    conn = get_db()
    q = "SELECT p.*, c.city_name FROM projects p JOIN city c ON p.city_id=c.city_id WHERE 1=1"
    params = []

    if city_id:
        q += " AND p.city_id=?"
        params.append(city_id)
    if ward_no:
        q += " AND p.ward_no=?"
        params.append(str(ward_no))
    if ward_name:
        q += " AND LOWER(p.ward_name) LIKE ?"
        params.append(f"%{ward_name.lower()}%")
    if project_type:
        q += " AND p.project_type=?"
        params.append(project_type)
    if status:
        q += " AND p.status=?"
        params.append(status)
    if keyword:
        # Smart keyword search: split into words, match ANY word across all text fields
        # This enables "Eastern Freeway Extension" to match projects containing any of those words
        words = [w.strip() for w in keyword.lower().split() if len(w.strip()) >= 2]
        stop_words = {"the", "is", "in", "at", "of", "on", "for", "to", "and", "or", "an",
                       "what", "how", "which", "where", "when", "show", "tell", "me", "my",
                       "are", "has", "have", "with", "about", "update", "status", "projects"}
        words = [w for w in words if w not in stop_words] or [keyword.lower()]

        if words:
            word_clauses = []
            for w in words:
                wk = f"%{w}%"
                word_clauses.append(
                    "(LOWER(p.project_name) LIKE ? OR LOWER(p.summary) LIKE ? "
                    "OR LOWER(p.location_details) LIKE ? OR LOWER(p.ward_name) LIKE ? "
                    "OR LOWER(p.contractor_name) LIKE ? OR LOWER(p.corporator_name) LIKE ?)"
                )
                params.extend([wk, wk, wk, wk, wk, wk])
            # Match ANY word (OR logic for broader results)
            q += " AND (" + " OR ".join(word_clauses) + ")"
    if corporator:
        q += " AND LOWER(p.corporator_name) LIKE ?"
        params.append(f"%{corporator.lower()}%")
    if min_delay:
        q += " AND p.delay_days>=?"
        params.append(int(min_delay))

    q += " ORDER BY p.delay_days DESC, p.created_at DESC LIMIT 100"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    results = [dict(r) for r in rows]

    # Rank results by relevance: count how many keywords match
    if keyword and results:
        words = [w.strip() for w in keyword.lower().split() if len(w.strip()) >= 2]
        words = [w for w in words if w not in stop_words] or [keyword.lower()]
        for r in results:
            searchable = " ".join([
                (r.get("project_name") or ""), (r.get("summary") or ""),
                (r.get("location_details") or ""), (r.get("ward_name") or ""),
                (r.get("contractor_name") or ""), (r.get("corporator_name") or ""),
            ]).lower()
            r["_relevance"] = sum(1 for w in words if w in searchable)
        results.sort(key=lambda x: (-x.get("_relevance", 0), -x.get("delay_days", 0)))
        for r in results:
            r.pop("_relevance", None)

    return results


def get_ward_stats(city_id=None):
    conn = get_db()
    q = """
        SELECT ward_no, ward_name, ward_zone,
            COUNT(*) as total_projects,
            SUM(CASE WHEN status='delayed' THEN 1 ELSE 0 END) as delayed_projects,
            SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed_projects,
            SUM(CASE WHEN status='stalled' THEN 1 ELSE 0 END) as stalled_projects,
            SUM(budget) as total_budget,
            MAX(corporator_name) as corporator_name
        FROM projects WHERE ward_no IS NOT NULL
    """
    params = []
    if city_id:
        q += " AND city_id=?"
        params.append(city_id)
    q += " GROUP BY ward_no ORDER BY ward_no"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_statistics(city_id=None):
    conn = get_db()
    w = " WHERE city_id=?" if city_id else ""
    p = [city_id] if city_id else []
    a = " AND" if city_id else " WHERE"

    stats = {}
    stats["total_projects"] = conn.execute(f"SELECT COUNT(*) FROM projects{w}", p).fetchone()[0]
    stats["delayed_projects"] = conn.execute(f"SELECT COUNT(*) FROM projects{w}{a} status='delayed'", p).fetchone()[0]
    stats["total_budget"] = conn.execute(f"SELECT COALESCE(SUM(budget),0) FROM projects{w}", p).fetchone()[0]
    stats["delayed_budget"] = conn.execute(f"SELECT COALESCE(SUM(budget),0) FROM projects{w}{a} status='delayed'", p).fetchone()[0]
    stats["total_wards"] = conn.execute(f"SELECT COUNT(DISTINCT ward_no) FROM projects{w}", p).fetchone()[0]
    conn.close()
    return stats


# ==================== MEETINGS ====================


def get_meetings(city_id=None, ward_no=None):
    conn = get_db()
    q = "SELECT m.*, c.city_name FROM meetings m JOIN city c ON m.city_id=c.city_id WHERE 1=1"
    params = []
    if city_id:
        q += " AND m.city_id=?"
        params.append(city_id)
    if ward_no:
        q += " AND m.ward_no=?"
        params.append(ward_no)
    q += " ORDER BY m.meet_date DESC LIMIT 50"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==================== COMPLAINTS ====================


def insert_complaint(data, user_id=None, city_id=None):
    conn = get_db()
    conn.execute("""
        INSERT INTO complaints (city_id, user_id, ward_no, category, description, location, citizen_name, user_phone)
        VALUES (?,?,?,?,?,?,?,?)
    """, (
        city_id, user_id, data.get("ward_no"), data.get("category"),
        data.get("description"), data.get("location"),
        data.get("citizen_name"), data.get("user_phone"),
    ))
    cid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return cid


def get_complaints_for_user(user_id):
    conn = get_db()
    rows = conn.execute("SELECT * FROM complaints WHERE user_id=? ORDER BY created_at DESC", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_complaints(city_id=None):
    conn = get_db()
    q = "SELECT * FROM complaints"
    params = []
    if city_id:
        q += " WHERE city_id=?"
        params.append(city_id)
    q += " ORDER BY created_at DESC LIMIT 100"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_complaint_status(complaint_id, status, admin_notes=None):
    conn = get_db()
    conn.execute("UPDATE complaints SET status=?, admin_notes=? WHERE id=?", (status, admin_notes, complaint_id))
    conn.commit()
    conn.close()


# ==================== FOLLOW-UPS ====================


def add_follow_up(user_id, project_id):
    conn = get_db()
    try:
        conn.execute("INSERT INTO follow_ups (user_id, project_id) VALUES (?,?)", (user_id, project_id))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False


def remove_follow_up(user_id, project_id):
    conn = get_db()
    conn.execute("DELETE FROM follow_ups WHERE user_id=? AND project_id=?", (user_id, project_id))
    conn.commit()
    conn.close()


def get_followed_projects(user_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT p.*, c.city_name FROM projects p
        JOIN city c ON p.city_id=c.city_id
        JOIN follow_ups f ON p.id=f.project_id
        WHERE f.user_id=?
        ORDER BY p.updated_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==================== CONTRACTOR REVIEWS ====================


def insert_review(contractor_name, reviewer_id, rating, title=None, body=None):
    """Insert or replace a review for a contractor by a user. Returns review id or None on error."""
    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO contractor_reviews (contractor_name, reviewer_id, rating, title, body)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(contractor_name, reviewer_id) DO UPDATE SET
                rating=excluded.rating, title=excluded.title,
                body=excluded.body, created_at=CURRENT_TIMESTAMP
        """, (contractor_name, reviewer_id, rating, title, body))
        conn.commit()
        rid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return rid
    except Exception as e:
        conn.close()
        print(f"Review insert error: {e}")
        return None


def get_reviews_for_contractor(contractor_name):
    conn = get_db()
    rows = conn.execute("""
        SELECT cr.*, u.display_name, u.username
        FROM contractor_reviews cr
        JOIN users u ON cr.reviewer_id = u.id
        WHERE LOWER(cr.contractor_name) = LOWER(?)
        ORDER BY cr.created_at DESC
    """, (contractor_name,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_contractor_rating(contractor_name):
    """Returns dict with avg_rating and review_count."""
    conn = get_db()
    row = conn.execute("""
        SELECT AVG(rating) as avg_rating, COUNT(*) as review_count
        FROM contractor_reviews WHERE LOWER(contractor_name) = LOWER(?)
    """, (contractor_name,)).fetchone()
    conn.close()
    if row:
        return {"avg_rating": round(row["avg_rating"] or 0, 1), "review_count": row["review_count"]}
    return {"avg_rating": 0, "review_count": 0}


def has_user_reviewed(contractor_name, reviewer_id):
    conn = get_db()
    row = conn.execute("""
        SELECT id, rating FROM contractor_reviews
        WHERE LOWER(contractor_name)=LOWER(?) AND reviewer_id=?
    """, (contractor_name, reviewer_id)).fetchone()
    conn.close()
    return dict(row) if row else None

