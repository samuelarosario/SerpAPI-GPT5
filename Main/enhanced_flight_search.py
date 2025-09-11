"""Enhanced Flight Search Client (orchestrator / façade).

Responsibilities:
    - Parameter validation / cache orchestration
    - Delegation to extracted services (inbound merge, week aggregation)
    - Persistence handoff to structured writer
    - Emission of standardized structured events

Out of Scope (handled elsewhere):
    - Data normalization (StructuredFlightWriter)
    - Multi-day logic (WeekRangeAggregator)
    - Inbound fallback (InboundMergeStrategy)

Notes:
    The client still contains CLI code and some legacy shims; future slimming
    can move CLI parsing + cleanup throttling into separate modules.
"""
import json
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from time import perf_counter
from typing import Any

# --- Path normalization for direct CLI execution ---------------------------------
# When this file is executed directly from the project "Main" directory, the
# package-qualified imports (e.g. `from Main.cache import FlightSearchCache`) will
# fail because the parent directory (containing the "Main" package) is not on
# sys.path. Tests/imports (python -m Main.enhanced_flight_search ...) are fine.
# This lightweight adjustment only runs for __main__ execution so library usage
# remains untouched.
if __name__ == "__main__":  # pragma: no cover (runtime convenience only)
    import sys as _sys
    parent = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if parent not in _sys.path:
        _sys.path.insert(0, parent)

import requests

from Main.cache import FlightSearchCache
from Main.config import RATE_LIMIT_CONFIG, SERPAPI_CONFIG, PROCESSING_CONFIG, get_api_key
# Added service/persistence imports (Option C extraction)
from Main.services.inbound_merge import InboundMergeStrategy  # type: ignore
from Main.services.week_aggregator import WeekRangeAggregator  # type: ignore
from Main.services.cli_date_parser import parse_cli_date as _cli_parse  # type: ignore
from Main.persistence.structured_writer import StructuredFlightWriter  # type: ignore

try:  # prefer real helper
    from DB.database_helper import SerpAPIDatabase  # type: ignore
except ImportError:  # pragma: no cover
    class SerpAPIDatabase:  # minimal fallback (no-op raw storage)
        def __init__(self, db_path: str):
            self.db_path = db_path
        def insert_api_response(self, **kwargs):  # pragma: no cover
            return None

from Main.core.common_validation import FlightSearchValidator, RateLimiter  # type: ignore
from Main.core.metrics import METRICS  # type: ignore
from Main.core.structured_logging import log_event, log_exception  # type: ignore
from Main.constants import Event, emit


