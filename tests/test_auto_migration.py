import os
import sqlite3
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_DIR = os.path.join(ROOT, 'DB')
if DB_DIR not in sys.path:
    sys.path.insert(0, DB_DIR)

from database_helper import SerpAPIDatabase  # type: ignore

LEGACY_SCHEMA = """
CREATE TABLE api_queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_timestamp TEXT NOT NULL,
    query_parameters TEXT,
    raw_response TEXT NOT NULL,
    query_type TEXT,
    status_code INTEGER,
    response_size INTEGER,
    api_endpoint TEXT,
    search_term TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
"""


def test_automated_migration_removes_query_timestamp():
    fd, path = tempfile.mkstemp(prefix='auto_mig_', suffix='.db')
    os.close(fd)
    try:
        with sqlite3.connect(path) as conn:
            conn.executescript(LEGACY_SCHEMA)
            conn.execute("INSERT INTO api_queries (query_timestamp, query_parameters, raw_response) VALUES (?,?,?)", ("2025-01-01T00:00:00","{}","{}"))
            conn.commit()
        # Instantiate helper pointing to legacy DB
        db = SerpAPIDatabase(db_path=path)
        # Trigger connection (and migration)
        with db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(api_queries)")
            cols = [r[1] for r in cur.fetchall()]
            assert 'query_timestamp' not in cols, 'Legacy column should be removed by automated migration'
            # Ensure existing row preserved
            cur.execute('SELECT COUNT(*) FROM api_queries')
            assert cur.fetchone()[0] == 1
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
