import json
import sqlite3
from pathlib import Path

import sys


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    db_path = root / "DB" / "Main_DB.db"
    sys.path.insert(0, str(root))
    sys.path.insert(0, str(root / "Main"))
    from Main.enhanced_flight_search import EnhancedFlightSearchClient

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    row = cur.execute(
        "SELECT id, search_id, raw_parameters, api_query_id FROM flight_searches ORDER BY id DESC LIMIT 1"
    ).fetchone()
    if not row:
        print("NO_SEARCH_ROWS")
        return 0
    _, search_id, raw_params, api_qid = row
    api_row = cur.execute("SELECT raw_response FROM api_queries WHERE id=?", (api_qid,)).fetchone()
    con.close()
    if not api_row:
        print(f"NO_API_ROW for api_query_id={api_qid}")
        return 1
    try:
        api_resp = json.loads(api_row[0])
    except Exception:
        print("API_RESPONSE_NOT_JSON")
        return 1
    search_params = {}
    if raw_params:
        try:
            search_params = json.loads(raw_params)
        except Exception:
            pass

    efs = EnhancedFlightSearchClient(db_path=str(db_path))
    # Re-store using updated derivation logic in enhanced_flight_search
    efs._store_structured_data(search_id, search_params, api_resp, api_qid)
    print("RESTORED", search_id)

    # Quick verification sample
    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    segs = cur.execute(
        "SELECT airline_code, flight_number FROM flight_segments WHERE flight_result_id IN (SELECT id FROM flight_results WHERE search_id=?) ORDER BY id ASC LIMIT 5",
        (search_id,),
    ).fetchall()
    codes = cur.execute(
        "SELECT airline_code FROM airlines ORDER BY last_seen DESC LIMIT 10"
    ).fetchall()
    con.close()
    print("SAMPLE_SEGMENTS", segs)
    print("AIRLINES_CODES", [c[0] for c in codes])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
