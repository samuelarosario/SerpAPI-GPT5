import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timedelta

# Ensure project imports work when run directly
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MAIN_DIR = os.path.join(ROOT, 'Main')
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
if MAIN_DIR not in sys.path:
    sys.path.insert(0, MAIN_DIR)

from Main.enhanced_flight_search import EnhancedFlightSearchClient  # type: ignore

DB_PATH = os.path.normpath(os.path.join(ROOT, 'DB', 'Main_DB.db'))


def fetch_candidates(conn, since_hours: int | None, route: str | None, outbound: str | None, ret_date: str | None, search_id: str | None):
    cur = conn.cursor()
    where = ["return_date IS NOT NULL"]
    params: list = []
    if since_hours is not None and since_hours > 0:
        cutoff = (datetime.now() - timedelta(hours=since_hours)).isoformat()
        where.append("created_at >= ?")
        params.append(cutoff)
    if route:
        try:
            dep, arr = route.strip().upper().split('-')
            where.append("departure_airport_code = ? AND arrival_airport_code = ?")
            params.extend([dep, arr])
        except Exception:
            pass
    if outbound:
        where.append("outbound_date = ?")
        params.append(outbound)
    if ret_date:
        where.append("return_date = ?")
        params.append(ret_date)
    if search_id:
        where = ["search_id = ?"]
        params = [search_id]
    sql = f"SELECT search_id, departure_airport_code, arrival_airport_code, outbound_date, return_date, api_query_id, raw_parameters FROM flight_searches WHERE {' AND '.join(where)} ORDER BY created_at DESC LIMIT 200"
    cur.execute(sql, params)
    rows = cur.fetchall()
    out: list[dict] = []
    for sid, dep, arr, outd, ret, aq, rawp in rows:
        # Check if inbound exists in structured segments already
        cur.execute(
            """
            SELECT COUNT(*)
            FROM flight_segments fs JOIN flight_results fr ON fs.flight_result_id=fr.id
            WHERE fr.search_id=?
              AND (
                    (fs.departure_airport_code = ? AND fs.arrival_airport_code = ?)
                 OR (fs.departure_time LIKE ?)
              )
            """,
            (sid, arr, dep, f"{ret}%")
        )
        has_inbound = (cur.fetchone() or [0])[0] > 0
        out.append({
            'search_id': sid,
            'dep': dep,
            'arr': arr,
            'outbound_date': outd,
            'return_date': ret,
            'api_query_id': aq,
            'raw_parameters': rawp,
            'has_inbound': has_inbound,
        })
    return out


def load_raw(conn, api_query_id: int | None):
    if not api_query_id:
        return None
    cur = conn.cursor()
    cur.execute("SELECT raw_response FROM api_queries WHERE id=?", (api_query_id,))
    row = cur.fetchone()
    if not row or not row[0]:
        return None
    try:
        return json.loads(row[0])
    except Exception:
        return None


def has_inbound_in_payload(data: dict, dep: str, arr: str, ret_date: str) -> bool:
    flights = (data.get('best_flights') or []) + (data.get('other_flights') or [])
    for f in flights:
        for s in (f.get('flights') or []):
            da = (s.get('departure_airport') or {})
            aa = (s.get('arrival_airport') or {})
            did = str(da.get('id') or '').upper()
            aid = str(aa.get('id') or '').upper()
            dt = str(da.get('time') or '')
            at = str(aa.get('time') or '')
            if (did == arr and aid == dep) or (dt.startswith(ret_date) or at.startswith(ret_date)):
                return True
    return False


def main():
    p = argparse.ArgumentParser(description='Backfill inbound segments by merging inbound one-way results when missing.')
    p.add_argument('--since-hours', type=int, default=72)
    p.add_argument('--route', help='Filter by route, e.g., SYD-HND')
    p.add_argument('--outbound')
    p.add_argument('--return-date')
    p.add_argument('--search-id')
    p.add_argument('--dry-run', action='store_true')
    args = p.parse_args()

    client = EnhancedFlightSearchClient()
    conn = sqlite3.connect(DB_PATH)
    try:
        candidates = fetch_candidates(conn, args.since_hours, args.route, args.outbound, args.return_date, args.search_id)
        fixed = 0
        skipped = 0
        for row in candidates:
            sid = row['search_id']
            dep = row['dep']
            arr = row['arr']
            outd = row['outbound_date']
            ret = row['return_date']
            aq = row['api_query_id']
            if not ret:
                skipped += 1
                continue
            if row['has_inbound']:
                skipped += 1
                continue
            raw = load_raw(conn, aq) or {}
            # Get stored params; fallback to raw search_parameters
            try:
                sp = json.loads(row['raw_parameters'] or '{}')
            except Exception:
                sp = {}
            if not sp:
                sp = raw.get('search_parameters') or {}
            # If payload already has inbound (rare), just re-store; else fetch inbound and merge
            merged = raw if isinstance(raw, dict) else {}
            if not has_inbound_in_payload(merged or {}, dep, arr, ret):
                # Perform inbound one-way API call and merge
                if args.dry_run:
                    print(f"[DRY] Would fetch inbound {arr}->{dep} on {ret} for {sid}")
                    continue
                inbound = client.api_client.search_one_way(departure_id=arr, arrival_id=dep, outbound_date=ret,
                                                          adults=sp.get('adults', 1), children=sp.get('children', 0),
                                                          infants_in_seat=sp.get('infants_in_seat', 0), infants_on_lap=sp.get('infants_on_lap', 0),
                                                          travel_class=sp.get('travel_class', 1), currency=sp.get('currency', 'USD'))
                if inbound and inbound.get('success'):
                    in_data = inbound.get('data') or {}
                    merged.setdefault('other_flights', [])
                    merged['other_flights'].extend(in_data.get('best_flights', []) or [])
                    merged['other_flights'].extend(in_data.get('other_flights', []) or [])
                else:
                    print(f"Inbound API failed for {sid}; skipping.")
                    skipped += 1
                    continue
            # Store back using the existing structured storage routine
            if not args.dry_run:
                client._store_structured_data(sid, {
                    'departure_id': dep,
                    'arrival_id': arr,
                    'outbound_date': outd,
                    'return_date': ret,
                    'adults': sp.get('adults', 1),
                    'children': sp.get('children', 0),
                    'infants_in_seat': sp.get('infants_in_seat', 0),
                    'infants_on_lap': sp.get('infants_on_lap', 0),
                    'travel_class': sp.get('travel_class', 1),
                    'currency': sp.get('currency', 'USD')
                }, merged, aq)
                fixed += 1
                print(f"Fixed: {sid} ({dep}-{arr} {outd} / {ret})")
        print(json.dumps({'fixed': fixed, 'skipped': skipped, 'candidates': len(candidates)}, indent=2))
    finally:
        conn.close()


if __name__ == '__main__':
    main()
