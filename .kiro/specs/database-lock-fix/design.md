# Database Lock Fix Bugfix Design

## Overview

The Flask application crashes on startup with a SQLite "database is locked" error during database initialization. The root cause is a configuration mismatch: `init_database()` creates a connection without enabling WAL (Write-Ahead Logging) mode or foreign keys, while `get_db()` creates connections with WAL mode enabled and foreign keys enforced. This inconsistency causes lock contention when `init_database()` attempts to create tables while WAL files exist from previous runs.

The fix is straightforward: make `init_database()` use the same connection configuration as `get_db()` by enabling WAL mode and foreign keys. This ensures all connections use consistent locking behavior and can coexist with existing WAL files.

## Glossary

- **Bug_Condition (C)**: The condition that triggers the bug - when `init_database()` creates a connection without WAL mode while WAL files exist or other WAL-mode connections are active
- **Property (P)**: The desired behavior - database initialization completes successfully without lock errors
- **Preservation**: All existing database operations, connection handling, and data integrity constraints must remain unchanged
- **WAL Mode**: Write-Ahead Logging mode in SQLite that allows concurrent reads and writes by using separate log files (.db-wal and .db-shm)
- **init_database()**: The function in `Backend/utils/database.py` (line 18) that creates database tables and seed data during app startup
- **get_db()**: The function in `Backend/utils/database.py` (line 10) that creates database connections for runtime operations with WAL mode enabled

## Bug Details

### Fault Condition

The bug manifests when `init_database()` is called during Flask application startup and attempts to create tables while the database is in WAL mode (evidenced by .db-wal and .db-shm files) or when other connections with WAL mode are active. The `init_database()` function creates a connection without enabling WAL mode, causing it to be incompatible with the existing WAL-mode database state, leading to lock contention at line 158 during `CREATE TABLE sessions` execution.

**Formal Specification:**
```
FUNCTION isBugCondition(input)
  INPUT: input of type DatabaseInitializationContext
  OUTPUT: boolean
  
  RETURN input.function == 'init_database()'
         AND input.connection.wal_mode_enabled == False
         AND (input.database.wal_files_exist == True 
              OR input.database.active_wal_connections > 0)
         AND input.operation == 'CREATE TABLE sessions'
END FUNCTION
```

### Examples

- **Example 1**: App starts, .db-wal file exists from previous run, `init_database()` creates non-WAL connection → raises `sqlite3.OperationalError: database is locked` at line 158
- **Example 2**: App restarts after crash, WAL files present, `init_database()` attempts table creation → database lock error prevents startup
- **Example 3**: Multiple workers/processes start simultaneously, one uses `get_db()` with WAL, another runs `init_database()` without WAL → lock contention occurs
- **Edge Case**: Fresh database with no WAL files, `init_database()` runs successfully but creates inconsistency for future runs when WAL mode is later enabled by `get_db()`

## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- `get_db()` must continue to return connections with WAL mode enabled, foreign keys enabled, and 30-second timeout
- All database operations using `get_db()` must continue to function correctly with proper data integrity
- Schema migration logic (dropping old tables when city table doesn't exist) must continue to work
- Seed data insertion using `INSERT OR IGNORE` must continue to avoid duplicate key errors
- All table creation using `CREATE TABLE IF NOT EXISTS` must continue to be idempotent
- Foreign key constraints must continue to be enforced for all operations

**Scope:**
All database operations that do NOT involve `init_database()` should be completely unaffected by this fix. This includes:
- All runtime database queries through `get_db()`
- User authentication and session management
- Project, complaint, meeting, and review operations
- Data integrity and foreign key constraint enforcement

## Hypothesized Root Cause

Based on the bug description and code analysis, the root cause is:

1. **Configuration Mismatch**: `init_database()` creates a connection with `sqlite3.connect(DATABASE_PATH, timeout=30.0)` but does NOT execute `PRAGMA journal_mode=WAL` or `PRAGMA foreign_keys=ON`, while `get_db()` does execute both pragmas. This creates two different connection configurations in the same application.

2. **WAL Mode Incompatibility**: When the database is in WAL mode (from previous `get_db()` calls or leftover .db-wal files), a non-WAL connection cannot acquire the necessary locks for DDL operations like `CREATE TABLE`. SQLite's locking protocol differs between rollback journal mode and WAL mode.

3. **Lock Contention at Table Creation**: The error occurs specifically at line 158 during `CREATE TABLE sessions`, which is the last table creation statement. By this point, the connection has already executed multiple DDL statements, but the cumulative lock requirements or a specific timing issue causes the lock error at this particular statement.

4. **Missing Foreign Key Enforcement**: While not directly causing the lock error, `init_database()` also fails to enable foreign keys, creating an inconsistency where tables are created without foreign key enforcement but later operations expect it to be enabled.

## Correctness Properties

Property 1: Fault Condition - Database Initialization Succeeds Without Lock Errors

_For any_ database initialization call where `init_database()` is invoked during app startup (regardless of whether WAL files exist or other connections are active), the fixed function SHALL successfully create all tables including the sessions table without raising a `sqlite3.OperationalError: database is locked` error, and the Flask application SHALL start successfully.

**Validates: Requirements 2.1, 2.2, 2.3**

Property 2: Preservation - Existing Database Operations Unchanged

_For any_ database operation that does NOT involve `init_database()` (all runtime queries, user operations, data manipulation through `get_db()`), the fixed code SHALL produce exactly the same behavior as the original code, preserving connection configuration (WAL mode, foreign keys, timeout), data integrity, and all functional behavior.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

## Fix Implementation

### Changes Required

Assuming our root cause analysis is correct:

**File**: `Backend/utils/database.py`

**Function**: `init_database()` (line 18)

**Specific Changes**:
1. **Enable WAL Mode**: Add `conn.execute("PRAGMA journal_mode=WAL")` immediately after creating the connection (after line 19) to ensure the initialization connection uses the same journal mode as runtime connections

2. **Enable Foreign Keys**: Add `conn.execute("PRAGMA foreign_keys=ON")` immediately after enabling WAL mode to ensure foreign key constraints are enforced during table creation and seed data insertion

3. **Set Row Factory (Optional but Recommended)**: Add `conn.row_factory = sqlite3.Row` for consistency with `get_db()`, though this is not strictly necessary for initialization since we don't fetch rows

4. **Alternative Approach**: Consider refactoring to use `get_db()` directly within `init_database()` instead of creating a separate connection, which would automatically ensure configuration consistency

5. **Verification**: Ensure the connection configuration matches `get_db()` exactly:
   - Timeout: 30.0 seconds ✓ (already present)
   - WAL mode: Add `PRAGMA journal_mode=WAL`
   - Foreign keys: Add `PRAGMA foreign_keys=ON`
   - Row factory: Add `sqlite3.Row` (optional)

## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate the bug on unfixed code by simulating the lock condition, then verify the fix works correctly and preserves existing behavior.

### Exploratory Fault Condition Checking

**Goal**: Surface counterexamples that demonstrate the bug BEFORE implementing the fix. Confirm that the lock error occurs when WAL files exist and `init_database()` uses a non-WAL connection.

**Test Plan**: Create test scenarios that simulate the lock condition by ensuring WAL files exist (by calling `get_db()` first) and then calling the unfixed `init_database()`. Run these tests on the UNFIXED code to observe the lock error and confirm the root cause.

**Test Cases**:
1. **WAL Files Present Test**: Create WAL files by calling `get_db()`, then call unfixed `init_database()` (will fail with lock error on unfixed code)
2. **Concurrent Connection Test**: Open a connection with `get_db()` (WAL mode), keep it open, then call unfixed `init_database()` in another thread (will fail on unfixed code)
3. **Fresh Database Test**: Delete all database files, call unfixed `init_database()` on clean slate (may succeed but creates inconsistency)
4. **Repeated Initialization Test**: Call unfixed `init_database()` twice in succession (second call may fail if first created WAL files)

**Expected Counterexamples**:
- `sqlite3.OperationalError: database is locked` at line 158 during `CREATE TABLE sessions`
- Possible causes: non-WAL connection cannot acquire locks when WAL mode is active, lock protocol mismatch between journal modes

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds (WAL files exist or WAL connections active), the fixed function produces the expected behavior (successful initialization without lock errors).

**Pseudocode:**
```
FOR ALL input WHERE isBugCondition(input) DO
  result := init_database_fixed()
  ASSERT result.success == True
  ASSERT result.exception == None
  ASSERT result.tables_created == ['city', 'users', 'projects', 'meetings', 
                                    'complaints', 'follow_ups', 
                                    'contractor_reviews', 'sessions']
  ASSERT result.seed_data_inserted == True
END FOR
```

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold (all runtime database operations), the fixed function produces the same result as the original function.

**Pseudocode:**
```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT get_db_original().configuration == get_db_fixed().configuration
  ASSERT database_operation_original(input) == database_operation_fixed(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for preservation checking because:
- It generates many test cases automatically across the input domain
- It catches edge cases that manual unit tests might miss
- It provides strong guarantees that behavior is unchanged for all non-initialization operations

**Test Plan**: Observe behavior on UNFIXED code first for all runtime operations (user creation, project queries, complaint submission, etc.), then write property-based tests capturing that behavior to ensure it remains unchanged after the fix.

**Test Cases**:
1. **get_db() Configuration Preservation**: Verify that `get_db()` still returns connections with WAL mode, foreign keys, 30s timeout, and Row factory after the fix
2. **Foreign Key Enforcement Preservation**: Verify that foreign key constraints are still enforced for all operations (insert invalid city_id, should fail)
3. **Schema Migration Preservation**: Verify that dropping old tables when city table doesn't exist still works correctly
4. **Seed Data Preservation**: Verify that `INSERT OR IGNORE` still prevents duplicate city entries
5. **All CRUD Operations Preservation**: Verify that create, read, update, delete operations for users, projects, complaints, meetings, reviews, and follow-ups continue to work identically

### Unit Tests

- Test `init_database()` succeeds when WAL files exist from previous run
- Test `init_database()` succeeds when called multiple times (idempotency)
- Test `init_database()` creates all 8 tables correctly
- Test `init_database()` inserts seed data (2 cities) correctly
- Test `init_database()` enables WAL mode on its connection
- Test `init_database()` enables foreign keys on its connection
- Test schema migration drops old tables when city table missing
- Test edge case: concurrent calls to `init_database()` (should handle gracefully)

### Property-Based Tests

- Generate random sequences of database operations (user creation, project insertion, queries) and verify they work identically before and after the fix
- Generate random foreign key violation scenarios and verify they fail identically before and after the fix
- Generate random concurrent access patterns (multiple `get_db()` calls) and verify no lock errors occur after the fix
- Test that WAL mode remains enabled across many connection open/close cycles

### Integration Tests

- Test full Flask app startup with existing WAL files (should succeed after fix)
- Test app startup after crash with leftover WAL files (should succeed after fix)
- Test app startup in multi-worker environment (gunicorn with 4 workers, should succeed after fix)
- Test that all API endpoints work correctly after initialization with the fix
- Test that database operations maintain data integrity (foreign keys enforced) after the fix
