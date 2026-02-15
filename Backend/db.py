"""
JanSaakshi Database Layer
Handles:
- SQLite connection
- Sessions
- Transactions
- Table creation
- Utility helpers
"""

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
from typing import Generator, Optional, List, Dict, Any
import logging
import os

# =====================================================
# CONFIGURATION
# =====================================================

DB_FILE = os.getenv("DB_FILE", "jansaakshi.db")
DATABASE_URL = f"sqlite:///./{DB_FILE}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DB")

# =====================================================
# ENGINE (SQLite optimized for FastAPI)
# =====================================================

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,  # prevents threading issues
    echo=False  # set True to debug SQL queries
)

# Enable foreign keys in SQLite
@event.listens_for(engine, "connect")
def enable_sqlite_fk(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# =====================================================
# SESSION FACTORY
# =====================================================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# =====================================================
# FASTAPI DEPENDENCY
# =====================================================

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency.
    Creates DB session per request and closes after response.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =====================================================
# TRANSACTION CONTEXT MANAGER
# =====================================================

@contextmanager
def db_transaction() -> Generator[Session, None, None]:
    """
    Use this for background jobs or scripts
    Ensures rollback on error
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Transaction rolled back: {e}")
        raise
    finally:
        db.close()

# =====================================================
# DATABASE INIT
# =====================================================

def init_db():
    """
    Creates all tables automatically.
    Call once on app startup.
    """
    logger.info("Creating database tables if not exist...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database ready.")

# =====================================================
# GENERIC HELPERS
# =====================================================

def save(db: Session, obj):
    """
    Save single object
    """
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def bulk_save(db: Session, objects: List[Any]):
    """
    Bulk insert
    """
    db.add_all(objects)
    db.commit()
    return objects


def delete(db: Session, obj):
    """
    Delete record
    """
    db.delete(obj)
    db.commit()


def update(db: Session):
    """
    Commit updates after modifying object
    """
    db.commit()

# =====================================================
# RAW SQL EXECUTION (for complex filters)
# =====================================================

def execute_sql(db: Session, query: str, params: Optional[Dict] = None):
    """
    Execute raw SQL safely
    Useful for search filters
    """
    result = db.execute(text(query), params or {})
    return result.fetchall()

# =====================================================
# PAGINATION
# =====================================================

def paginate(query, page: int = 1, limit: int = 10):
    """
    Generic pagination helper
    """
    if page < 1:
        page = 1

    offset = (page - 1) * limit
    return query.offset(offset).limit(limit)

# =====================================================
# HEALTH CHECK
# =====================================================

def check_connection() -> bool:
    """
    Verify DB connection
    Used in /health endpoint
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"DB connection failed: {e}")
        return False