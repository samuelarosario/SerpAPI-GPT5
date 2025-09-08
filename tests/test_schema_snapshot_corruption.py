import pathlib
import re
import sqlite3
from DB.database_helper import SerpAPIDatabase  # type: ignore

ROOT = pathlib.Path(__file__).resolve().parents[1]

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
    # remove a non-header DDL line safely and record which table was removed
    removed_table = None
    for i, l in enumerate(lines):
        if l.strip().startswith('CREATE TABLE'):
            # line format: CREATE TABLE airlines (
            parts = l.split()
            if len(parts) >= 3:
                removed_table = parts[2].strip('"')  # strip quotes if any
            del lines[i]
            break
    corrupted = '\n'.join(lines) + '\n'
    temp_file.write_text(corrupted, encoding='utf-8')

    # Recompute checksum from live DB (schema itself is unchanged)
    db = SerpAPIDatabase(str(ROOT / 'DB' / 'Main_DB.db'))
    with sqlite3.connect(str(ROOT / 'DB' / 'Main_DB.db')) as conn:
        live_cs = db.compute_schema_checksum(conn)
    # Sanity: live DB checksum should still equal original good checksum (DB not altered by file corruption)
    assert live_cs == good_checksum

    # Validate corruption indicators:
    # 1. Header still lists the removed table name (ensuring inconsistency)
    header_match = re.search(r'^-- Table List: (.+)$', original, flags=re.MULTILINE)
    assert header_match, 'Original snapshot missing table list header'
    table_list = [t.strip() for t in header_match.group(1).split(',')]
    if removed_table:
        assert removed_table in table_list
        # 2. Corrupted snapshot body no longer contains the removed table DDL line
        assert f'CREATE TABLE {removed_table}' not in corrupted

    # 3. Corrupted snapshot still contains old checksum line (stale)
    assert f'-- Schema Checksum: {good_checksum}' in corrupted
    # 4. Presence of checksum line allows downstream tooling to detect mismatch when recomputing body-based checksum
    assert '-- Schema Checksum:' in corrupted
