import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
DB_DIR = ROOT / 'DB'
if str(DB_DIR) not in sys.path:
    sys.path.append(str(DB_DIR))

from DB.database_helper import SerpAPIDatabase  # type: ignore

def test_migration_history_baseline_exists():
    db = SerpAPIDatabase()
    conn = db.get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT version FROM migration_history WHERE version='2025.09.08-baseline'")
        row = cur.fetchone()
        assert row is not None, "Baseline migration history row missing"
    finally:
        cur.close(); conn.close()
