"""Cache management for flight searches (extracted from enhanced_flight_search)."""
from __future__ import annotations
import json, sqlite3, hashlib, logging, os
from core.metrics import METRICS  # type: ignore
from core.db_utils import open_connection
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

class FlightSearchCache:
    """Manages local database cache for flight searches (24h freshness policy)."""
    def __init__(self, db_path: str = "DB/Main_DB.db"):
        # Make db path absolute relative to project root so running from /Main works
        if not os.path.isabs(db_path):  # type: ignore[name-defined]
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            candidate = os.path.normpath(os.path.join(base, db_path))
            self.db_path = candidate
        else:
            self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        # Ensure supporting index for cache lookups exists (idempotent)
        try:
            with open_connection(self.db_path) as conn:
                conn.execute("CREATE INDEX IF NOT EXISTS idx_flight_searches_cache_key ON flight_searches(cache_key)")
                # Ensure composite route+date index exists (performance improvement)
                try:
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_flight_searches_route_date ON flight_searches(departure_airport_code, arrival_airport_code, outbound_date)")
                except Exception:
                    pass
        except Exception as e:  # pragma: no cover
            self.logger.warning(f"Could not ensure cache_key index: {e}")

    # ------------------- key generation -------------------
    def generate_cache_key(self, search_params: Dict[str, Any]) -> str:
        normalized = {}
        for k, v in search_params.items():
            if v is not None:
                normalized[k] = v.lower() if isinstance(v, str) else v
        return hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()

    # ------------------- lookup -------------------
    def search_cache(self, search_params: Dict[str, Any], max_age_hours: int = 24) -> Optional[Dict[str, Any]]:
        try:
            cache_key = self.generate_cache_key(search_params)
            with open_connection(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cutoff = datetime.now() - timedelta(hours=max_age_hours)
                cur.execute(
                    """
                    SELECT fs.*, COUNT(fr.id) flight_count
                    FROM flight_searches fs
                    LEFT JOIN flight_results fr ON fs.search_id = fr.search_id
                    WHERE fs.cache_key = ? AND fs.created_at > ?
                    GROUP BY fs.search_id
                    ORDER BY fs.created_at DESC
                    LIMIT 1
                    """,
                    (cache_key, cutoff.isoformat())
                )
                row = cur.fetchone()
                if not row:
                    self.logger.info(f"[cache:{cache_key[:12]}] Cache MISS")
                    METRICS.inc('cache_misses')
                    return None
                hit_search_id = row['search_id'] if 'search_id' in row.keys() else 'unknown'
                self.logger.info(f"[{hit_search_id}] Cache HIT key={cache_key[:12]}")
                METRICS.inc('cache_hits')
                # Fetch flight results
                cur.execute(
                    """
                    SELECT id, total_price, price_currency, total_duration, layover_count, result_type,
                           carbon_emissions_flight, booking_token
                    FROM flight_results WHERE search_id = ? ORDER BY total_price ASC
                    """,
                    (row["search_id"],)
                )
                flights = cur.fetchall()
                best, other = [], []
                for (fid, price, curr, duration, layovers, rt, carbon, booking_token) in flights:
                    cur.execute(
                        """
                        SELECT departure_airport_code, arrival_airport_code, airline_code, flight_number,
                               departure_time, arrival_time, duration_minutes
                        FROM flight_segments WHERE flight_result_id = ? ORDER BY segment_order
                        """, (fid,)
                    )
                    seg_rows = cur.fetchall()
                    flight_obj = {
                        'price': f'{price} {curr}' if price and curr else None,
                        'total_duration': duration,
                        'layovers': [] if layovers == 0 else [{'duration': 'N/A'} for _ in range(layovers)],
                        'carbon_emissions': {'this_flight': carbon} if carbon else {},
                        'booking_token': booking_token,
                        'flights': []
                    }
                    for seg in seg_rows:
                        dep, arr, airline, fnum, dep_t, arr_t, seg_dur = seg
                        flight_obj['flights'].append({
                            'departure_airport': {'id': dep},
                            'arrival_airport': {'id': arr},
                            'airline': airline,
                            'flight_number': fnum,
                            'departure_time': dep_t,
                            'arrival_time': arr_t,
                            'duration': seg_dur
                        })
                    norm_type = 'best' if rt in ('best', 'best_flight') else 'other'
                    (best if norm_type == 'best' else other).append(flight_obj)
                return {
                    'search_id': row['search_id'],
                    'search_parameters': json.loads(row['raw_parameters']) if row['raw_parameters'] else {},
                    'cached': True,
                    'cache_timestamp': row['created_at'],
                    'flight_results_count': row['flight_count'],
                    'processing_status': 'cached_data',
                    'best_flights': best,
                    'other_flights': other
                }
        except Exception as e:
            self.logger.error(f"Error searching cache: {e}")
            return None

    # ------------------- cleanup -------------------
    def cleanup_old_data(self, max_age_hours: int = 24, prune_raw: bool = False):  # kept for compatibility
        """Remove expired cached search structures while (by default) preserving raw api_queries.

        Raw retention policy (authoritative, Sept 2025):
        - Raw API rows (api_queries) are retained indefinitely unless an *explicit* retention
          policy is applied via the session cleanup utility or prune_raw=True here.
        - This method only removes structured / derived tables to keep cache window fresh.
        """
        try:
            with open_connection(self.db_path) as conn:
                cur = conn.cursor()
                cutoff = datetime.now() - timedelta(hours=max_age_hours)
                cur.execute("SELECT search_id FROM flight_searches WHERE created_at < ?", (cutoff.isoformat(),))
                old_ids = [r[0] for r in cur.fetchall()]
                for sid in old_ids:
                    cur.execute("DELETE FROM layovers WHERE flight_result_id IN (SELECT id FROM flight_results WHERE search_id = ?)", (sid,))
                    cur.execute("DELETE FROM flight_segments WHERE flight_result_id IN (SELECT id FROM flight_results WHERE search_id = ?)", (sid,))
                    cur.execute("DELETE FROM flight_results WHERE search_id = ?", (sid,))
                    cur.execute("DELETE FROM price_insights WHERE search_id = ?", (sid,))
                    cur.execute("DELETE FROM flight_searches WHERE search_id = ?", (sid,))
                # Raw api_queries are only pruned when explicitly requested
                if prune_raw:
                    cur.execute("DELETE FROM api_queries WHERE created_at < ?", (cutoff.isoformat(),))
                conn.commit()
                if old_ids:
                    self.logger.info(f"Cleaned {len(old_ids)} expired searches (raw retained={not prune_raw})")
        except Exception as e:
            self.logger.error(f"Cleanup error: {e}")

__all__ = ['FlightSearchCache']