import subprocess, sys, pathlib, re

ROOT = pathlib.Path(__file__).parent.parent
DBHELPER = ROOT / 'DB' / 'database_helper.py'


def run_cli(*args: str) -> str:
    cmd = [sys.executable, str(DBHELPER), *args]
    out = subprocess.check_output(cmd, text=True).strip()
    return out


def test_cli_checksum_matches_snapshot():
    # get checksum via CLI
    cli_cs = run_cli('--checksum')
    snap = (ROOT / 'DB' / 'current_schema.sql').read_text(encoding='utf-8')
    m = re.search(r'^-- Schema Checksum: (.+)$', snap, flags=re.MULTILINE)
    assert m, 'Checksum line missing in snapshot'
    file_cs = m.group(1).strip()
    assert cli_cs == file_cs, f'CLI checksum {cli_cs} != file checksum {file_cs}'


def test_cli_snapshot_refuses_temp_table(monkeypatch, tmp_path):
    # Copy DB to temp and add a forbidden table name, then invoke snapshot
    import shutil, sqlite3
    src_db = ROOT / 'DB' / 'Main_DB.db'
    dst_db = tmp_path / 'temp.db'
    shutil.copyfile(src_db, dst_db)
    conn = sqlite3.connect(dst_db)
    try:
        conn.execute('CREATE TABLE temp_bad_table (id INTEGER)')
        conn.commit()
    finally:
        conn.close()
    # Expect failure exit code 2
    proc = subprocess.run([sys.executable, str(DBHELPER), '--snapshot', '--db', str(dst_db)], capture_output=True, text=True)
    assert proc.returncode == 2, f'Expected failure (2) when temp table present, got {proc.returncode}\nSTDERR:{proc.stderr}'
    assert 'unexpected tables' in proc.stderr.lower()
