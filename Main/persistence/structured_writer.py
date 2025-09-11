"""Structured flight data writer.

Role:
    Convert raw API flight search payload into a fully normalized relational
    representation (flight_searches, flight_results, flight_segments, layovers,
    airlines, airports, price_insights). Designed for idempotent rewrites so a
    search_id can be safely reprocessed without duplicating subordinate rows.

Public Entry Point:
    StructuredFlightWriter.store(search_id, search_params, api_response, api_query_id)

Inputs:
    search_id: stable identifier from upstream API client.
    search_params: dict of original query params (used for flight_searches row & cache key regen).
    api_response: dict with best_flights/other_flights arrays matching SerpAPI shape.
    api_query_id: optional FK to raw api_queries table (for lineage).

Outputs / Side Effects:
    - Inserts/updates a single row in flight_searches (UPSERT on search_id).
    - Deletes prior flight_results/segments/layovers/price_insights for search_id then reinserts.
    - Inserts any newly discovered airlines (INSERT OR IGNORE) and optionally airports if
      PROCESSING_CONFIG['auto_extract_airports'] is enabled.
    - Emits structured log events efs.store.structured.* and logger info lines with counts.

Failure Handling:
    - Any exception bubbles as StructuredStorageError (wrapped) to allow caller to log metrics.
    - Partial writes avoided by single transaction commit at end.

Idempotency Notes:
    - Old subordinate rows are purged prior to reinsertion ensuring deterministic set.
    - price_insights cleaned then re-added (unique index enforced externally).
"""
from __future__ import annotations
from typing import Any
import json
import logging
from datetime import datetime

from Main.config import PROCESSING_CONFIG
from Main.core.db_utils import open_connection  # type: ignore
from Main.core.structured_logging import log_event, log_exception  # type: ignore
from Main.constants import Event, emit

class StructuredStorageError(Exception):
    pass

