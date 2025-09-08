import pathlib, sys
ROOT = pathlib.Path(__file__).resolve().parents[1]
DB_DIR = ROOT / 'DB'
if str(DB_DIR) not in sys.path:
    sys.path.append(str(DB_DIR))
from DB.database_helper import SerpAPIDatabase  # type: ignore

def test_schema_drift_ok():
    """Schema drift should report ok against the canonical DB file.

    We explicitly point at DB/Main_DB.db (the populated schema) and open a
    connection first so that schema_version + migration_history tables are
    ensured before drift detection runs (detect_schema_drift itself does not
    perform initialization to keep side‑effects minimal).
    """
    db_file = DB_DIR / "Main_DB.db"
    db = SerpAPIDatabase(str(db_file))
    # Trigger initialization side-effects (schema_version + migration_history)
    conn = db.get_connection(); conn.close()
    drift = db.detect_schema_drift()
    assert drift['ok'] is True, f"Unexpected drift: {drift}"
    assert 'schema_version' not in drift['missing']
