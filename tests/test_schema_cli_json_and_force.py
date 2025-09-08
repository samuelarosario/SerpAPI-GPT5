import json
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).parent.parent
DBHELPER = ROOT / 'DB' / 'database_helper.py'
MAIN_DB = ROOT / 'DB' / 'Main_DB.db'


def run_cmd(*args):
    out = subprocess.check_output([sys.executable, str(DBHELPER), *args], text=True).strip()
    return out


def test_cli_json_checksum_parses():
    raw = run_cmd('--checksum', '--json')
    obj = json.loads(raw)
    assert obj['mode'] == 'checksum'
    assert 'checksum' in obj and len(obj['checksum']) > 10


def test_cli_force_snapshot_on_temp_table():
    tmpdir = tempfile.mkdtemp()
    try:
        temp_db = pathlib.Path(tmpdir) / 'force.db'
        shutil.copyfile(MAIN_DB, temp_db)
        conn = sqlite3.connect(temp_db)
        try:
            conn.execute('CREATE TABLE temp_ephemeral (id INTEGER)')
            conn.commit()
        finally:
            conn.close()
        # Without --force should fail
        proc_fail = subprocess.run([sys.executable, str(DBHELPER), '--snapshot', '--db', str(temp_db), '--json'], capture_output=True, text=True)
        assert proc_fail.returncode == 2
        jfail = json.loads(proc_fail.stdout or proc_fail.stderr)
        assert jfail['mode'] == 'snapshot' and jfail['status'] == 'failed'
        # With --force should succeed
        proc_ok = subprocess.run([sys.executable, str(DBHELPER), '--snapshot', '--db', str(temp_db), '--json', '--force'], capture_output=True, text=True)
        assert proc_ok.returncode == 0
        jok = json.loads(proc_ok.stdout)
        assert jok['status'] == 'ok' and jok['forced'] is True
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
