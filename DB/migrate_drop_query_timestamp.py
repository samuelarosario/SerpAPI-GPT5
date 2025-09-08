"""Schema Migration: Drop legacy query_timestamp column from api_queries.

Strategy (SQLite limitation workaround):
1. Create new table api_queries_new without query_timestamp.
2. Copy data mapping old created_at semantics.
3. Drop original api_queries.
4. Rename api_queries_new -> api_queries.
5. Recreate indexes excluding idx_query_timestamp.

Idempotent: If query_timestamp already absent, exits cleanly.
Backup: Optional simple .bak copy if desired by operator.
"""
import sqlite3, os, shutil, sys

DB_PATH = os.path.join(os.path.dirname(__file__), 'Main_DB.db')

def column_exists(cur, table, column):
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.cursor()
        if not column_exists(cur, 'api_queries', 'query_timestamp'):
            print("query_timestamp already absent; nothing to do.")
            return
        # Simple backup
        backup_path = DB_PATH + '.bak'
        shutil.copy2(DB_PATH, backup_path)
        print(f"Backup created at {backup_path}")
        cur.execute("BEGIN TRANSACTION")
        cur.execute("""
            CREATE TABLE api_queries_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_parameters TEXT,
                raw_response TEXT NOT NULL,
                query_type TEXT,
                status_code INTEGER,
                response_size INTEGER,
                api_endpoint TEXT,
                search_term TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("INSERT INTO api_queries_new (id, query_parameters, raw_response, query_type, status_code, response_size, api_endpoint, search_term, created_at) SELECT id, query_parameters, raw_response, query_type, status_code, response_size, api_endpoint, search_term, COALESCE(created_at, query_timestamp) FROM api_queries")
        cur.execute("DROP TABLE api_queries")
        cur.execute("ALTER TABLE api_queries_new RENAME TO api_queries")
        # Recreate needed indexes (excluding idx_query_timestamp)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON api_queries(created_at)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_query_type ON api_queries(query_type)")
        conn.commit()
        print("Migration completed: query_timestamp removed.")
    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        conn.close()

if __name__ == '__main__':
    migrate()