"""
Wipe structured flight data for a clean observation run.

This removes derived/structured tables in a safe FK order while preserving:
- airports, airlines (reference data)
- api_queries (raw payloads)

Tables cleared (in order):
  layovers -> flight_segments -> flight_results -> price_insights -> route_analytics -> flight_searches

Outputs a JSON summary with counts before/after.
"""
from __future__ import annotations

import json
import os
import sqlite3


DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'DB', 'Main_DB.db'))


def table_count(cur: sqlite3.Cursor, table: str) -> int:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    return int(cur.fetchone()[0])


def main() -> None:
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        cur = conn.cursor()

        tables_watch = [
            'flight_searches', 'flight_results', 'flight_segments', 'layovers',
            'price_insights', 'route_analytics', 'api_queries', 'airports', 'airlines'
        ]
        before = {t: table_count(cur, t) for t in tables_watch}

        # Delete in dependency-safe order
        cur.execute('DELETE FROM layovers')
        cur.execute('DELETE FROM flight_segments')
        cur.execute('DELETE FROM flight_results')
        cur.execute('DELETE FROM price_insights')
        cur.execute('DELETE FROM route_analytics')
        cur.execute('DELETE FROM flight_searches')
        conn.commit()

        # Reclaim space
        conn.execute('VACUUM')

        after = {t: table_count(cur, t) for t in tables_watch}
        print(json.dumps({
            'ok': True,
            'db_path': DB_PATH,
            'before': before,
            'after': after
        }, indent=2))
    finally:
        conn.close()


if __name__ == '__main__':
    main()
