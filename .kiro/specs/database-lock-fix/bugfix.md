# Bugfix Requirements Document

## Introduction

The Flask application crashes on startup with a SQLite "database is locked" error during database initialization. The error occurs at line 158 in `Backend/utils/database.py` when executing `CREATE TABLE sessions`. The database is in WAL (Write-Ahead Logging) mode as evidenced by the presence of `.db-shm` and `.db-wal` files. This prevents the application from starting successfully.

The root cause is that `init_database()` creates its own connection without enabling WAL mode or proper timeout handling, while `get_db()` (used elsewhere) creates connections with WAL mode enabled and a 30-second timeout. This mismatch can lead to lock contention during initialization.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN `init_database()` is called during app startup THEN the system raises `sqlite3.OperationalError: database is locked` at line 158 during `CREATE TABLE sessions` execution

1.2 WHEN `init_database()` creates a connection without WAL mode enabled THEN the system fails to coordinate with existing WAL-mode connections or leftover WAL files

1.3 WHEN the database lock error occurs THEN the system crashes and prevents the Flask application from starting

### Expected Behavior (Correct)

2.1 WHEN `init_database()` is called during app startup THEN the system SHALL successfully create all tables including the sessions table without raising a database lock error

2.2 WHEN `init_database()` creates a database connection THEN the system SHALL enable WAL mode and use appropriate timeout settings consistent with `get_db()`

2.3 WHEN database initialization completes THEN the system SHALL allow the Flask application to start successfully

### Unchanged Behavior (Regression Prevention)

3.1 WHEN `get_db()` is called to create database connections THEN the system SHALL CONTINUE TO return connections with WAL mode enabled, foreign keys enabled, and 30-second timeout

3.2 WHEN database tables already exist THEN the system SHALL CONTINUE TO use `CREATE TABLE IF NOT EXISTS` to avoid errors

3.3 WHEN schema migration is needed (city table doesn't exist) THEN the system SHALL CONTINUE TO drop old tables and recreate them

3.4 WHEN seed data is inserted THEN the system SHALL CONTINUE TO use `INSERT OR IGNORE` to avoid duplicate key errors

3.5 WHEN any database operation is performed after initialization THEN the system SHALL CONTINUE TO function correctly with proper data integrity and foreign key constraints
