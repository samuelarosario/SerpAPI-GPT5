"""Phase 1 DB inspection utility.
Lists tables and simple row counts for quick sanity checks.
"""
from __future__ import annotations
import sqlite3
from pathlib import Path
from typing import Dict, Any

DB_PATH = Path(__file__).resolve().parents[2] / 'DB' / 'Main_DB.db'

def table_counts() -> Dict[str, int]:
    counts: Dict[str, int] = {}
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [r[0] for r in cur.fetchall()]
        for t in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                counts[t] = cur.fetchone()[0]
            except Exception:
                counts[t] = -1
    finally:
        conn.close()
    return counts

if __name__ == '__main__':
    print(f'Database: {DB_PATH}')
    for name, cnt in sorted(table_counts().items()):
        print(f'{name:25} {cnt}')
