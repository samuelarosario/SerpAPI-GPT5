import os
import sqlite3
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MAIN_DIR = os.path.join(ROOT, 'Main')
if MAIN_DIR not in sys.path:
    sys.path.insert(0, MAIN_DIR)

from core.db_utils import open_connection  # type: ignore


def test_foreign_key_enforced():
    fd, path = tempfile.mkstemp(prefix='fk_', suffix='.db')
    os.close(fd)
    # Minimal schema with FK
    schema = """
    CREATE TABLE parent (id INTEGER PRIMARY KEY AUTOINCREMENT);
    CREATE TABLE child (id INTEGER PRIMARY KEY AUTOINCREMENT, parent_id INTEGER, FOREIGN KEY(parent_id) REFERENCES parent(id));
    """
    with open_connection(path) as conn:
        conn.executescript(schema)
        # Insert child referencing missing parent should fail
        try:
            conn.execute("INSERT INTO child (parent_id) VALUES (999)")
            conn.commit()
            failed = False
        except sqlite3.IntegrityError:
            failed = True
    assert failed, 'Foreign key constraint should prevent orphan child insertion'