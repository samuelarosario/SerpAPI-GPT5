import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB_DIR = ROOT / 'DB'
if str(DB_DIR) not in sys.path:
    sys.path.append(str(DB_DIR))

from DB import database_helper  # type: ignore


def test_schema_version_exists():
    db = database_helper.SerpAPIDatabase()
    conn = db.get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT version FROM schema_version WHERE id=1")
        row = cur.fetchone()
        assert row is not None, "schema_version row missing"
        assert row[0].startswith("2025.09.08-baseline"), f"Unexpected schema version {row[0]}"
    finally:
        cur.close()
        conn.close()
