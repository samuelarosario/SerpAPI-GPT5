import pathlib
import re
import shutil
import tempfile

from DB.database_helper import SerpAPIDatabase

DB_PATH = 'DB/Main_DB.db'

def read_checksum_from_snapshot():
    snap = pathlib.Path('DB/current_schema.sql').read_text(encoding='utf-8')
    m = re.search(r'^-- Schema Checksum: (.+)$', snap, flags=re.MULTILINE)
    assert m, 'Schema Checksum line missing'
    return m.group(1).strip()


def test_schema_checksum_changes_on_drift():
    # Copy DB to temp so we can mutate safely
    tmp_dir = tempfile.mkdtemp()
    try:
        tmp_db = pathlib.Path(tmp_dir) / 'temp.db'
        shutil.copyfile(DB_PATH, tmp_db)
        db = SerpAPIDatabase(str(tmp_db))
        # Use a single connection lifecycle to avoid Windows file locks
        conn = db.get_connection()
        try:
            base_cs = db.compute_schema_checksum(conn)
            # Drift
            conn.execute('CREATE TABLE temp_drift_table (id INTEGER PRIMARY KEY, note TEXT)')
            drift_cs = db.compute_schema_checksum(conn)
        finally:
            try:
                conn.close()
            except Exception:
                pass
        assert base_cs != drift_cs, 'Checksum did not change after schema drift'
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
