import pathlib, hashlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA_FILE = ROOT / 'DB' / 'current_schema.sql'

def test_schema_snapshot_checksum_alignment():
    if not SCHEMA_FILE.exists():
        raise RuntimeError('Schema snapshot missing')
    content = SCHEMA_FILE.read_text(encoding='utf-8')
    m = re.search(r"-- Schema Checksum: (\w+)", content)
    assert m, 'Checksum line missing'
    snapshot_checksum = m.group(1)
    # Canonical recompute: concatenate all CREATE statements (tables + indexes)
    stmts = []
    for line in content.splitlines():
        line = line.strip()
        if line.startswith('CREATE TABLE') or line.startswith('CREATE INDEX'):
            stmts.append(line.rstrip(';'))
    canonical = "\n".join(sorted(stmts))
    live_checksum = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    assert snapshot_checksum == live_checksum, f"Snapshot checksum mismatch: file={snapshot_checksum} live={live_checksum}"