class EnhancedFlightSearchClient:
    """Enhanced Flight Search Client with Local Database Cache"""
    
    def __init__(self, api_key: str | None = None, db_path: str = "DB/Main_DB.db"):
        """Initialize the enhanced client"""
        self.api_key = api_key or get_api_key()
        if not os.path.isabs(db_path):
            base = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            self.db_path = os.path.normpath(os.path.join(base, db_path))
        else:
            self.db_path = db_path

        # Initialize cache manager
        self.cache = FlightSearchCache(self.db_path)
        # Throttle marker for periodic cleanup (epoch seconds)
        self._last_cleanup_ts = None  # type: ignore

        # Ensure supporting unique constraint for price_insights (logical 1:1)
        try:
            from Main.core.db_utils import open_connection as _open_conn
            with _open_conn(self.db_path) as _c:
                _c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_price_insights_search_unique ON price_insights(search_id)")
        except Exception:
            pass

        # API configuration
        self.base_url = SERPAPI_CONFIG['base_url']
        self.engine = SERPAPI_CONFIG['engine']
        self.timeout = SERPAPI_CONFIG['timeout']
        self.max_retries = SERPAPI_CONFIG['max_retries']
        self.retry_delay = SERPAPI_CONFIG['retry_delay']

        self.rate_limiter = RateLimiter() if RATE_LIMIT_CONFIG['enable_rate_limiting'] else None
        self.session = requests.Session()

        # Setup logging
        self.logger = logging.getLogger(__name__)

        # Import original client for API calls
        from serpapi_client import SerpAPIFlightClient  # local import
        self.api_client = SerpAPIFlightClient(self.api_key) if self.api_key else None
        # Service composition root (new)
        self._inbound_merge = InboundMergeStrategy(logging.getLogger(__name__))
        self._week_agg = WeekRangeAggregator(logging.getLogger(__name__))
        self._writer = StructuredFlightWriter(self.db_path, logging.getLogger(__name__))
    
    def search_flights(self,
                       departure_id: str,
                       arrival_id: str,
                       outbound_date: str,
                       return_date: str | None = None,
                       adults: int = 1,
                       children: int = 0,
                       infants_in_seat: int = 0,
                       infants_on_lap: int = 0,
                       travel_class: int = 1,
                       currency: str = "USD",
                       max_cache_age_hours: int = 24,
                       force_api: bool = False,
                       one_way: bool = False,
                       **kwargs) -> dict[str, Any]:
        """
        Smart flight search that checks cache first, then API
        Defaults to round-trip searches for comprehensive data capture
        
        Args:
            departure_id: Departure airport IATA code
            arrival_id: Arrival airport IATA code  
            outbound_date: Outbound date (YYYY-MM-DD)
            return_date: Return date for round-trip (YYYY-MM-DD). 
                        If not provided, auto-generates date 7 days after outbound
            adults: Number of adult passengers
            children: Number of child passengers
            infants_in_seat: Number of infants with seats
            infants_on_lap: Number of infants on lap
            travel_class: Travel class (1=Economy, 2=Premium, 3=Business, 4=First)
            currency: Currency for prices
            max_cache_age_hours: Maximum age of cached data to accept
            force_api: Force API call even if cache exists
            **kwargs: Additional search parameters
            
        Returns:
            Flight search results with cache/API source indicated
            Always attempts round-trip search for comprehensive data
        """
        op_start = perf_counter()
        # Throttled structured cache cleanup (at most every 15 minutes)
        import time as _t
        now = _t.time()
        if (self._last_cleanup_ts is None) or (now - self._last_cleanup_ts > 900):
            self.cache.cleanup_old_data(max_cache_age_hours)
            self._last_cleanup_ts = now
        
        # Build search parameters
        search_params = {
            'departure_id': departure_id,
            'arrival_id': arrival_id,
            'outbound_date': outbound_date,
            'adults': adults,
            'children': children,
            'infants_in_seat': infants_in_seat,
            'infants_on_lap': infants_on_lap,
            'travel_class': travel_class,
            'currency': currency
        }
        
        # Auto-generate return date for round-trip searches to capture more data
        if not one_way and not return_date:
            from datetime import datetime, timedelta
            try:
                outbound_dt = datetime.strptime(outbound_date, '%Y-%m-%d')
                # Default return date: 7 days after outbound for better data capture
                return_dt = outbound_dt + timedelta(days=7)
                return_date = return_dt.strftime('%Y-%m-%d')
                self.logger.info(f"Auto-generated return date: {return_date} (7 days after outbound)")
            except ValueError:
                self.logger.warning(f"Could not parse outbound_date: {outbound_date}")
        
        # Always include return_date for round-trip searches (unless one-way explicit)
        if not one_way and return_date:
            search_params['return_date'] = return_date
            
        # Add additional parameters
        search_params.update(kwargs)
        
        # Validate parameters
        is_valid, errors = self._validate_search_params(search_params)
        if not is_valid:
            return {
                'success': False,
                'error': 'Validation failed',
                'errors': errors,
                'source': 'validation'
            }
        # Pre-compute cache key for logging
        cache_key = self.cache.generate_cache_key(search_params)
        emit(Event.SEARCH_START, log_event, route=f"{departure_id}-{arrival_id}", outbound=outbound_date, has_return=bool(return_date), cache_key=cache_key)
        # Step 1: Check local cache first (unless forced to use API)
        if not force_api:
            self.logger.info("Checking local database cache...")
            cached_result = self.cache.search_cache(search_params, max_cache_age_hours)
            if cached_result:
                self.logger.info(f"Using cached data from {cached_result['cache_timestamp']}")
                emit(Event.CACHE_HIT, log_event, search_id=cached_result.get('search_id'), cache_key=cache_key)
                duration_ms = int((perf_counter() - op_start) * 1000)
                emit(Event.SEARCH_SUCCESS, log_event, search_id=cached_result.get('search_id'), source='cache', duration_ms=duration_ms)
                return {
                    'success': True,
                    'source': 'cache',
                    'data': cached_result,
                    'cache_age_hours': self._calculate_cache_age(cached_result['cache_timestamp']),
                    'message': 'Data retrieved from local cache'
                }
            else:
                emit(Event.CACHE_MISS, log_event, cache_key=cache_key)

        # Step 2: No cache found or forced API - use API
        self.logger.info("Cache miss or forced API - making API request...")
        emit(Event.API_REQUEST, log_event, route=f"{departure_id}-{arrival_id}", cache_key=cache_key)

        if not self.api_client:
            emit(Event.API_ERROR, log_event, error='no_api_client', cache_key=cache_key)
            return {
                'success': False,
                'error': 'No API key available and no cached data found',
                'source': 'api_error'
            }

        try:
            if 'return_date' in search_params:
                self.logger.info("Making round-trip API call (return date provided)")
                api_result = self.api_client.search_round_trip(**search_params)
            else:
                self.logger.info("Making one-way API call (no return date available)")
                api_result = self.api_client.search_one_way(**search_params)

            if not api_result.get('success'):
                emit(Event.API_ERROR, log_event, cache_key=cache_key, search_id=api_result.get('search_id'), error=api_result.get('error'))
                return {
                    'success': False,
                    'error': api_result.get('error', 'API call failed'),
                    'source': 'api_error'
                }

            search_id = api_result.get('search_id')
            api_data = api_result.get('data')
            api_query_id = None

            # Store raw API response first (non-fatal on failure)
            try:
                if search_id and api_data:
                    dbh = SerpAPIDatabase(self.db_path)
                    api_query_id = dbh.insert_api_response(
                        query_parameters=search_params,
                        raw_response=json.dumps(api_data),
                        query_type='google_flights',
                        status_code=200,
                        api_endpoint='google_flights',
                        search_term=f"{search_params.get('departure_id','')}-{search_params.get('arrival_id','')}"
                    )
                    emit(Event.STORE_RAW_SUCCESS, log_event, search_id=search_id, api_query_id=api_query_id)
            except Exception as raw_err:
                self.logger.error(f"Failed to store raw API response: {raw_err}")
                log_exception(str(Event.STORE_RAW_ERROR), search_id=search_id, exc=raw_err)

            # Inbound merge delegation (ensures inbound leg if missing)
            try:
                api_data = self._inbound_merge.ensure_inbound(api_data, search_params, self.api_client)
            except Exception as _merge_err:  # pragma: no cover
                self.logger.warning(f"Inbound merge strategy failure: {_merge_err}")

            # Structured storage (non-fatal) via writer
            try:
                if search_id and api_data:
                    # Use backward-compatible wrapper so tests that monkeypatch
                    # _store_structured_data still trigger struct failure metrics.
                    self._store_structured_data(search_id, search_params, api_data, api_query_id)
                    self.logger.info(f"API call successful - stored complete flight data for search: {search_id}")
            except Exception as struct_err:
                self.logger.error(f"Structured storage failure: {struct_err}")
                try:
                    # Increment standardized metric counter for structured storage failures
                    from .constants import Metric  # local import to avoid circulars at module import time
                    METRICS.inc(Metric.STRUCTURED_STORAGE_FAILURES.value)
                except Exception:  # pragma: no cover - metrics failure is non-fatal
                    pass
                log_exception(str(Event.STORE_STRUCTURED_ERROR), search_id=search_id, exc=struct_err)

            # After storing, load back from DB so UI always reads a single, consistent shape
            try:
                db_view = self.cache.search_cache(search_params, max_cache_age_hours)
            except Exception:
                db_view = None
            duration_ms = int((perf_counter() - op_start) * 1000)
            emit(Event.SEARCH_SUCCESS, log_event, search_id=search_id, source='api', duration_ms=duration_ms)
            return {
                'success': True,
                'source': 'api',  # fresh API, but data is normalized via DB
                'data': db_view if db_view else api_data,
                'search_id': search_id,
                'message': 'Fresh data retrieved from API and normalized via DB' if db_view else 'Fresh data retrieved from API'
            }
        except Exception as e:
            self.logger.error(f"API call failed: {str(e)}")
            log_exception(str(Event.SEARCH_ERROR), exc=e, cache_key=cache_key)
            return {
                'success': False,
                'error': f'API call failed: {str(e)}',
                'source': 'api_exception'
            }
    
    def search_week_range(self, departure_id: str, arrival_id: str, start_date: str, **kwargs) -> dict[str, Any]:  # noqa: D401
        """Delegate to WeekRangeAggregator (extracted service)."""
        return self._week_agg.run_week(self, departure_id, arrival_id, start_date, **kwargs)

    def _analyze_week_price_trend(self, daily_results: dict) -> dict[str, Any]:  # pragma: no cover - legacy shim
        return self._week_agg._analyze_price_trend(daily_results)  # type: ignore[attr-defined]

    def _store_structured_data(self, search_id: str, search_params: dict[str, Any], api_response: dict[str, Any], api_query_id: int | None):  # noqa: D401
        """Deprecated shim retained for backward compatibility in tests.

        Provides a single interception point so tests monkeypatching this method
        can force a failure and still exercise standardized metric increments.
        """
        try:
            self._writer.store(search_id, search_params, api_response, api_query_id)
        except Exception:
            # Mirror the metric increment logic used in the main call site so
            # monkeypatching this wrapper surfaces as a structured storage failure.
            try:
                from .constants import Metric  # local import to avoid circulars
                METRICS.inc(Metric.STRUCTURED_STORAGE_FAILURES.value)
            except Exception:
                pass
            raise

    # ---------------- Internal validation bridge -----------------
    def _validate_search_params(self, params: dict[str, Any]):
        """Wrapper to reuse common validation (kept separate for easy patching/testing)."""
        return FlightSearchValidator.validate_search_params(params)
    
    def clear_cache(self, older_than_hours: int = 168) -> dict[str, Any]:
        """DEPRECATED: Raw API retention is indefinite by default.

        This method no longer deletes raw api_queries automatically to honor the
        authoritative retention policy. It now returns a no-op summary. If
        explicit raw pruning is required, use the dedicated session_cleanup.py
        utility with --raw-retention-days or --prune-raw-cache-age flags.
        """
        self.logger.warning("clear_cache() is deprecated and performs no action (raw retention policy). Use session_cleanup.py for pruning.")
        return {
            'success': True,
            'deleted_count': 0,
            'cutoff_time': (datetime.now() - timedelta(hours=older_than_hours)).isoformat(),
            'deprecated': True
        }
    
    def get_cache_stats(self) -> dict[str, Any]:
        """Get statistics about cached flight data.

        Adds raw api_queries count and delta since last stats invocation to help
        operators understand ingestion velocity without separate queries.
        """
        try:
            from Main.core.db_utils import open_connection as _open_conn
            with _open_conn(self.db_path) as conn:
                cursor = conn.cursor()
                # Total cached searches
                cursor.execute("SELECT COUNT(*) FROM flight_searches")
                total_searches = cursor.fetchone()[0]
                
                # Searches in last 24 hours (using api_queries.created_at authoritative)
                yesterday = datetime.now() - timedelta(hours=24)
                # Use created_at (authoritative) instead of query_timestamp for recent activity measure
                cursor.execute("""
                SELECT COUNT(*) FROM api_queries 
                WHERE created_at > ?
                """, (yesterday.isoformat(),))
                recent_searches = cursor.fetchone()[0]

                # Raw api_queries total + delta tracking
                cursor.execute("SELECT COUNT(*) FROM api_queries")
                raw_total = cursor.fetchone()[0]
                delta = None
                if not hasattr(self, '_last_raw_total'):
                    self._last_raw_total = raw_total  # type: ignore[attr-defined]
                else:
                    delta = raw_total - self._last_raw_total  # type: ignore[attr-defined]
                    self._last_raw_total = raw_total  # type: ignore[attr-defined]
                
                # Popular routes (defensive: only if columns exist)
                popular_routes = []
                try:
                    cursor.execute("PRAGMA table_info(flight_searches)")
                    cols = {row[1] for row in cursor.fetchall()}
                    if {'departure_id','arrival_id'} <= cols:
                        cursor.execute("""
                        SELECT departure_id, arrival_id, COUNT(*) as search_count
                        FROM flight_searches
                        GROUP BY departure_id, arrival_id
                        ORDER BY search_count DESC
                        LIMIT 5
                        """)
                        popular_routes = cursor.fetchall()
                except Exception:
                    # silently ignore missing columns
                    popular_routes = []
                
                return {
                    'total_cached_searches': total_searches,
                    'recent_searches_24h': recent_searches,
                    'raw_api_queries_total': raw_total,
                    'raw_api_queries_delta': delta,
                    'metrics': METRICS.snapshot(),
                    'popular_routes': [
                        {
                            'route': f"{route[0]}-{route[1]}",
                            'search_count': route[2]
                        }
                        for route in popular_routes
                    ]
                }
                
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {str(e)}")
            return {'error': str(e)}

    # ---------------- Small utility helpers -----------------
    def _calculate_cache_age(self, cache_timestamp: str) -> float:
        """Return cache age in hours given an ISO timestamp string.

        Accepts naive or aware ISO-8601 strings. Naive values are treated as
        local time (consistent with how created_at is currently stored).
        Falls back to 0.0 hours on parse errors.
        """
        try:
            # Handle common 'Z' suffix if present
            ts = cache_timestamp.replace('Z', '+00:00') if isinstance(cache_timestamp, str) else cache_timestamp
            dt = datetime.fromisoformat(ts)
        except Exception:
            try:
                # Last-resort: some ISO strings may use space separator
                dt = datetime.fromisoformat(str(cache_timestamp).strip().replace(' ', 'T'))
            except Exception:
                return 0.0
        try:
            if dt.tzinfo is None:
                # Naive -> assume local clock
                age_hours = (datetime.now() - dt).total_seconds() / 3600.0
            else:
                # Aware -> compare in the same tz
                age_hours = (datetime.now(dt.tzinfo) - dt).total_seconds() / 3600.0
            return max(0.0, age_hours)
        except Exception:
            return 0.0

