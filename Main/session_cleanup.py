"""Session cleanup utility.

Goals (safe-by-default):
1. Prune expired cached search artifacts (flight_searches + dependent tables) older than a TTL (default 24h).
2. (Optional) Prune raw api_queries ONLY if an explicit retention is provided (env SERPAPI_RAW_RETENTION_DAYS or CLI flag).
3. Vacuum (opt-in) the SQLite database to reclaim space.
4. Remove orphaned flight_results / segments / layovers defensively (shouldn't normally exist).

Raw data preservation policy: By default NO raw api_queries rows are deleted, preserving the "store ALL raw data" mandate.
Enable raw pruning only with explicit retention days > 0.

Exit code: 0 success, 1 error.
"""
from __future__ import annotations
import os, sqlite3, logging, argparse, json
from datetime import datetime, timedelta

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'DB', 'Main_DB.db'))

logger = logging.getLogger("session_cleanup")
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s :: %(message)s')

def _connect():
    return sqlite3.connect(DB_PATH)

def prune_search_cache(max_age_hours: int, dry_run: bool = False) -> dict:
    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    removed = { 'searches': 0, 'flight_results': 0, 'segments': 0, 'layovers': 0, 'price_insights': 0 }
    with _connect() as conn:
        cur = conn.cursor()
        # Identify expired searches
        cur.execute("SELECT search_id FROM flight_searches WHERE created_at < ?", (cutoff.isoformat(),))
        old_ids = [r[0] for r in cur.fetchall()]
        if not old_ids:
            return { 'cutoff': cutoff.isoformat(), 'removed': removed }
        if dry_run:
            return { 'cutoff': cutoff.isoformat(), 'would_remove_search_ids': old_ids, 'removed': removed }
        for sid in old_ids:
            cur.execute("SELECT id FROM flight_results WHERE search_id = ?", (sid,))
            fr_ids = [r[0] for r in cur.fetchall()]
            for frid in fr_ids:
                cur.execute("DELETE FROM layovers WHERE flight_result_id = ?", (frid,))
                removed['layovers'] += cur.rowcount
                cur.execute("DELETE FROM flight_segments WHERE flight_result_id = ?", (frid,))
                removed['segments'] += cur.rowcount
            cur.execute("DELETE FROM flight_results WHERE search_id = ?", (sid,))
            removed['flight_results'] += cur.rowcount
            cur.execute("DELETE FROM price_insights WHERE search_id = ?", (sid,))
            removed['price_insights'] += cur.rowcount
            cur.execute("DELETE FROM flight_searches WHERE search_id = ?", (sid,))
            removed['searches'] += cur.rowcount
        conn.commit()
    return { 'cutoff': cutoff.isoformat(), 'removed': removed }

def prune_raw_api(retention_days: int, dry_run: bool = False) -> dict:
    cutoff = datetime.now() - timedelta(days=retention_days)
    with _connect() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM api_queries WHERE created_at < ?", (cutoff.isoformat(),))
        ids = [r[0] for r in cur.fetchall()]
        if dry_run:
            return { 'cutoff': cutoff.isoformat(), 'would_remove_raw_ids': ids }
        if ids:
            cur.executemany("DELETE FROM api_queries WHERE id = ?", [(i,) for i in ids])
            conn.commit()
        return { 'cutoff': cutoff.isoformat(), 'removed_raw_count': len(ids) }

