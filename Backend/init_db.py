"""
Initialize the JanSaakshi database with sample project data
Run this once to set up the database
"""

import sqlite3
from datetime import datetime, timedelta

DB_PATH = "DATA_DB.db"

def init_database():
    """Create tables and insert sample data"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create PROJECT_DATA table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS PROJECT_DATA (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ward TEXT,
        ward_no INTEGER,
        project_name TEXT,
        budget TEXT,
        deadline TEXT,
        responsible_person TEXT,
        contractor TEXT,
        body_text TEXT,
        status TEXT
    )
    ''')
   
    conn.close()

if __name__ == "__main__":
    init_database()
