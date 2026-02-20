import sqlite3
from datetime import datetime
import os
import hashlib
import secrets

DATABASE_PATH = os.environ.get("DATABASE_PATH", "jansaakshi.db")


def get_db():
    """Get a database connection with row_factory set."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_database():
    """Initialize database with complete schema."""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    cursor = conn.cursor()

    # Users
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            city TEXT DEFAULT 'mumbai',
            ward_number TEXT,
            role TEXT DEFAULT 'user',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Projects
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT DEFAULT 'mumbai',
            project_name TEXT NOT NULL,
            summary TEXT,
            ward_number TEXT,
            ward_name TEXT,
            budget_amount REAL,
            corporator_name TEXT,
            contractor_name TEXT,
            responsible_official TEXT,
            approval_date TEXT,
            expected_completion TEXT,
            actual_completion TEXT,
            project_type TEXT,
            status TEXT,
            delay_days INTEGER DEFAULT 0,
            location_details TEXT,
            coordinates_lat REAL,
            coordinates_lng REAL,
            source_pdf TEXT,
            extracted_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_city ON projects(city)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_ward ON projects(ward_number)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_type ON projects(project_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_projects_delay ON projects(delay_days)")

    # Meetings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT DEFAULT 'mumbai',
            ward_number TEXT,
            ward_name TEXT,
            meeting_date TEXT,
            meeting_type TEXT,
            venue TEXT,
            objective TEXT,
            attendees TEXT,
            projects_discussed TEXT,
            pdf_filename TEXT,
            projects_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Wards
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT DEFAULT 'mumbai',
            ward_number TEXT,
            ward_name TEXT,
            center_lat REAL,
            center_lng REAL,
            corporator_name TEXT,
            corporator_party TEXT,
            UNIQUE(city, ward_number)
        )
    """)

    # Complaints
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT DEFAULT 'mumbai',
            user_id INTEGER,
            ward_number TEXT,
            category TEXT,
            description TEXT,
            location TEXT,
            citizen_name TEXT,
            citizen_phone TEXT,
            status TEXT DEFAULT 'submitted',
            admin_notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Follow-ups (users tracking specific projects)
    cursor.execute("""
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

    conn.commit()
    conn.close()
    print("Database initialized")


# ==================== AUTH ====================


def hash_password(password):
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}:{h}"


def verify_password(password, stored):
    salt, h = stored.split(":")
    return hashlib.sha256((salt + password).encode()).hexdigest() == h


def create_user(username, password, display_name=None, city="mumbai", ward_number=None, role="user"):
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash, display_name, city, ward_number, role) VALUES (?,?,?,?,?,?)",
            (username, hash_password(password), display_name or username, city, ward_number, role),
        )
        conn.commit()
        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        conn.close()
        return None


def authenticate_user(username, password):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if row and verify_password(password, row["password_hash"]):
        return dict(row)
    return None


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute("SELECT id, username, display_name, city, ward_number, role, created_at FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ==================== PROJECTS ====================


def insert_projects(projects_list, city="mumbai"):
    conn = get_db()
    inserted = 0
    for p in projects_list:
        try:
            conn.execute("""
                INSERT INTO projects (
                    city, project_name, summary, ward_number, ward_name,
                    budget_amount, corporator_name, contractor_name,
                    approval_date, expected_completion, project_type,
                    status, delay_days, location_details, source_pdf,
                    extracted_at, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                city,
                p.get("project_name"), p.get("summary"),
                p.get("ward_number"), p.get("ward_name"),
                p.get("budget_amount"), p.get("corporator_name"),
                p.get("contractor_name"), p.get("approval_date"),
                p.get("expected_completion"), p.get("project_type"),
                p.get("status"), p.get("delay_days", 0),
                p.get("location_details"), p.get("source_pdf"),
                p.get("extracted_at"), datetime.now().isoformat(),
            ))
            inserted += 1
        except Exception as e:
            print(f"Insert error: {e}")
    conn.commit()
    conn.close()
    return inserted