def remove_orphans(dry_run: bool = False) -> dict:
    stats = {}
    with _connect() as conn:
        cur = conn.cursor()
        # Orphan flight_results
        cur.execute("""
            SELECT fr.id FROM flight_results fr
            LEFT JOIN flight_searches fs ON fs.search_id = fr.search_id
            WHERE fs.search_id IS NULL
        """)
        fr_orphans = [r[0] for r in cur.fetchall()]
        stats['flight_results_orphans'] = len(fr_orphans)
        # Orphan segments
        cur.execute("""
            SELECT s.id FROM flight_segments s
            LEFT JOIN flight_results fr ON fr.id = s.flight_result_id
            WHERE fr.id IS NULL
        """)
        seg_orphans = [r[0] for r in cur.fetchall()]
        stats['segments_orphans'] = len(seg_orphans)
        # Orphan layovers
        cur.execute("""
            SELECT l.id FROM layovers l
            LEFT JOIN flight_results fr ON fr.id = l.flight_result_id
            WHERE fr.id IS NULL
        """)
        lay_orphans = [r[0] for r in cur.fetchall()]
        stats['layovers_orphans'] = len(lay_orphans)
        if dry_run:
            return stats
        # Delete them
        for oid in lay_orphans: cur.execute("DELETE FROM layovers WHERE id = ?", (oid,))
        for oid in seg_orphans: cur.execute("DELETE FROM flight_segments WHERE id = ?", (oid,))
        for oid in fr_orphans: cur.execute("DELETE FROM flight_results WHERE id = ?", (oid,))
        conn.commit()
        stats['deleted'] = {
            'layovers': len(lay_orphans),
            'segments': len(seg_orphans),
            'flight_results': len(fr_orphans)
        }
    return stats

def vacuum(dry_run: bool = False) -> bool:
    if dry_run: return True
    with _connect() as conn:
        conn.execute("VACUUM")
    return True

def main():
    parser = argparse.ArgumentParser(description="Session cleanup utility (safe defaults: preserve raw API data)")
    parser.add_argument('--cache-age-hours', type=int, default=24, help='Age threshold for cached searches (flight_searches)')
    parser.add_argument('--raw-retention-days', type=int, default=int(os.getenv('SERPAPI_RAW_RETENTION_DAYS','0')), help='Retention for raw api_queries (0 = keep all)')
    parser.add_argument('--prune-raw-cache-age', action='store_true', help='Also prune raw api_queries older than --cache-age-hours (authoritative override)')
    parser.add_argument('--vacuum', action='store_true', help='VACUUM the database after deletions')
    parser.add_argument('--orphans', action='store_true', help='Remove orphaned dependent rows')
    parser.add_argument('--dry-run', action='store_true', help='Show actions without modifying data')
    parser.add_argument('--json', action='store_true', help='Emit JSON summary only')
    args = parser.parse_args()

    summary = {
        'db_path': DB_PATH,
        'cache_age_hours': args.cache_age_hours,
        'raw_retention_days': args.raw_retention_days,
        'dry_run': args.dry_run
    }
    try:
        summary['cache_prune'] = prune_search_cache(args.cache_age_hours, dry_run=args.dry_run)
        if args.raw_retention_days > 0:
            summary['raw_prune'] = prune_raw_api(args.raw_retention_days, dry_run=args.dry_run)
        elif args.prune_raw_cache_age:
            # derive cutoff in days (floor >=1 if hours >=24) else treat as fractional days for reporting
            hours = args.cache_age_hours
            # Use hours directly by converting to timedelta comparison (custom inline logic)
            cutoff = datetime.now() - timedelta(hours=hours)
            with _connect() as conn:
                cur = conn.cursor()
                cur.execute("SELECT id FROM api_queries WHERE created_at < ?", (cutoff.isoformat(),))
                ids = [r[0] for r in cur.fetchall()]
                if not args.dry_run and ids:
                    cur.executemany("DELETE FROM api_queries WHERE id = ?", [(i,) for i in ids])
                    conn.commit()
                summary['raw_prune_cache_age'] = {
                    'cutoff': cutoff.isoformat(),
                    'removed_raw_count': 0 if args.dry_run else len(ids),
                    'would_remove_raw_count': len(ids) if args.dry_run else None
                }
        if args.orphans:
            summary['orphans'] = remove_orphans(dry_run=args.dry_run)
        if args.vacuum:
            summary['vacuum'] = vacuum(dry_run=args.dry_run)
    except Exception as e:
        summary['error'] = str(e)
        if not args.json:
            print("ERROR:", e)
        print(json.dumps(summary, indent=2))
        raise SystemExit(1)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print("Session Cleanup Summary")
        print(json.dumps(summary, indent=2))
    raise SystemExit(0)

if __name__ == '__main__':
    main()
