import os
import json
import sqlite3
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    db_path = root / "DB" / "Main_DB.db"
    out_dir = root / "runtime_logs"
    out_dir.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(str(db_path))
    cur = con.cursor()
    row = cur.execute(
        """
        SELECT id, created_at, status_code, response_size, api_endpoint, search_term, raw_response
        FROM api_queries
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchone()
    con.close()

    if not row:
        print("NO_API_QUERY_ROWS")
        return 0

    id_, created_at, status_code, response_size, api_endpoint, search_term, raw_response = row
    try:
        data = json.loads(raw_response)
        pretty = json.dumps(data, indent=2, ensure_ascii=False)
    except Exception:
        data = None
        pretty = raw_response

    out_path = out_dir / f"api_last_response_{id_}.json"
    out_path.write_text(pretty, encoding="utf-8")

    meta = {
        "id": id_,
        "created_at": created_at,
        "status_code": status_code,
        "response_size": response_size,
        "api_endpoint": api_endpoint,
        "search_term": search_term,
        "file": str(out_path),
    }
    print("SAVED", str(out_path))
    print("META", json.dumps(meta, indent=2))

    # Optional: small preview to confirm structure
    if isinstance(data, dict):
        bf = data.get("best_flights", [])
        of = data.get("other_flights", [])
        print("COUNTS", json.dumps({"best_flights": len(bf), "other_flights": len(of)}))
        if bf:
            segs = bf[0].get("flights") or []
            if segs:
                keys = ["airline_code", "airline", "flight_number", "departure_airport", "arrival_airport"]
                sample = {k: segs[0].get(k) for k in keys}
                print("SAMPLE_SEGMENT", json.dumps(sample, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
