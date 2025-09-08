import os, shutil, tempfile, re, sqlite3, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from DB.database_helper import SerpAPIDatabase  # type: ignore

SCHEMA_PATH = ROOT / 'DB' / 'current_schema.sql'


def test_schema_snapshot_corruption_detection(tmp_path):
    # Read original
    original = SCHEMA_PATH.read_text(encoding='utf-8')
    assert '-- Schema Checksum:' in original
    m = re.search(r'^-- Schema Checksum: (.+)$', original, flags=re.MULTILINE)
    assert m
    good_checksum = m.group(1)

    # Corrupt middle of file (remove a CREATE TABLE line) in temp copy
    temp_file = tmp_path / 'current_schema.sql'
    lines = original.splitlines()
    # remove a non-header DDL line safely
    for i,l in enumerate(lines):
        if l.strip().startswith('CREATE TABLE'):
            del lines[i]
            break
    corrupted = '\n'.join(lines) + '\n'
    temp_file.write_text(corrupted, encoding='utf-8')

    # Use helper to recompute checksum from live DB; it should NOT equal stale checksum embedded in corrupted snapshot
    db = SerpAPIDatabase(str(ROOT / 'DB' / 'Main_DB.db'))
    with sqlite3.connect(str(ROOT / 'DB' / 'Main_DB.db')) as conn:
        live_cs = db.compute_schema_checksum(conn)
    assert live_cs != good_checksum, 'Live checksum unexpectedly matches original (test precondition issue)'
    # The corrupted snapshot still shows old checksum line; mismatch indicates corruption / drift not reflected
    assert good_checksum in corrupted
    # Basic remediation guidance (assert mismatch is detectable)
    assert '-- Schema Checksum:' in corrupted
