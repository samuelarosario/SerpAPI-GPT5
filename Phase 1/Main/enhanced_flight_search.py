"""Phase 1 refactored Enhanced Flight Search Client

Key changes vs original monolith:
 - Uses unified RateLimiter & FlightSearchValidator from common_validation
 - Central logging via logging_setup
 - Explicit transaction for storing search + related rows
 - Price parsing / normalization before DB persistence
 - Cache-first lookup (ported, trimmed for Phase 1 scope)
 - Cleaner public API: EnhancedFlightSearch.search_flights / search_week_range

Deferred for later phases:
 - Full route analytics & carbon metrics enrichment
 - Advanced price trend analytics persistence
 - Airline/airport metadata augmentation services
"""
from __future__ import annotations
import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple, List
import hashlib

from config import SERPAPI_CONFIG, RATE_LIMIT_CONFIG, get_api_key

# Ensure DB helper path is discoverable (root/DB)
import os, sys, pathlib as _p
_ROOT = _p.Path(__file__).resolve().parents[2]
_DB_PATH = _ROOT / 'DB'
if str(_DB_PATH) not in sys.path:
	sys.path.append(str(_DB_PATH))
from common_validation import RateLimiter, FlightSearchValidator, parse_price
from logging_setup import init_logging

try:
	# Re‑use original lightweight DB helper for now (future phase: specialized module)
	from database_helper import SerpAPIDatabase
except ImportError:  # Phase 1 isolation fallback
	class SerpAPIDatabase:  # type: ignore
		def __init__(self, db_path: str = "DB/Main_DB.db"):
			self.db_path = db_path

init_logging()
logger = logging.getLogger(__name__)

class _CacheAdapter:
	"""Minimal cache operations extracted from original implementation."""
	def __init__(self, db_path: str):
		self.db_path = db_path
		self.log = logging.getLogger(__name__)

	def _normalize_params(self, params: Dict[str, Any]) -> Dict[str, Any]:
		norm = {}
		for k, v in params.items():
			if v is None:
				continue
			if isinstance(v, str):
				norm[k] = v.strip().lower()
			else:
				norm[k] = v
		return norm

	def cache_key(self, params: Dict[str, Any]) -> str:
		normalized = self._normalize_params(params)
		return hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()

	def fetch(self, params: Dict[str, Any], max_age_hours: int) -> Optional[Dict[str, Any]]:
		key = self.cache_key(params)
		cutoff = datetime.now() - timedelta(hours=max_age_hours)
		try:
			with sqlite3.connect(self.db_path) as conn:
				conn.row_factory = sqlite3.Row
				cur = conn.cursor()
				cur.execute(
					"""
					SELECT fs.search_id, fs.raw_parameters, fs.created_at
					FROM flight_searches fs
					WHERE fs.cache_key = ? AND fs.created_at > ?
					ORDER BY fs.created_at DESC LIMIT 1
					""",
					(key, cutoff.isoformat())
				)
				row = cur.fetchone()
				if not row:
					return None
				search_id = row["search_id"]
				# Pull flight_results with segments
				cur.execute(
					"""SELECT id, result_type, total_price, price_currency, total_duration, layover_count, booking_token
						FROM flight_results WHERE search_id = ? ORDER BY total_price ASC NULLS LAST""",
					(search_id,)
				)
				flight_rows = cur.fetchall()
				best: List[Dict[str, Any]] = []
				other: List[Dict[str, Any]] = []
				for frow in flight_rows:
					fr_id = frow["id"]
					cur.execute(
						"""SELECT departure_airport_code, arrival_airport_code, departure_time, arrival_time, duration_minutes, airline_code, flight_number
							   FROM flight_segments WHERE flight_result_id = ? ORDER BY segment_order""",
						(fr_id,)
					)
					seg_rows = cur.fetchall()
					segments = []
					for s in seg_rows:
						segments.append({
							"departure_airport": {"id": s[0], "time": s[2]},
							"arrival_airport": {"id": s[1], "time": s[3]},
							"duration": s[4],
							"airline": s[5],
							"flight_number": s[6],
						})
					flight_obj = {
						"price": f"{frow['total_price']} {frow['price_currency']}" if frow["total_price"] else None,
						"total_duration": frow["total_duration"],
						"layovers": [{}] * (frow["layover_count"] or 0),
						"booking_token": frow["booking_token"],
						"flights": segments,
					}
					if frow["result_type"] == "best":
						best.append(flight_obj)
					else:
						other.append(flight_obj)
				return {
					"search_id": search_id,
					"search_parameters": json.loads(row["raw_parameters"] or "{}"),
					"cached": True,
					"cache_timestamp": row["created_at"],
					"best_flights": best,
					"other_flights": other,
				}
		except Exception as e:
			self.log.warning(f"Cache fetch error: {e}")
		return None

	def cleanup(self, max_age_hours: int):
		cutoff = datetime.now() - timedelta(hours=max_age_hours)
		try:
			with sqlite3.connect(self.db_path) as conn:
				cur = conn.cursor()
				cur.execute("DELETE FROM api_queries WHERE created_at < ?", (cutoff.isoformat(),))
		except Exception as e:
			self.log.debug(f"Cleanup skipped: {e}")

