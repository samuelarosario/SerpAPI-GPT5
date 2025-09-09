"""Enhanced Flight Search Client with Local Database Cache.

Cache-first strategy; raw API data retained by default per retention policy.
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
from Main.config import RATE_LIMIT_CONFIG, SERPAPI_CONFIG, get_api_key

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
        from serpapi_client import SerpAPIFlightClient
        self.api_client = SerpAPIFlightClient(self.api_key) if self.api_key else None
    
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
        if not return_date:
            from datetime import datetime, timedelta
            try:
                outbound_dt = datetime.strptime(outbound_date, '%Y-%m-%d')
                # Default return date: 7 days after outbound for better data capture
                return_dt = outbound_dt + timedelta(days=7)
                return_date = return_dt.strftime('%Y-%m-%d')
                self.logger.info(f"Auto-generated return date: {return_date} (7 days after outbound)")
            except ValueError:
                self.logger.warning(f"Could not parse outbound_date: {outbound_date}")
        
        # Always include return_date for round-trip searches
        if return_date:
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
        log_event('efs.search.start', route=f"{departure_id}-{arrival_id}", outbound=outbound_date, has_return=bool(return_date), cache_key=cache_key)
        # Step 1: Check local cache first (unless forced to use API)
        if not force_api:
            self.logger.info("Checking local database cache...")
            cached_result = self.cache.search_cache(search_params, max_cache_age_hours)
            
            if cached_result:
                self.logger.info(f"Using cached data from {cached_result['cache_timestamp']}")
                log_event('efs.cache.hit', search_id=cached_result.get('search_id'), cache_key=cache_key)
                duration_ms = int((perf_counter() - op_start) * 1000)
                log_event('efs.search.success', search_id=cached_result.get('search_id'), source='cache', duration_ms=duration_ms)
                return {
                    'success': True,
                    'source': 'cache',
                    'data': cached_result,
                    'cache_age_hours': self._calculate_cache_age(cached_result['cache_timestamp']),
                    'message': 'Data retrieved from local cache'
                }
            else:
                log_event('efs.cache.miss', cache_key=cache_key)
        
        # Step 2: No cache found or forced API - use API
        self.logger.info("Cache miss or forced API - making API request...")
        log_event('efs.api.request', route=f"{departure_id}-{arrival_id}", cache_key=cache_key)
        
        if not self.api_client:
            log_event('efs.api.error', error='no_api_client', cache_key=cache_key)
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
                log_event('efs.api.error', cache_key=cache_key, search_id=api_result.get('search_id'), error=api_result.get('error'))
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
                    log_event('efs.store.raw.success', search_id=search_id, api_query_id=api_query_id)
            except Exception as raw_err:
                self.logger.error(f"Failed to store raw API response: {raw_err}")
                log_exception('efs.store.raw.error', search_id=search_id, exc=raw_err)

            # Structured storage (non-fatal)
            try:
                if search_id and api_data:
                    self._store_structured_data(search_id, search_params, api_data, api_query_id)
                    self.logger.info(f"API call successful - stored complete flight data for search: {search_id}")
                    log_event('efs.store.structured.success', search_id=search_id)
            except Exception as struct_err:
                self.logger.error(f"Structured storage failure: {struct_err}")
                try:
                    METRICS.inc('structured_storage_failures')
                except Exception:
                    pass
                log_exception('efs.store.structured.error', search_id=search_id, exc=struct_err)

            duration_ms = int((perf_counter() - op_start) * 1000)
            log_event('efs.search.success', search_id=search_id, source='api', duration_ms=duration_ms)
            return {
                'success': True,
                'source': 'api',
                'data': api_data,
                'search_id': search_id,
                'message': 'Fresh data retrieved from API'
            }
        except Exception as e:
            self.logger.error(f"API call failed: {str(e)}")
            log_exception('efs.search.error', exc=e, cache_key=cache_key)
            return {
                'success': False,
                'error': f'API call failed: {str(e)}',
                'source': 'api_exception'
            }
    
    def search_week_range(self,
                          departure_id: str,
                          arrival_id: str,
                          start_date: str,
                          **kwargs) -> dict[str, Any]:
        """
        Search flights for 7 consecutive days starting from start_date
        Returns aggregated results with date-wise breakdown and price trends
        
        Args:
            departure_id: Departure airport IATA code
            arrival_id: Arrival airport IATA code
            start_date: Starting date for 7-day search (YYYY-MM-DD)
            **kwargs: Additional search parameters (adults, children, travel_class, etc.)
            
        Returns:
            Dict containing:
            - success: Boolean indicating overall success
            - source: 'week_range'
            - date_range: String showing search range
            - daily_results: Dict of results for each date
            - best_week_flights: Top flights across all dates
            - price_trend: Price analysis across the week
            - summary: Week search statistics
        """
        from datetime import datetime, timedelta

        self.logger.info(f"Starting week range search: {departure_id} → {arrival_id} from {start_date}")
        log_event('efs.week.start', route=f"{departure_id}-{arrival_id}", start_date=start_date)

        try:
            # Parse start date
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            return {
                'success': False,
                'error': f'Invalid start_date format: {start_date}. Use YYYY-MM-DD',
                'source': 'week_range_validation'
            }

        # Calculate end date
        end_dt = start_dt + timedelta(days=6)
        end_date = end_dt.strftime('%Y-%m-%d')

        # Initialize results containers
        daily_results: dict[str, Any] = {}
        all_flights: list[dict[str, Any]] = []
        successful_searches = 0
        total_flights_found = 0

        # Search each day in the 7-day range
        for day_offset in range(7):
            search_date = (start_dt + timedelta(days=day_offset)).strftime('%Y-%m-%d')
            day_name = (start_dt + timedelta(days=day_offset)).strftime('%A')

            self.logger.info(f"Searching day {day_offset + 1}/7: {search_date} ({day_name})")
            log_event('efs.week.day.start', date=search_date, day_offset=day_offset)

            # Use existing search_flights method for each date
            daily_result = self.search_flights(departure_id, arrival_id, search_date, **kwargs)

            if daily_result.get('success'):
                successful_searches += 1
                daily_results[search_date] = {
                    'result': daily_result,
                    'day_name': day_name,
                    'day_offset': day_offset
                }

                # Extract flights from daily result
                data = daily_result.get('data', {})
                best_flights = data.get('best_flights', [])
                other_flights = data.get('other_flights', [])

                # Tag flights with search date info and add to aggregated list
                for flight in best_flights + other_flights:
                    flight_copy = flight.copy()
                    flight_copy['search_date'] = search_date
                    flight_copy['day_name'] = day_name
                    flight_copy['day_offset'] = day_offset
                    flight_copy['is_best'] = flight in best_flights
                    all_flights.append(flight_copy)

                daily_count = len(best_flights) + len(other_flights)
                total_flights_found += daily_count
                self.logger.info(f"  Found {daily_count} flights for {search_date}")
                log_event('efs.week.day.success', date=search_date, flights=daily_count)
            else:
                daily_results[search_date] = {
                    'result': daily_result,
                    'day_name': day_name,
                    'day_offset': day_offset,
                    'error': daily_result.get('error', 'Search failed')
                }
                self.logger.warning(f"  Search failed for {search_date}: {daily_result.get('error')}")
                log_event('efs.week.day.error', date=search_date, error=daily_result.get('error'))

        # Sort all flights by price across all dates
        def extract_price(flight: dict[str, Any]):
            price_str = flight.get('price', '9999 USD')
            try:
                return float(price_str.replace(' USD', '').replace(',', ''))
            except Exception:
                return 9999.0

        all_flights.sort(key=extract_price)

        # Analyze price trends
        price_trend = self._analyze_week_price_trend(daily_results)

        # Create summary statistics
        summary = {
            'total_days_searched': 7,
            'successful_searches': successful_searches,
            'failed_searches': 7 - successful_searches,
            'total_flights_found': total_flights_found,
            'avg_flights_per_day': round(total_flights_found / max(successful_searches, 1), 1),
            'date_range': f"{start_date} to {end_date}",
            'cheapest_day': None,
            'most_expensive_day': None
        }

        # Find cheapest and most expensive days
        if price_trend['daily_min_prices']:
            min_price_day = min(price_trend['daily_min_prices'].items(), key=lambda x: x[1])
            max_price_day = max(price_trend['daily_min_prices'].items(), key=lambda x: x[1])
            summary['cheapest_day'] = {'date': min_price_day[0], 'price': min_price_day[1]}
            summary['most_expensive_day'] = {'date': max_price_day[0], 'price': max_price_day[1]}

        result = {
            'success': successful_searches > 0,
            'source': 'week_range',
            'date_range': f"{start_date} to {end_date}",
            'daily_results': daily_results,
            'best_week_flights': all_flights[:10],  # Top 10 flights across all dates
            'all_week_flights': all_flights,
            'price_trend': price_trend,
            'summary': summary
        }

        if successful_searches == 0:
            result['error'] = 'No successful searches in the 7-day range'
        elif successful_searches < 7:
            result['warning'] = f'Only {successful_searches}/7 days returned results'
        self.logger.info(f"Week range search completed: {successful_searches}/7 days successful, {total_flights_found} total flights")
        log_event('efs.week.complete', successful_days=successful_searches, total_flights=total_flights_found)

        return result

    # ---------------- Internal validation bridge -----------------
    def _validate_search_params(self, params: dict[str, Any]):
        """Wrapper to reuse common validation (kept separate for easy patching/testing)."""
        return FlightSearchValidator.validate_search_params(params)
    
    def _analyze_week_price_trend(self, daily_results: dict) -> dict[str, Any]:
        """Analyze price trends across the week"""
        daily_min_prices = {}
        daily_avg_prices = {}
        daily_flight_counts = {}
        weekday_analysis = {'weekday': [], 'weekend': []}
        
        for date_str, day_data in daily_results.items():
            if 'error' in day_data:
                continue
                
            daily_result = day_data['result']
            day_name = day_data['day_name']
            
            data = daily_result.get('data', {})
            all_day_flights = data.get('best_flights', []) + data.get('other_flights', [])
            
            if all_day_flights:
                # Extract prices for this day
                prices = []
                for flight in all_day_flights:
                    try:
                        price = float(flight.get('price', '0').replace(' USD', '').replace(',', ''))
                        if price > 0:
                            prices.append(price)
                    except Exception:
                        continue
                
                # Calculate daily min and avg prices
                daily_min_prices[date_str] = min(prices)
                daily_avg_prices[date_str] = sum(prices) / len(prices)
                
                # Classify day as weekday or weekend
                if day_name in ['Saturday', 'Sunday']:
                    weekday_analysis['weekend'].append(date_str)
                else:
                    weekday_analysis['weekday'].append(date_str)
        
        # Overall trends
        trend_analysis = {
            'overall_price_trend': 'stable',
            'price_increase_days': [],
            'price_decrease_days': []
        }
        
        # Compare first and last day for trend direction
        if len(daily_min_prices) > 1:
            sorted_days = sorted(daily_min_prices.keys())
            first_day = sorted_days[0]
            last_day = sorted_days[-1]
            
            if daily_min_prices[last_day] < daily_min_prices[first_day]:
                trend_analysis['overall_price_trend'] = 'decreasing'
            elif daily_min_prices[last_day] > daily_min_prices[first_day]:
                trend_analysis['overall_price_trend'] = 'increasing'
        
        return {
            'daily_min_prices': daily_min_prices,
            'daily_avg_prices': daily_avg_prices,
            'daily_flight_counts': daily_flight_counts,
            'weekday_analysis': weekday_analysis,
            'trend_analysis': trend_analysis
        }
    
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

    # ---------------- Internal structured storage (extracted) -----------------
    def _store_structured_data(self, search_id: str, search_params: dict[str, Any], api_response: dict[str, Any], api_query_id: int | None):
        """Persist normalized flight data (idempotent for a given search_id).

        NOTE: Foreign key constraints require referenced airport & airline rows
        to exist. Minimal upserts are performed to avoid silent FK failures
        that previously caused inserts to be rolled back (manifesting as the
        UI showing source=api but no row in flight_searches).
        """
        try:
            cache_key = self.cache.generate_cache_key(search_params)
            from Main.core.db_utils import open_connection as _open_conn
            with _open_conn(self.db_path) as conn:
                cur = conn.cursor()
                # --- Airports are managed manually: do not write to airports table ---
                # Validate presence of required airport codes; if missing, skip storage to respect FKs
                def _canon(code: Any) -> str:
                    return str(code).strip().upper() if code else ''

                def _airport_exists(code: Any) -> bool:
                    c = _canon(code)
                    if not c:
                        return False
                    cur.execute("SELECT 1 FROM airports WHERE airport_code = ? LIMIT 1", (c,))
                    return cur.fetchone() is not None

                dep_code = _canon(search_params.get('departure_id'))
                arr_code = _canon(search_params.get('arrival_id'))
                if not dep_code or not arr_code or not (_airport_exists(dep_code) and _airport_exists(arr_code)):
                    self.logger.warning("Skipping structured storage: missing airports for search dep=%s arr=%s", dep_code, arr_code)
                    return

                # Collect airline codes (IATA/ICAO) from segments; do not touch airports
                def _canon_airline(code: Any) -> str:
                    s = str(code).strip().upper() if code else ''
                    return s if (2 <= len(s) <= 3 and s.isalnum()) else ''
                airlines: dict[str, str] = {}
                for group in (api_response.get('best_flights', []), api_response.get('other_flights', [])):
                    for flight in group:
                        for seg in flight.get('flights', []):
                            code = _canon_airline(seg.get('airline_code') or seg.get('airline'))
                            name = (seg.get('airline') or code or '').strip()
                            if code:
                                airlines[code] = name
                for code, name in airlines.items():
                    cur.execute("INSERT OR IGNORE INTO airlines(airline_code, airline_name) VALUES (?, ?)", (code, name or code))

                # Idempotent cleanup
                # Also proactively remove any orphaned price_insights left from legacy runs
                try:
                    cur.execute("DELETE FROM price_insights WHERE search_id NOT IN (SELECT search_id FROM flight_searches)")
                except Exception:
                    pass
                cur.execute("DELETE FROM layovers WHERE flight_result_id IN (SELECT id FROM flight_results WHERE search_id = ?)", (search_id,))
                cur.execute("DELETE FROM flight_segments WHERE flight_result_id IN (SELECT id FROM flight_results WHERE search_id = ?)", (search_id,))
                cur.execute("DELETE FROM flight_results WHERE search_id = ?", (search_id,))
                cur.execute("DELETE FROM price_insights WHERE search_id = ?", (search_id,))
                # Upsert using ON CONFLICT to avoid REPLACE (which deletes parent rows and can violate FKs)
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
                # Batch collect flights
                flight_rows: list[tuple] = []
                now_iso = datetime.now().isoformat()
                for group, label in ((api_response.get('best_flights', []), 'best'), (api_response.get('other_flights', []), 'other')):
                    for rank, flight in enumerate(group, 1):
                        legacy = 'best_flight' if label == 'best' else 'other_flight'
                        flight_rows.append((
                            search_id, legacy, rank,
                            flight.get('total_duration'),
                            flight.get('price'),
                            'USD',
                            flight.get('type', 'One way'),
                            len(flight.get('layovers', [])),
                            flight.get('carbon_emissions', {}).get('this_flight'),
                            flight.get('carbon_emissions', {}).get('typical_for_this_route'),
                            flight.get('carbon_emissions', {}).get('difference_percent'),
                            flight.get('departure_token'),
                            flight.get('booking_token'),
                            flight.get('airline_logo'),
                            now_iso
                        ))
                if flight_rows:
                    cur.executemany(
                        """
                        INSERT INTO flight_results (
                            search_id, result_type, result_rank, total_duration, total_price,
                            price_currency, flight_type, layover_count, carbon_emissions_flight,
                            carbon_emissions_typical, carbon_emissions_difference_percent,
                            departure_token, booking_token, airline_logo_url, created_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, flight_rows
                    )
                    # Map ids
                    cur.execute("SELECT id, result_type, result_rank FROM flight_results WHERE search_id = ?", (search_id,))
                    id_map = {(r[1], r[2]): r[0] for r in cur.fetchall()}
                    segment_rows: list[tuple] = []
                    layover_rows: list[tuple] = []
                    for group, label in ((api_response.get('best_flights', []), 'best'), (api_response.get('other_flights', []), 'other')):
                        for rank, flight in enumerate(group, 1):
                            fid = id_map.get(('best_flight' if label=='best' else 'other_flight', rank))
                            if not fid:
                                continue
                            for order, seg in enumerate(flight.get('flights', []), 1):
                                dep = seg.get('departure_airport', {})
                                arr = seg.get('arrival_airport', {})
                                dep_code_seg = _canon(dep.get('id'))
                                arr_code_seg = _canon(arr.get('id'))
                                # Only include segments when both airports exist
                                if not (_airport_exists(dep_code_seg) and _airport_exists(arr_code_seg)):
                                    continue
                                al_code = _canon_airline(seg.get('airline_code') or seg.get('airline'))
                                # If missing/invalid, derive from airline name or use 'ZZ' fallback to keep segment (FK-safe)
                                if not al_code:
                                    name_raw = (seg.get('airline') or '').upper()
                                    derived = ''.join(ch for ch in name_raw if ch.isalnum())[:3]
                                    if len(derived) >= 2:
                                        al_code = derived[:3]
                                    else:
                                        al_code = 'ZZ'
                                # Ensure airline row exists for FK
                                try:
                                    cur.execute("INSERT OR IGNORE INTO airlines(airline_code, airline_name) VALUES (?, ?)", (al_code, (seg.get('airline') or al_code)))
                                except Exception:
                                    pass
                                segment_rows.append((
                                    fid, order,
                                    dep_code_seg, dep.get('time'),
                                    arr_code_seg, arr.get('time'),
                                    seg.get('duration'), seg.get('airplane'),
                                    al_code, seg.get('flight_number'),
                                    seg.get('travel_class'), seg.get('legroom'),
                                    seg.get('often_delayed_by_over_30_min', False),
                                    json.dumps(seg.get('extensions', [])),
                                    now_iso
                                ))
                            for order, lay in enumerate(flight.get('layovers', []), 1):
                                lay_code = _canon(lay.get('id'))
                                if not _airport_exists(lay_code):
                                    continue
                                layover_rows.append((
                                    fid, order,
                                    lay_code, lay.get('duration'), lay.get('overnight', False), now_iso
                                ))
                    if segment_rows:
                        # No airports upserts here; airlines only (already inserted above if needed)
                        cur.executemany(
                            """
                            INSERT INTO flight_segments (
                                flight_result_id, segment_order, departure_airport_code, departure_time,
                                arrival_airport_code, arrival_time, duration_minutes, airplane_model,
                                airline_code, flight_number, travel_class, legroom,
                                often_delayed, extensions, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, segment_rows
                        )
                    if layover_rows:
                        cur.executemany(
                            """
                            INSERT INTO layovers (
                                flight_result_id, layover_order, airport_code, duration_minutes, is_overnight, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?)
                            """, layover_rows
                        )
                if 'price_insights' in api_response:
                    self._insert_price_insights(cur, search_id, api_response['price_insights'])
                conn.commit()
                try:
                    # Post-commit verification (counts)
                    cur2 = conn.cursor()
                    cur2.execute("SELECT COUNT(*) FROM flight_results WHERE search_id=?", (search_id,))
                    fr_count = cur2.fetchone()[0]
                    cur2.execute("SELECT COUNT(*) FROM flight_segments fs JOIN flight_results fr ON fs.flight_result_id=fr.id WHERE fr.search_id=?", (search_id,))
                    seg_count = cur2.fetchone()[0]
                    self.logger.info(f"Structured storage committed search_id={search_id} results={fr_count} segments={seg_count} cache_key={cache_key[:12]}")
                except Exception:  # pragma: no cover
                    pass
        except Exception as e:  # pragma: no cover
            # Log full class name to aid debugging of FK vs other failures
            self.logger.error(f"Structured storage error: {e.__class__.__name__}: {e}")

    def _insert_flight_result(self, cur, search_id: str, flight: dict[str, Any], kind: str, rank: int):
        legacy = 'best_flight' if kind == 'best' else 'other_flight'
        cur.execute(
            """
            INSERT INTO flight_results (
                search_id, result_type, result_rank, total_duration, total_price,
                price_currency, flight_type, layover_count, carbon_emissions_flight,
                carbon_emissions_typical, carbon_emissions_difference_percent,
                departure_token, booking_token, airline_logo_url, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                search_id, legacy, rank,
                flight.get('total_duration'),
                flight.get('price'),
                'USD',
                flight.get('type', 'One way'),
                len(flight.get('layovers', [])),
                flight.get('carbon_emissions', {}).get('this_flight'),
                flight.get('carbon_emissions', {}).get('typical_for_this_route'),
                flight.get('carbon_emissions', {}).get('difference_percent'),
                flight.get('departure_token'),
                flight.get('booking_token'),
                flight.get('airline_logo'),
                datetime.now().isoformat()
            )
        )
        flight_result_id = cur.lastrowid
        for order, seg in enumerate(flight.get('flights', []), 1):
            self._insert_segment(cur, flight_result_id, seg, order)
        for order, lay in enumerate(flight.get('layovers', []), 1):
            self._insert_layover(cur, flight_result_id, lay, order)

    def _insert_segment(self, cur, flight_result_id: int, seg: dict[str, Any], order: int):
        dep = seg.get('departure_airport', {})
        arr = seg.get('arrival_airport', {})
        # Minimal airport+airline upserts removed for brevity; could re-add if needed
        cur.execute(
            """
            INSERT INTO flight_segments (
                flight_result_id, segment_order, departure_airport_code, departure_time,
                arrival_airport_code, arrival_time, duration_minutes, airplane_model,
                airline_code, flight_number, travel_class, legroom,
                often_delayed, extensions, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                flight_result_id, order,
                dep.get('id'), dep.get('time'),
                arr.get('id'), arr.get('time'),
                seg.get('duration'), seg.get('airplane'),
                seg.get('airline'), seg.get('flight_number'),
                seg.get('travel_class'), seg.get('legroom'),
                seg.get('often_delayed_by_over_30_min', False),
                json.dumps(seg.get('extensions', [])),
                datetime.now().isoformat()
            )
        )

    def _insert_layover(self, cur, flight_result_id: int, lay: dict[str, Any], order: int):
        cur.execute(
            """
            INSERT INTO layovers (flight_result_id, layover_order, airport_code, duration_minutes, is_overnight, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                flight_result_id, order,
                lay.get('id'), lay.get('duration'), lay.get('overnight', False), datetime.now().isoformat()
            )
        )

    def _insert_price_insights(self, cur, search_id: str, pi: dict[str, Any]):
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