def parse_cli_date(raw: str) -> str:  # noqa: D401
    """Backward compatible wrapper (moved to services.cli_date_parser)."""
    return _cli_parse(raw)


def _cli():  # minimal terminal interface
    import argparse
    import json as _json
    import sys as _sys

    from date_utils import DateParseError, validate_and_order
    def _print_helper():
        helper = """
Enhanced Flight Search CLI
Minimum required positional arguments:
    1) departure  (IATA code, e.g. MNL)
    2) arrival    (IATA code, e.g. POM)
    3) outbound_date (DD-MM-YYYY or DD-MM)  [Ambiguous inputs treated as DD-MM]

Optional:
    return_date (DD-MM-YYYY or DD-MM) for round-trip
    --week / -w  Perform 7-day range search starting outbound_date (ignores return_date)

Examples:
    python enhanced_flight_search.py MNL POM 30-11-2025
    python enhanced_flight_search.py MNL POM 30-11-2025 07-12-2025 --adults 2 --travel-class 3
    python enhanced_flight_search.py MNL POM 30-11 --week --include-airlines PX --max-price 800

Common Options:
    --adults N  --children N  --infants-seat N  --infants-lap N
    --travel-class 1|2|3|4 (1=Economy 2=Premium 3=Business 4=First)
    --currency USD
    --max-price 1200
    --include-airlines PX,CX --exclude-airlines AA,UA
    --deep-search  (enables deeper SerpAPI search)
    --raw          (print full JSON)
    --stats        (print cache statistics after run)

Exit Codes:
    0 success | 2 argument/date error | 1 other error
""".strip()
        print(helper)

    # Early minimal argument check before argparse formatting (positional count)
    if len([a for a in _sys.argv[1:] if not a.startswith('-')]) < 3:
        print("Error: minimum arguments not provided (need departure arrival outbound_date).\n")
        _print_helper()
        raise SystemExit(2)

    p = argparse.ArgumentParser(
        description=(
            "Enhanced Flight Search CLI (cache-first). Primary accepted date format: DD-MM-YYYY or DD-MM. "
            "Also accepts legacy MM-DD-YYYY / MM-DD. Ambiguous (<=12-<=12) treated as DD-MM per new policy."
        ),
        add_help=True
    )
    p.add_argument('departure', help='Departure airport code (IATA)')
    p.add_argument('arrival', help='Arrival airport code (IATA)')
    p.add_argument('outbound_date', help='Outbound date (MM-DD or MM-DD-YYYY)')
    p.add_argument('return_date', nargs='?', help='Optional return date (MM-DD or MM-DD-YYYY)')
    p.add_argument('--week', '-w', action='store_true', help='7-day range search starting outbound date (ignores return_date)')
    p.add_argument('--adults', type=int, default=1)
    p.add_argument('--children', type=int, default=0)
    p.add_argument('--infants-seat', type=int, default=0, dest='infants_in_seat')
    p.add_argument('--infants-lap', type=int, default=0, dest='infants_on_lap')
    p.add_argument('--travel-class', type=int, default=1, choices=[1,2,3,4], help='1=Economy 2=Premium 3=Business 4=First')
    p.add_argument('--currency', default='USD')
    p.add_argument('--max-price', type=int)
    p.add_argument('--include-airlines', help='Comma-separated airline codes to include')
    p.add_argument('--exclude-airlines', help='Comma-separated airline codes to exclude')
    p.add_argument('--deep-search', action='store_true')
    p.add_argument('--raw', action='store_true', help='Print full JSON payload')
    p.add_argument('--stats', action='store_true', help='Print cache stats after search')
    args = p.parse_args()

    try:
        outbound_fmt = parse_cli_date(args.outbound_date)
        ret_fmt = parse_cli_date(args.return_date) if (args.return_date and not args.week) else None
        if ret_fmt:
            validate_and_order(outbound_fmt, ret_fmt)
    except DateParseError as e:
        print(f"Date error: {e}\n")
        _print_helper()
        raise SystemExit(2) from None

    client = EnhancedFlightSearchClient()

    common_kwargs = dict(
        adults=args.adults,
        children=args.children,
        infants_in_seat=args.infants_in_seat,
        infants_on_lap=args.infants_on_lap,
        travel_class=args.travel_class,
        currency=args.currency,
        deep_search=args.deep_search
    )
    if args.max_price is not None:
        common_kwargs['max_price'] = args.max_price
    if args.include_airlines:
        common_kwargs['include_airlines'] = [a.strip().upper() for a in args.include_airlines.split(',') if a.strip()]
    if args.exclude_airlines:
        common_kwargs['exclude_airlines'] = [a.strip().upper() for a in args.exclude_airlines.split(',') if a.strip()]

    if args.week:
        result = client.search_week_range(
            args.departure.upper(), args.arrival.upper(), outbound_fmt, **common_kwargs
        )
    else:
        result = client.search_flights(
            args.departure.upper(), args.arrival.upper(), outbound_fmt, ret_fmt, **common_kwargs
        )

    # Summary output
    if result.get('success'):
        src = result.get('source')
        print(f"✅ Success ({src})")
        if 'cache_age_hours' in result:
            print(f"Cache Age: {result['cache_age_hours']:.3f}h")
        if args.week:
            summary = result.get('summary', {})
            print(f"Dates: {result.get('date_range')}")
            print(f"Flights: {summary.get('total_flights_found', 0)} across {summary.get('successful_searches', 0)} days")
        else:
            data = result.get('data', {})
            print(f"Flights: {len(data.get('best_flights', []))} best / {len(data.get('other_flights', []))} other")
    else:
        print(f"❌ Failed: {result.get('error','unknown error')}")

    if args.raw:
        print("\nRAW RESULT JSON:")
        print(_json.dumps(result, indent=2)[:20000])  # safety truncate

    if args.stats:
        stats = client.get_cache_stats()
        print("\nCache Stats:", stats)

if __name__ == "__main__":
    _cli()