class EnhancedFlightSearch:
	def __init__(self, api_key: Optional[str] = None, db_path: str = "DB/Main_DB.db"):
		self.api_key = api_key or get_api_key()
		self.db_path = db_path
		self.rate_limiter = RateLimiter() if RATE_LIMIT_CONFIG['enable_rate_limiting'] else None
		self.cache = _CacheAdapter(db_path)
		from serpapi_client import SerpAPIFlightClient  # local Phase 1 client
		self.api_client = SerpAPIFlightClient(self.api_key)

	# ---------------- Public API -----------------
	def search_flights(self, *, departure_id: str, arrival_id: str, outbound_date: str, return_date: Optional[str] = None,
					   adults: int = 1, children: int = 0, infants_in_seat: int = 0, infants_on_lap: int = 0,
					   travel_class: int = 1, currency: str = 'USD', force_api: bool = False,
					   max_cache_age_hours: int = 24, enforce_horizon: bool = True, **extra) -> Dict[str, Any]:
		params: Dict[str, Any] = {
			'departure_id': departure_id,
			'arrival_id': arrival_id,
			'outbound_date': outbound_date,
			'return_date': return_date,
			'adults': adults,
			'children': children,
			'infants_in_seat': infants_in_seat,
			'infants_on_lap': infants_on_lap,
			'travel_class': travel_class,
			'currency': currency,
		}
		params.update(extra)

		is_valid, errors = FlightSearchValidator.validate_search_params(params, enforce_horizon=enforce_horizon)
		if not is_valid:
			return {'success': False, 'source': 'validation', 'errors': errors}

		# Cache check
		if not force_api:
			cached = self.cache.fetch(params, max_cache_age_hours)
			if cached:
				age = self._cache_age_hours(cached['cache_timestamp'])
				return {'success': True, 'source': 'cache', 'data': cached, 'cache_age_hours': age}

		if self.rate_limiter and not self.rate_limiter.can_make_request():
			return {'success': False, 'source': 'rate_limit', 'error': 'Rate limit exceeded'}

		# Decide search type
		if return_date:
			api_result = self.api_client.search_round_trip(departure_id, arrival_id, outbound_date, return_date, adults=adults,
														   children=children, infants_in_seat=infants_in_seat, infants_on_lap=infants_on_lap,
														   travel_class=travel_class, currency=currency)
		else:
			api_result = self.api_client.search_one_way(departure_id, arrival_id, outbound_date, adults=adults,
													 children=children, infants_in_seat=infants_in_seat, infants_on_lap=infants_on_lap,
													 travel_class=travel_class, currency=currency)

		if not api_result.get('success'):
			return {'success': False, 'source': 'api_error', 'error': api_result.get('error')}

		data = api_result.get('data') or {}
		search_id = api_result.get('search_id')
		if search_id:
			self._store_transaction(search_id, params, data)
		if self.rate_limiter:
			self.rate_limiter.record_request()
		return {'success': True, 'source': 'api', 'data': data, 'search_id': search_id}

	def search_week_range(self, *, departure_id: str, arrival_id: str, start_date: str, days: int = 7, **base_params) -> Dict[str, Any]:
		try:
			start_dt = datetime.strptime(start_date, '%Y-%m-%d')
		except ValueError:
			return {'success': False, 'error': 'Invalid start_date', 'source': 'validation'}
		results: Dict[str, Any] = {}
		flights: List[Dict[str, Any]] = []
		for offset in range(days):
			d = (start_dt + timedelta(days=offset)).strftime('%Y-%m-%d')
			res = self.search_flights(departure_id=departure_id, arrival_id=arrival_id, outbound_date=d, **base_params)
			results[d] = res
			if res.get('success'):
				data = res.get('data', {})
				for f in data.get('best_flights', []) + data.get('other_flights', []):
					f_copy = dict(f)
					f_copy['search_date'] = d
					flights.append(f_copy)
		return {
			'success': any(v.get('success') for v in results.values()),
			'source': 'week_range',
			'daily_results': results,
			'aggregated_flights': flights,
		}

	# ---------------- Internal helpers -----------------
	def _cache_age_hours(self, ts: str) -> float:
		try:
			t = datetime.fromisoformat(ts.replace('Z', '+00:00'))
			return (datetime.now() - t).total_seconds() / 3600.0
		except Exception:
			return 0.0

	def _store_transaction(self, search_id: str, params: Dict[str, Any], data: Dict[str, Any]) -> None:
		try:
			with sqlite3.connect(self.db_path) as conn:
				cur = conn.cursor()
				cur.execute('BEGIN')
				cache_key = self.cache.cache_key(params)
				total_results = len(data.get('best_flights', [])) + len(data.get('other_flights', []))
				cur.execute(
					"""INSERT OR REPLACE INTO flight_searches (
						search_id, search_timestamp, departure_airport_code, arrival_airport_code,
						outbound_date, return_date, flight_type, adults, children, infants_in_seat,
						infants_on_lap, travel_class, currency, country_code, language_code,
						raw_parameters, response_status, total_results, cache_key, created_at
					) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
					(
						search_id, datetime.now().isoformat(), params.get('departure_id'), params.get('arrival_id'),
						params.get('outbound_date'), params.get('return_date'), 1 if params.get('return_date') else 2,
						params.get('adults', 1), params.get('children', 0), params.get('infants_in_seat', 0), params.get('infants_on_lap', 0),
						params.get('travel_class', 1), params.get('currency', 'USD'), params.get('gl', 'us'), params.get('hl', 'en'),
						json.dumps(params), 'success', total_results, cache_key, datetime.now().isoformat()
					)
				)
				# Store flights
				def store_flights(collection: List[Dict[str, Any]], result_type: str):
					for rank, flight in enumerate(collection, 1):
						amount_int, currency_code = parse_price(flight.get('price'))
						cur.execute(
							"""INSERT INTO flight_results (
								search_id, result_type, result_rank, total_duration, total_price,
								price_currency, flight_type, layover_count, carbon_emissions_flight,
								carbon_emissions_typical, carbon_emissions_difference_percent, booking_token,
								airline_logo_url, created_at
							) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
							(
								search_id, result_type, rank, flight.get('total_duration'), amount_int,
								currency_code or params.get('currency','USD'), flight.get('type','One way'),
								len(flight.get('layovers', []) or []),
								(flight.get('carbon_emissions') or {}).get('this_flight'),
								(flight.get('carbon_emissions') or {}).get('typical_for_this_route'),
								(flight.get('carbon_emissions') or {}).get('difference_percent'),
								flight.get('booking_token'), flight.get('airline_logo'), datetime.now().isoformat()
							)
						)
						flight_result_id = cur.lastrowid
						# Segments
						for order, seg in enumerate(flight.get('flights', []), 1):
							cur.execute(
								"""INSERT INTO flight_segments (
									flight_result_id, segment_order, departure_airport_code, departure_time,
									arrival_airport_code, arrival_time, duration_minutes, airplane_model,
									airline_code, flight_number, travel_class, legroom, often_delayed, extensions, created_at
								) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
								(
									flight_result_id, order,
									(seg.get('departure_airport') or {}).get('id'), (seg.get('departure_airport') or {}).get('time'),
									(seg.get('arrival_airport') or {}).get('id'), (seg.get('arrival_airport') or {}).get('time'),
									seg.get('duration'), seg.get('airplane'), seg.get('airline'), seg.get('flight_number'),
									seg.get('travel_class'), seg.get('legroom'), seg.get('often_delayed_by_over_30_min', False),
									json.dumps(seg.get('extensions', [])), datetime.now().isoformat()
								)
							)
						# Layovers
						for order, lay in enumerate(flight.get('layovers', []), 1):
							cur.execute(
								"""INSERT INTO layovers (
									flight_result_id, layover_order, airport_code, duration_minutes, is_overnight, created_at
								) VALUES (?,?,?,?,?,?)""",
								(
									flight_result_id, order, lay.get('id'), lay.get('duration'), lay.get('overnight', False), datetime.now().isoformat()
								)
							)
				store_flights(data.get('best_flights', []), 'best')
				store_flights(data.get('other_flights', []), 'other')
				conn.commit()
		except Exception as e:
			logger.error(f"Persistence failed for {search_id}: {e}")

if __name__ == '__main__':
	import sys, argparse
	from date_utils import parse_date, DateParseError

	parser = argparse.ArgumentParser(description='Enhanced Flight Search (Phase 1)')
	parser.add_argument('departure', help='Departure airport IATA (e.g. MNL)')
	parser.add_argument('arrival', help='Arrival airport IATA (e.g. HND)')
	parser.add_argument('outbound_date', help='Outbound date (MM-DD-YYYY or MM-DD)')
	parser.add_argument('return_date', nargs='?', help='Optional return date (MM-DD-YYYY or MM-DD)')
	parser.add_argument('--adults', type=int, default=1)
	parser.add_argument('--children', type=int, default=0)
	parser.add_argument('--infants-seat', type=int, default=0)
	parser.add_argument('--infants-lap', type=int, default=0)
	parser.add_argument('--travel-class', type=int, default=1)
	parser.add_argument('--currency', default='USD')
	parser.add_argument('--force-api', action='store_true')
	parser.add_argument('--no-horizon', action='store_true', help='Disable date horizon validation')
	args = parser.parse_args()

	try:
		outbound_fmt = parse_date(args.outbound_date)
		return_fmt = parse_date(args.return_date) if args.return_date else None
	except DateParseError as e:
		print(f'Date error: {e}')
		sys.exit(1)

	try:
		client = EnhancedFlightSearch()
	except Exception as e:
		print(f'Initialization failed (API key?): {e}')
		sys.exit(2)

	result = client.search_flights(
		departure_id=args.departure.upper(),
		arrival_id=args.arrival.upper(),
		outbound_date=outbound_fmt,
		return_date=return_fmt,
		adults=args.adults,
		children=args.children,
		infants_in_seat=args.infants_seat,
		infants_on_lap=args.infants_lap,
		travel_class=args.travel_class,
		currency=args.currency,
		force_api=args.force_api,
		enforce_horizon=not args.no_horizon,
	)

	if result.get('success'):
		src = result.get('source')
		print(f'SUCCESS source={src} search_id={result.get("search_id")}')
		data = result.get('data') or {}
		best = len(data.get('best_flights', []))
		other = len(data.get('other_flights', []))
		print(f'Flights: best={best} other={other}')
	else:
		print('FAILED source=', result.get('source'), 'error=', result.get('error'), 'errors=', result.get('errors'))
		sys.exit(1)