def parse_cli_date(raw: str) -> str:
    """Parse CLI date inputs supporting DD-MM[-YYYY] preferred & legacy MM-DD forms.

    Rules:
    1. If first component >12 -> interpret as DD-MM.
    2. If second component >12 and first <=12 -> interpret as MM-DD (legacy month-first).
    3. If both <=12 (ambiguous) -> interpret as DD-MM (day-first policy).
    4. Year omitted -> current year, roll forward one year if resulting date already past and input had no year.
    5. On malformed input fall back to legacy parse_date for validation consistency.
    """
    from date_utils import parse_date as _legacy_parse  # local import to avoid circulars
    raw = raw.strip()
    parts = raw.split('-')
    if len(parts) not in (2,3):
        return _legacy_parse(raw)
    try:
        a = int(parts[0])
        b = int(parts[1])
        year = int(parts[2]) if len(parts) == 3 else None
    except ValueError:
        return _legacy_parse(raw)
    if a > 12:
        use_day_first = True
    elif b > 12:
        use_day_first = False
    else:
        use_day_first = True  # ambiguous
    day, month = (a, b) if use_day_first else (b, a)
    from datetime import date as _date
    today = _date.today()
    if year is None:
        year = today.year
    try:
        d = _date(year, month, day)
    except ValueError:
        return _legacy_parse(raw)
    if len(parts) == 2 and d < today:
        # rollover year for short form in the past
        try:
            d = _date(year + 1, month, day)
        except ValueError:
            return _legacy_parse(raw)
    return d.strftime('%Y-%m-%d')


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