def search_projects(city=None, ward_number=None, ward_name=None,
                    project_type=None, status=None, keyword=None,
                    corporator=None, min_delay=None):
    conn = get_db()
    q = "SELECT * FROM projects WHERE 1=1"
    params = []

    if city:
        q += " AND city = ?"
        params.append(city)
    if ward_number:
        q += " AND ward_number = ?"
        params.append(str(ward_number))
    if ward_name:
        q += " AND LOWER(ward_name) LIKE ?"
        params.append(f"%{ward_name.lower()}%")
    if project_type:
        q += " AND project_type = ?"
        params.append(project_type)
    if status:
        q += " AND status = ?"
        params.append(status)
    if keyword:
        q += " AND (LOWER(project_name) LIKE ? OR LOWER(location_details) LIKE ? OR LOWER(summary) LIKE ?)"
        kw = f"%{keyword.lower()}%"
        params.extend([kw, kw, kw])
    if corporator:
        q += " AND LOWER(corporator_name) LIKE ?"
        params.append(f"%{corporator.lower()}%")
    if min_delay:
        q += " AND delay_days >= ?"
        params.append(int(min_delay))

    q += " ORDER BY created_at DESC LIMIT 100"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ward_stats(city=None):
    conn = get_db()
    q = """
        SELECT ward_number, ward_name,
            COUNT(*) as total_projects,
            SUM(CASE WHEN status='delayed' THEN 1 ELSE 0 END) as delayed_projects,
            SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed_projects,
            SUM(budget_amount) as total_budget,
            MAX(corporator_name) as corporator_name
        FROM projects WHERE ward_number IS NOT NULL
    """
    params = []
    if city:
        q += " AND city = ?"
        params.append(city)
    q += " GROUP BY ward_number ORDER BY ward_number"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_statistics(city=None):
    conn = get_db()
    where = " WHERE city = ?" if city else ""
    params = [city] if city else []

    stats = {}
    stats["total_projects"] = conn.execute(f"SELECT COUNT(*) FROM projects{where}", params).fetchone()[0]
    stats["delayed_projects"] = conn.execute(f"SELECT COUNT(*) FROM projects{where} {'AND' if city else 'WHERE'} status='delayed'", params).fetchone()[0]
    stats["total_budget"] = conn.execute(f"SELECT COALESCE(SUM(budget_amount),0) FROM projects{where}", params).fetchone()[0]
    stats["delayed_budget"] = conn.execute(f"SELECT COALESCE(SUM(budget_amount),0) FROM projects{where} {'AND' if city else 'WHERE'} status='delayed'", params).fetchone()[0]
    stats["total_wards"] = conn.execute(f"SELECT COUNT(DISTINCT ward_number) FROM projects{where}", params).fetchone()[0]
    conn.close()
    return stats


# ==================== MEETINGS ====================


def get_meetings(city=None, ward_number=None):
    conn = get_db()
    q = "SELECT * FROM meetings WHERE 1=1"
    params = []
    if city:
        q += " AND city = ?"
        params.append(city)
    if ward_number:
        q += " AND ward_number = ?"
        params.append(ward_number)
    q += " ORDER BY meeting_date DESC LIMIT 50"
    rows = conn.execute(q, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==================== COMPLAINTS ====================


def insert_complaint(data, user_id=None, city="mumbai"):
    conn = get_db()
    conn.execute("""
        INSERT INTO complaints (city, user_id, ward_number, category, description, location, citizen_name, citizen_phone)
        VALUES (?,?,?,?,?,?,?,?)
    """, (
        city, user_id, data.get("ward_number"), data.get("category"),
        data.get("description"), data.get("location"),
        data.get("citizen_name"), data.get("citizen_phone"),
    ))
    cid = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    conn.commit()
    conn.close()
    return cid


def get_complaints_for_user(user_id):
    conn = get_db()
    rows = conn.execute("SELECT * FROM complaints WHERE user_id = ? ORDER BY created_at DESC", (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_complaints(city=None):
    conn = get_db()
    q = "SELECT * FROM complaints"
    params = []
    if city:
        q += " WHERE city = ?"
        params.append(city)
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
        SELECT p.* FROM projects p
        JOIN follow_ups f ON p.id = f.project_id
        WHERE f.user_id = ?
        ORDER BY p.updated_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