class StructuredFlightWriter:
    def __init__(self, db_path: str, logger: logging.Logger | None = None) -> None:
        self.db_path = db_path
        self.logger = logger or logging.getLogger(__name__)

    # Public API
    def store(self, search_id: str, search_params: dict[str, Any], api_response: dict[str, Any], api_query_id: int | None) -> None:  # noqa: ANN401
        try:
            self._store_impl(search_id, search_params, api_response, api_query_id)
        except Exception as e:  # pragma: no cover (defensive)
            log_exception(str(Event.STORE_STRUCTURED_ERROR), search_id=search_id, exc=e)
            raise

    # Internal implementation (adapted from original method)
    def _store_impl(self, search_id: str, search_params: dict[str, Any], api_response: dict[str, Any], api_query_id: int | None):  # noqa: ANN401
        auto_airports = bool(PROCESSING_CONFIG.get('auto_extract_airports', False))
        from Main.cache import FlightSearchCache  # local to avoid circular
        cache_key = FlightSearchCache(self.db_path).generate_cache_key(search_params)
        with open_connection(self.db_path) as conn:
            cur = conn.cursor()
            def _canon(code: Any) -> str:
                return str(code).strip().upper() if code else ''
            def _airport_exists(code: Any) -> bool:
                c = _canon(code); cur.execute("SELECT 1 FROM airports WHERE airport_code = ? LIMIT 1", (c,)); return cur.fetchone() is not None
            def _ensure_airport(code: Any) -> bool:
                c = _canon(code)
                if not c:
                    return False
                if _airport_exists(c):
                    return True
                if not auto_airports:
                    return False
                try:
                    cur.execute("INSERT OR IGNORE INTO airports(airport_code, airport_name) VALUES (?, ?)", (c, c))
                    return True
                except Exception:
                    return False
            dep_code = _canon(search_params.get('departure_id'))
            arr_code = _canon(search_params.get('arrival_id'))
            if not (_ensure_airport(dep_code) and _ensure_airport(arr_code)):
                self.logger.warning("Skipping structured storage: missing airports dep=%s arr=%s", dep_code, arr_code)
                return
            # Airline collection
            def _canon_airline(code: Any) -> str:
                s = str(code).strip().upper() if code else ''
                return s if (2 <= len(s) <= 3 and s.isalnum()) else ''
            def _derive_airline(seg: dict[str, Any]) -> str:
                fn = seg.get('flight_number')
                if not fn:
                    return ''
                head = str(fn).strip().split(' ')[0].upper()
                head = ''.join(ch for ch in head if ch.isalnum())
                return head[:2] if len(head) >= 2 else ''
            airlines: dict[str, str] = {}
            for group in (api_response.get('best_flights', []), api_response.get('other_flights', [])):
                for flight in group:
                    for seg in flight.get('flights', []):
                        code = _canon_airline(_derive_airline(seg)) or _canon_airline(seg.get('airline_code')) or _canon_airline(seg.get('airline'))
                        name = (seg.get('airline') or code or '').strip()
                        if code:
                            airlines[code] = name
            for code, name in airlines.items():
                cur.execute("INSERT OR IGNORE INTO airlines(airline_code, airline_name) VALUES (?, ?)", (code, name or code))
            # Idempotent cleanup for this search
            try:
                cur.execute("DELETE FROM price_insights WHERE search_id NOT IN (SELECT search_id FROM flight_searches)")
            except Exception:
                pass
            cur.execute("DELETE FROM layovers WHERE flight_result_id IN (SELECT id FROM flight_results WHERE search_id = ?)", (search_id,))
            cur.execute("DELETE FROM flight_segments WHERE flight_result_id IN (SELECT id FROM flight_results WHERE search_id = ?)", (search_id,))
            cur.execute("DELETE FROM flight_results WHERE search_id = ?", (search_id,))
            cur.execute("DELETE FROM price_insights WHERE search_id = ?", (search_id,))
            cur.execute(
                """
                INSERT INTO flight_searches (
                    search_id, search_timestamp, departure_airport_code, arrival_airport_code,
                    outbound_date, return_date, flight_type, adults, children,
                    infants_in_seat, infants_on_lap, travel_class, currency,
                    country_code, language_code, raw_parameters, response_status,
                    total_results, cache_key, api_query_id, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(search_id) DO UPDATE SET
                    search_timestamp=excluded.search_timestamp,
                    departure_airport_code=excluded.departure_airport_code,
                    arrival_airport_code=excluded.arrival_airport_code,
                    outbound_date=excluded.outbound_date,
                    return_date=excluded.return_date,
                    flight_type=excluded.flight_type,
                    adults=excluded.adults,
                    children=excluded.children,
                    infants_in_seat=excluded.infants_in_seat,
                    infants_on_lap=excluded.infants_on_lap,
                    travel_class=excluded.travel_class,
                    currency=excluded.currency,
                    country_code=excluded.country_code,
                    language_code=excluded.language_code,
                    raw_parameters=excluded.raw_parameters,
                    response_status=excluded.response_status,
                    total_results=excluded.total_results,
                    cache_key=excluded.cache_key,
                    api_query_id=excluded.api_query_id
                """,
                (
                    search_id,
                    datetime.now().isoformat(),
                    dep_code,
                    arr_code,
                    search_params.get('outbound_date'),
                    search_params.get('return_date'),
                    1 if search_params.get('return_date') else 2,
                    search_params.get('adults', 1),
                    search_params.get('children', 0),
                    search_params.get('infants_in_seat', 0),
                    search_params.get('infants_on_lap', 0),
                    search_params.get('travel_class', 1),
                    search_params.get('currency', 'USD'),
                    search_params.get('gl', 'us'),
                    search_params.get('hl', 'en'),
                    json.dumps(search_params),
                    'success',
                    len(api_response.get('best_flights', [])) + len(api_response.get('other_flights', [])),
                    cache_key,
                    api_query_id,
                    datetime.now().isoformat()
                )
            )
            flight_rows = []
            now_iso = datetime.now().isoformat()
            is_round_trip = bool(search_params.get('return_date'))
            for group, label in ((api_response.get('best_flights', []), 'best'), (api_response.get('other_flights', []), 'other')):
                for rank, flight in enumerate(group, 1):
                    legacy = 'best_flight' if label == 'best' else 'other_flight'
                    flight_type_text = flight.get('type') or ('Round trip' if is_round_trip else 'One way')
                    flight_rows.append((search_id, legacy, rank, flight.get('total_duration'), flight.get('price'), 'USD', flight_type_text, len(flight.get('layovers', [])), flight.get('carbon_emissions', {}).get('this_flight'), flight.get('carbon_emissions', {}).get('typical_for_this_route'), flight.get('carbon_emissions', {}).get('difference_percent'), flight.get('departure_token'), flight.get('booking_token'), flight.get('airline_logo'), now_iso))
            if flight_rows:
                cur.executemany("""
                    INSERT INTO flight_results (
                        search_id, result_type, result_rank, total_duration, total_price,
                        price_currency, flight_type, layover_count, carbon_emissions_flight,
                        carbon_emissions_typical, carbon_emissions_difference_percent,
                        departure_token, booking_token, airline_logo_url, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, flight_rows)
                cur.execute("SELECT id, result_type, result_rank FROM flight_results WHERE search_id = ?", (search_id,))
                id_map = {(r[1], r[2]): r[0] for r in cur.fetchall()}
                segment_rows = []
                layover_rows = []
                for group, label in ((api_response.get('best_flights', []), 'best'), (api_response.get('other_flights', []), 'other')):
                    for rank, flight in enumerate(group, 1):
                        fid = id_map.get(('best_flight' if label == 'best' else 'other_flight', rank))
                        if not fid:
                            continue
                        for order, seg in enumerate(flight.get('flights', []), 1):
                            dep_seg = seg.get('departure_airport', {})
                            arr_seg = seg.get('arrival_airport', {})
                            dep_code_seg = _canon(dep_seg.get('id'))
                            arr_code_seg = _canon(arr_seg.get('id'))
                            if not (_ensure_airport(dep_code_seg) and _ensure_airport(arr_code_seg)):
                                continue
                            al_code = _canon_airline(_derive_airline(seg)) or _canon_airline(seg.get('airline_code'))
                            if not al_code:
                                name_raw = (seg.get('airline') or '').upper()
                                derived = ''.join(ch for ch in name_raw if ch.isalnum())[:3]
                                if len(derived) >= 2:
                                    al_code = _canon_airline(derived)
                                else:
                                    al_code = 'ZZ'
                            try:
                                cur.execute("INSERT OR IGNORE INTO airlines(airline_code, airline_name) VALUES (?, ?)", (al_code, (seg.get('airline') or al_code)))
                            except Exception:
                                pass
                            segment_rows.append((fid, order, dep_code_seg, dep_seg.get('time'), arr_code_seg, arr_seg.get('time'), seg.get('duration'), seg.get('airplane'), al_code, seg.get('flight_number'), seg.get('travel_class'), seg.get('legroom'), seg.get('often_delayed_by_over_30_min', False), json.dumps(seg.get('extensions', [])), now_iso))
                        for order, lay in enumerate(flight.get('layovers', []), 1):
                            lay_code = _canon(lay.get('id'))
                            if not _ensure_airport(lay_code):
                                continue
                            layover_rows.append((fid, order, lay_code, lay.get('duration'), lay.get('overnight', False), now_iso))
                if segment_rows:
                    cur.executemany("""
                        INSERT INTO flight_segments (
                            flight_result_id, segment_order, departure_airport_code, departure_time,
                            arrival_airport_code, arrival_time, duration_minutes, airplane_model,
                            airline_code, flight_number, travel_class, legroom,
                            often_delayed, extensions, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, segment_rows)
                if layover_rows:
                    cur.executemany("""
                        INSERT INTO layovers (
                            flight_result_id, layover_order, airport_code, duration_minutes, is_overnight, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?)
                    """, layover_rows)
            if 'price_insights' in api_response:
                self._insert_price_insights(cur, search_id, api_response['price_insights'])
            conn.commit()
            emit(Event.STORE_STRUCTURED_SUCCESS, log_event, search_id=search_id)
            try:
                cur2 = conn.cursor()
                cur2.execute("SELECT COUNT(*) FROM flight_results WHERE search_id=?", (search_id,))
                fr_count = cur2.fetchone()[0]
                cur2.execute("SELECT COUNT(*) FROM flight_segments fs JOIN flight_results fr ON fs.flight_result_id=fr.id WHERE fr.search_id=?", (search_id,))
                seg_count = cur2.fetchone()[0]
                self.logger.info("Structured storage committed search_id=%s results=%s segments=%s cache_key=%s", search_id, fr_count, seg_count, cache_key[:12])
            except Exception:  # pragma: no cover
                pass

    def _insert_price_insights(self, cur, search_id: str, pi: dict[str, Any]):  # noqa: ANN001
        cur.execute(
            """
            INSERT INTO price_insights (search_id, lowest_price, price_level, typical_price_low, typical_price_high, price_history, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                search_id,
                pi.get('lowest_price'),
                pi.get('price_level'),
                pi.get('typical_price_range', [None, None])[0],
                pi.get('typical_price_range', [None, None])[1],
                json.dumps(pi.get('price_history', [])),
                datetime.now().isoformat()
            )
        )

__all__ = ['StructuredFlightWriter', 'StructuredStorageError']
