"""
Enhanced Flight Search Client with Local Database Cache
Searches local DB first, then uses API if data not found
"""

import requests
import json
import time
import logging
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Union
from urllib.parse import urlencode
import os
import sys

# Add DB directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'DB'))

from config import (
    SERPAPI_CONFIG, DEFAULT_SEARCH_PARAMS, RATE_LIMIT_CONFIG, 
    VALIDATION_RULES, get_api_key
)

try:
    from database_helper import SerpAPIDatabase
except ImportError:
    # Fallback if import fails
    class SerpAPIDatabase:
        def __init__(self, db_path):
            self.db_path = db_path
        def insert_api_response(self, **kwargs):
            return 1

class FlightSearchCache:
    """Manages local database cache for flight searches"""
    
    def __init__(self, db_path: str = "DB/Main_DB.db"):
        """Initialize cache manager"""
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def generate_cache_key(self, search_params: Dict[str, Any]) -> str:
        """Generate consistent cache key from search parameters"""
        # Normalize parameters for consistent hashing
        normalized_params = {}
        for key, value in search_params.items():
            if value is not None:
                normalized_params[key] = str(value).lower() if isinstance(value, str) else value
        
        # Create hash from sorted parameters
        param_string = json.dumps(normalized_params, sort_keys=True)
        return hashlib.sha256(param_string.encode()).hexdigest()
    
    def search_cache(self, search_params: Dict[str, Any], max_age_hours: int = 24) -> Optional[Dict[str, Any]]:
        """
        Search for cached flight data in local database
        
        Args:
            search_params: Flight search parameters
            max_age_hours: Maximum age of cached data in hours (default 24)
            
        Returns:
            Cached search result if found and valid, None otherwise
        """
        try:
            cache_key = self.generate_cache_key(search_params)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Search for recent cached results - simplified lookup
                cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
                
                query = """
                SELECT fs.*, COUNT(fr.id) as flight_count
                FROM flight_searches fs
                LEFT JOIN flight_results fr ON fs.search_id = fr.search_id
                WHERE fs.cache_key = ? 
                AND fs.created_at > ?
                GROUP BY fs.search_id
                ORDER BY fs.created_at DESC
                LIMIT 1
                """
                
                cursor.execute(query, (cache_key, cutoff_time.isoformat()))
                result = cursor.fetchone()
                
                if result:
                    self.logger.info(f"Cache HIT for search key: {cache_key[:12]}...")
                    
                    # Get flight results and reconstruct API-compatible format
                    cursor.execute("""
                        SELECT fr.id, fr.total_price, fr.price_currency, fr.total_duration, 
                               fr.layover_count, fr.result_type, fr.carbon_emissions_flight,
                               fr.booking_token
                        FROM flight_results fr
                        WHERE fr.search_id = ?
                        ORDER BY fr.total_price ASC
                    """, (result['search_id'],))
                    
                    flight_results = cursor.fetchall()
                    
                    # Reconstruct API-compatible response format
                    best_flights = []
                    other_flights = []
                    
                    for flight_row in flight_results:
                        flight_id, price, currency, duration, layovers, result_type, carbon, booking_token = flight_row
                        
                        # Get flight segments for this flight
                        cursor.execute("""
                            SELECT departure_airport_code, arrival_airport_code, 
                                   airline_code, flight_number, departure_time, 
                                   arrival_time, duration_minutes
                            FROM flight_segments 
                            WHERE flight_result_id = ?
                            ORDER BY segment_order
                        """, (flight_id,))
                        
                        segments = cursor.fetchall()
                        
                        # Build flight object in API format
                        flight_obj = {
                            'price': f'{price} {currency}' if price and currency else None,
                            'total_duration': duration,
                            'layovers': [] if layovers == 0 else [{'duration': 'N/A'} for _ in range(layovers)],
                            'carbon_emissions': {'this_flight': carbon} if carbon else {},
                            'booking_token': booking_token,
                            'flights': []
                        }
                        
                        # Add flight segments
                        for seg in segments:
                            dep_code, arr_code, airline, flight_num, dep_time, arr_time, seg_duration = seg
                            segment_obj = {
                                'departure_airport': {'id': dep_code},
                                'arrival_airport': {'id': arr_code},
                                'airline': airline,
                                'flight_number': flight_num,
                                'departure_time': dep_time,
                                'arrival_time': arr_time,
                                'duration': seg_duration
                            }
                            flight_obj['flights'].append(segment_obj)
                        
                        # Categorize as best or other flight
                        if result_type == 'best':
                            best_flights.append(flight_obj)
                        else:
                            other_flights.append(flight_obj)
                    
                    # Format response in API-compatible structure
                    cached_response = {
                        'search_id': result['search_id'],
                        'search_parameters': json.loads(result['raw_parameters']) if result['raw_parameters'] else {},
                        'cached': True,
                        'cache_timestamp': result['created_at'],
                        'flight_results_count': result['flight_count'],
                        'processing_status': 'cached_data',
                        'best_flights': best_flights,
                        'other_flights': other_flights
                    }
                    
                    return cached_response
                else:
                    self.logger.info(f"Cache MISS for search key: {cache_key[:12]}...")
                    return None
                    
        except Exception as e:
            self.logger.error(f"Error searching cache: {str(e)}")
            return None
    
    def store_flight_data(self, search_id: str, search_params: Dict[str, Any], api_response: Dict[str, Any]) -> None:
        """Store complete flight search data in the database"""
        try:
            cache_key = self.generate_cache_key(search_params)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Insert flight search record
                cursor.execute("""
                INSERT OR REPLACE INTO flight_searches (
                    search_id, search_timestamp, departure_airport_code, arrival_airport_code, 
                    outbound_date, return_date, flight_type, adults, children,
                    infants_in_seat, infants_on_lap, travel_class, currency,
                    country_code, language_code, raw_parameters, response_status,
                    total_results, cache_key, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    search_id,
                    datetime.now().isoformat(),
                    search_params.get('departure_id'),
                    search_params.get('arrival_id'),
                    search_params.get('outbound_date'),
                    search_params.get('return_date'),
                    1 if search_params.get('return_date') else 2,  # 1=round-trip, 2=one-way
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
                    datetime.now().isoformat()
                ))
                
                # Store flight results
                flight_result_id = cursor.lastrowid
                
                # Process best flights
                best_flights = api_response.get('best_flights', [])
                for rank, flight in enumerate(best_flights, 1):
                    self._store_flight_result(cursor, search_id, flight, 'best', rank)
                
                # Process other flights
                other_flights = api_response.get('other_flights', [])
                for rank, flight in enumerate(other_flights, 1):
                    self._store_flight_result(cursor, search_id, flight, 'other', rank)
                
                # Store price insights
                if 'price_insights' in api_response:
                    self._store_price_insights(cursor, search_id, api_response['price_insights'])
                
                conn.commit()
                self.logger.info(f"Successfully stored flight data for search: {search_id}")
                
        except Exception as e:
            self.logger.error(f"Error storing flight data: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def _store_flight_result(self, cursor, search_id: str, flight: Dict[str, Any], result_type: str, rank: int):
        """Store individual flight result"""
        try:
            cursor.execute("""
            INSERT INTO flight_results (
                search_id, result_type, result_rank, total_duration, total_price,
                price_currency, flight_type, layover_count, carbon_emissions_flight,
                carbon_emissions_typical, carbon_emissions_difference_percent,
                booking_token, airline_logo_url, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                search_id, result_type, rank,
                flight.get('total_duration'),
                flight.get('price'),
                'USD',  # Default currency
                flight.get('type', 'One way'),
                len(flight.get('layovers', [])),
                flight.get('carbon_emissions', {}).get('this_flight'),
                flight.get('carbon_emissions', {}).get('typical_for_this_route'),
                flight.get('carbon_emissions', {}).get('difference_percent'),
                flight.get('booking_token'),
                flight.get('airline_logo'),
                datetime.now().isoformat()
            ))
            
            flight_result_id = cursor.lastrowid
            
            # Store flight segments
            for segment_order, segment in enumerate(flight.get('flights', []), 1):
                self._store_flight_segment(cursor, flight_result_id, segment, segment_order)
            
            # Store layovers
            for layover_order, layover in enumerate(flight.get('layovers', []), 1):
                self._store_layover(cursor, flight_result_id, layover, layover_order)
                
        except Exception as e:
            self.logger.error(f"Error storing flight result: {str(e)}")
    
    def _store_flight_segment(self, cursor, flight_result_id: int, segment: Dict[str, Any], segment_order: int):
        """Store flight segment details with optimized schema (no redundant data)"""
        try:
            departure_airport = segment.get('departure_airport', {})
            arrival_airport = segment.get('arrival_airport', {})
            
            # Store airport information in normalized tables
            self._store_airport_info(cursor, departure_airport)
            self._store_airport_info(cursor, arrival_airport)
            
            # Extract IATA airline code from flight number instead of using full name
            flight_number = segment.get('flight_number', '')
            airline_iata_code = self._extract_airline_iata_code(flight_number, segment.get('airline', ''))
            
            # Store airline information in normalized table
            self._store_airline_info(cursor, airline_iata_code, segment.get('airline_logo'), segment.get('airline'))
            
            # Insert flight segment with ONLY airport codes and airline IATA code (no redundant names)
            cursor.execute("""
            INSERT INTO flight_segments (
                flight_result_id, segment_order, departure_airport_code, departure_time,
                arrival_airport_code, arrival_time, duration_minutes, airplane_model,
                airline_code, flight_number, travel_class, legroom,
                often_delayed, extensions, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                flight_result_id, segment_order,
                departure_airport.get('id'),      # Only store airport CODE
                departure_airport.get('time'),
                arrival_airport.get('id'),        # Only store airport CODE
                arrival_airport.get('time'),
                segment.get('duration'),
                segment.get('airplane'),
                airline_iata_code,                # Store proper IATA airline code
                segment.get('flight_number'),
                segment.get('travel_class'),
                segment.get('legroom'),
                segment.get('often_delayed_by_over_30_min', False),
                json.dumps(segment.get('extensions', [])),
                datetime.now().isoformat()
            ))
        except Exception as e:
            self.logger.error(f"Error storing flight segment: {str(e)}")
    
    def _extract_airline_iata_code(self, flight_number: str, airline_name: str) -> str:
        """Extract IATA airline code from flight number or airline name"""
        if not flight_number:
            return airline_name
        
        # Flight numbers typically start with 2-3 letter IATA code
        import re
        match = re.match(r'^([A-Z]{2,3})\s*\d+', flight_number.strip())
        if match:
            return match.group(1)
        
        # Fallback: use airline name if no IATA code found
        return airline_name
    
    def _store_layover(self, cursor, flight_result_id: int, layover: Dict[str, Any], layover_order: int):
        """Store layover information with optimized schema (no redundant airport name)"""
        try:
            cursor.execute("""
            INSERT INTO layovers (
                flight_result_id, layover_order, airport_code,
                duration_minutes, is_overnight, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                flight_result_id, layover_order,
                layover.get('id'),        # Only store airport CODE (no redundant name)
                layover.get('duration'),
                layover.get('overnight', False),
                datetime.now().isoformat()
            ))
        except Exception as e:
            self.logger.error(f"Error storing layover: {str(e)}")
    
    def _store_price_insights(self, cursor, search_id: str, price_insights: Dict[str, Any]):
        """Store price insights data"""
        try:
            cursor.execute("""
            INSERT INTO price_insights (
                search_id, lowest_price, price_level, typical_price_low,
                typical_price_high, price_history, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                search_id,
                price_insights.get('lowest_price'),
                price_insights.get('price_level'),
                price_insights.get('typical_price_range', [None, None])[0],
                price_insights.get('typical_price_range', [None, None])[1],
                json.dumps(price_insights.get('price_history', [])),
                datetime.now().isoformat()
            ))
        except Exception as e:
            self.logger.error(f"Error storing price insights: {str(e)}")
    
    def _store_airport_info(self, cursor, airport_data: Dict[str, Any]):
        """Store or update airport information in normalized airports table"""
        if not airport_data or not airport_data.get('id'):
            return
            
        try:
            airport_code = airport_data.get('id')
            airport_name = airport_data.get('name')
            
            # Use INSERT OR IGNORE to add new airports, then UPDATE existing ones
            current_time = datetime.now().isoformat()
            
            # First, try to insert new airport (will be ignored if code already exists)
            cursor.execute("""
            INSERT OR IGNORE INTO airports (
                airport_code, airport_name, city, country, country_code,
                timezone, image_url, thumbnail_url, first_seen, last_seen
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                airport_code,
                airport_name,
                airport_data.get('city'),
                airport_data.get('country'),
                airport_data.get('country_code'),
                airport_data.get('timezone'),
                airport_data.get('image'),
                airport_data.get('thumbnail'),
                current_time,
                current_time
            ))
            
            # Then update the existing record (always update last_seen and fill in missing data)
            cursor.execute("""
            UPDATE airports SET 
                airport_name = COALESCE(?, airport_name),
                city = COALESCE(?, city),
                country = COALESCE(?, country),
                country_code = COALESCE(?, country_code),
                timezone = COALESCE(?, timezone),
                image_url = COALESCE(?, image_url),
                thumbnail_url = COALESCE(?, thumbnail_url),
                last_seen = ?
            WHERE airport_code = ?
            """, (
                airport_name,
                airport_data.get('city'),
                airport_data.get('country'),
                airport_data.get('country_code'),
                airport_data.get('timezone'),
                airport_data.get('image'),
                airport_data.get('thumbnail'),
                current_time,
                airport_code
            ))
                
        except Exception as e:
            self.logger.error(f"Error storing airport info: {str(e)}")
    
    def _store_airline_info(self, cursor, airline_iata_code: str, airline_logo: str = None, airline_name: str = None):
        """Store or update airline information in normalized airlines table"""
        if not airline_iata_code:
            return
            
        try:
            # Use INSERT OR IGNORE to add new airlines, then UPDATE existing ones
            current_time = datetime.now().isoformat()
            
            # Determine airline name - prefer provided name, fallback to IATA code
            display_name = airline_name if airline_name else airline_iata_code
            
            # First, try to insert new airline (will be ignored if code already exists)
            cursor.execute("""
            INSERT OR IGNORE INTO airlines (
                airline_code, airline_name, logo_url, alliance,
                first_seen, last_seen
            ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                airline_iata_code,
                display_name,
                airline_logo,
                None,           # Alliance info not available in current data
                current_time,
                current_time
            ))
            
            # Then update the existing record (always update last_seen and improve data if available)
            cursor.execute("""
            UPDATE airlines SET 
                airline_name = CASE 
                    WHEN ? != ? THEN ?  -- Update name if we have a better one (not just IATA code)
                    ELSE airline_name 
                END,
                logo_url = COALESCE(?, logo_url),
                last_seen = ?
            WHERE airline_code = ?
            """, (
                display_name, airline_iata_code, display_name,  # Update name if it's not just the IATA code
                airline_logo,
                current_time,
                airline_iata_code
            ))
                
        except Exception as e:
            self.logger.error(f"Error storing airline info: {str(e)}")
    
    def cleanup_old_data(self, max_age_hours: int = 24):
        """Remove flight data older than specified hours to keep database fresh"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
                
                # Get search IDs that are too old
                cursor.execute("""
                SELECT search_id FROM flight_searches 
                WHERE created_at < ?
                """, (cutoff_time.isoformat(),))
                
                old_search_ids = [row[0] for row in cursor.fetchall()]
                
                if old_search_ids:
                    self.logger.info(f"Cleaning up {len(old_search_ids)} old flight searches")
                    
                    # Delete related data in correct order (due to foreign key constraints)
                    for search_id in old_search_ids:
                        # Delete layovers first
                        cursor.execute("""
                        DELETE FROM layovers 
                        WHERE flight_result_id IN (
                            SELECT id FROM flight_results WHERE search_id = ?
                        )
                        """, (search_id,))
                        
                        # Delete flight segments
                        cursor.execute("""
                        DELETE FROM flight_segments 
                        WHERE flight_result_id IN (
                            SELECT id FROM flight_results WHERE search_id = ?
                        )
                        """, (search_id,))
                        
                        # Delete flight results
                        cursor.execute("DELETE FROM flight_results WHERE search_id = ?", (search_id,))
                        
                        # Delete price insights
                        cursor.execute("DELETE FROM price_insights WHERE search_id = ?", (search_id,))
                        
                        # Delete flight search
                        cursor.execute("DELETE FROM flight_searches WHERE search_id = ?", (search_id,))
                    
                    # Clean up old API queries too
                    cursor.execute("DELETE FROM api_queries WHERE created_at < ?", (cutoff_time.isoformat(),))
                    
                    conn.commit()
                    self.logger.info(f"Cleaned up {len(old_search_ids)} old searches and related data")
                    
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")

    def store_cache_key(self, search_id: str, search_params: Dict[str, Any]) -> None:
        """Store cache key for a search in the database (legacy method)"""
        # This method is kept for compatibility but store_flight_data should be used instead
        pass

class RateLimiter:
    """Simple rate limiter for API requests"""
    
    def __init__(self):
        self.requests_minute = []
        self.requests_hour = []
    
    def can_make_request(self) -> bool:
        """Check if we can make a request within rate limits"""
        now = datetime.now()
        
        # Clean old requests
        self.requests_minute = [req_time for req_time in self.requests_minute 
                              if now - req_time < timedelta(minutes=1)]
        self.requests_hour = [req_time for req_time in self.requests_hour 
                            if now - req_time < timedelta(hours=1)]
        
        # Check limits
        minute_limit = RATE_LIMIT_CONFIG['requests_per_minute']
        hour_limit = RATE_LIMIT_CONFIG['requests_per_hour']
        
        return (len(self.requests_minute) < minute_limit and 
                len(self.requests_hour) < hour_limit)
    
    def record_request(self):
        """Record a new request"""
        now = datetime.now()
        self.requests_minute.append(now)
        self.requests_hour.append(now)

class FlightSearchValidator:
    """Validates flight search parameters"""
    
    @staticmethod
    def validate_airport_code(code: str) -> bool:
        """Validate IATA airport code format"""
        if not code or len(code) != 3:
            return False
        return code.isalpha() and code.isupper()
    
    @staticmethod
    def validate_date(date_str: str) -> bool:
        """Validate date format (YYYY-MM-DD)"""
        try:
            datetime.strptime(date_str, '%Y-%m-%d')
            return True
        except ValueError:
            return False
    
    @staticmethod
    def validate_passengers(adults: int, children: int = 0, infants_seat: int = 0, infants_lap: int = 0) -> bool:
        """Validate passenger counts"""
        total_passengers = adults + children + infants_seat + infants_lap
        return adults >= 1 and total_passengers <= 9 and infants_lap <= adults

class EnhancedFlightSearchClient:
    """Enhanced Flight Search Client with Local Database Cache"""
    
    def __init__(self, api_key: Optional[str] = None, db_path: str = "DB/Main_DB.db"):
        """Initialize the enhanced client"""
        self.api_key = api_key or get_api_key()
        self.db_path = db_path
        
        # Initialize cache manager
        self.cache = FlightSearchCache(db_path)
        
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
        self.api_client = SerpAPIFlightClient(api_key) if self.api_key else None
    
    def search_flights(self, 
                      departure_id: str,
                      arrival_id: str,
                      outbound_date: str,
                      return_date: Optional[str] = None,
                      adults: int = 1,
                      children: int = 0,
                      infants_in_seat: int = 0,
                      infants_on_lap: int = 0,
                      travel_class: int = 1,
                      currency: str = "USD",
                      max_cache_age_hours: int = 24,
                      force_api: bool = False,
                      **kwargs) -> Dict[str, Any]:
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
        
        # Clean up old data first to maintain fresh 24-hour window
        self.cache.cleanup_old_data(max_cache_age_hours)
        
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
        
        # Step 1: Check local cache first (unless forced to use API)
        if not force_api:
            self.logger.info("Checking local database cache...")
            cached_result = self.cache.search_cache(search_params, max_cache_age_hours)
            
            if cached_result:
                self.logger.info(f"Using cached data from {cached_result['cache_timestamp']}")
                return {
                    'success': True,
                    'source': 'cache',
                    'data': cached_result,
                    'cache_age_hours': self._calculate_cache_age(cached_result['cache_timestamp']),
                    'message': 'Data retrieved from local cache'
                }
        
        # Step 2: No cache found or forced API - use API
        self.logger.info("Cache miss or forced API - making API request...")
        
        if not self.api_client:
            return {
                'success': False,
                'error': 'No API key available and no cached data found',
                'source': 'api_error'
            }
        
        try:
            # Always use round-trip search to capture more comprehensive data
            # This provides both outbound and return flight options
            if 'return_date' in search_params:
                self.logger.info("Making round-trip API call (return date provided)")
                api_result = self.api_client.search_round_trip(**search_params)
            else:
                self.logger.info("Making one-way API call (no return date available)")
                api_result = self.api_client.search_one_way(**search_params)
            
            if api_result.get('success'):
                # Store complete flight data in database
                search_id = api_result.get('search_id')
                api_data = api_result.get('data')
                
                if search_id and api_data:
                    self.cache.store_flight_data(search_id, search_params, api_data)
                    self.logger.info(f"API call successful - stored complete flight data for search: {search_id}")
                
                return {
                    'success': True,
                    'source': 'api',
                    'data': api_data,
                    'search_id': search_id,
                    'message': 'Fresh data retrieved from API'
                }
            else:
                return {
                    'success': False,
                    'error': api_result.get('error', 'API call failed'),
                    'source': 'api_error'
                }
                
        except Exception as e:
            self.logger.error(f"API call failed: {str(e)}")
            return {
                'success': False,
                'error': f'API call failed: {str(e)}',
                'source': 'api_exception'
            }
    
    def _validate_search_params(self, params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate search parameters"""
        errors = []
        
        # Validate airport codes
        if not FlightSearchValidator.validate_airport_code(params.get('departure_id', '')):
            errors.append(f"Invalid departure airport code: {params.get('departure_id')}")
        
        if not FlightSearchValidator.validate_airport_code(params.get('arrival_id', '')):
            errors.append(f"Invalid arrival airport code: {params.get('arrival_id')}")
        
        # Validate dates
        if 'outbound_date' in params:
            if not FlightSearchValidator.validate_date(params['outbound_date']):
                errors.append(f"Invalid outbound date: {params['outbound_date']}")
        
        if 'return_date' in params and params['return_date']:
            if not FlightSearchValidator.validate_date(params['return_date']):
                errors.append(f"Invalid return date: {params['return_date']}")
        
        # Validate passengers
        adults = params.get('adults', 1)
        children = params.get('children', 0)
        infants_seat = params.get('infants_in_seat', 0)
        infants_lap = params.get('infants_on_lap', 0)
        
        if not FlightSearchValidator.validate_passengers(adults, children, infants_seat, infants_lap):
            errors.append("Invalid passenger configuration")
        
        return len(errors) == 0, errors
    
    def _calculate_cache_age(self, cache_timestamp: str) -> float:
        """Calculate age of cached data in hours"""
        try:
            cache_time = datetime.fromisoformat(cache_timestamp.replace('Z', '+00:00'))
            now = datetime.now()
            if cache_time.tzinfo:
                # Make now timezone aware if cache_time is
                from datetime import timezone
                now = now.replace(tzinfo=timezone.utc)
            
            age_delta = now - cache_time
            return age_delta.total_seconds() / 3600
        except Exception:
            return 0.0
    
    def clear_cache(self, older_than_hours: int = 168) -> Dict[str, Any]:
        """
        Clear cached flight data older than specified hours
        
        Args:
            older_than_hours: Clear cache older than this many hours (default 7 days)
            
        Returns:
            Dict with cleanup results
        """
        try:
            cutoff_time = datetime.now() - timedelta(hours=older_than_hours)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Count records to be deleted
                cursor.execute("""
                SELECT COUNT(*) FROM api_queries 
                WHERE query_timestamp < ?
                """, (cutoff_time.isoformat(),))
                
                count_to_delete = cursor.fetchone()[0]
                
                # Delete old records (cascading will handle related tables)
                cursor.execute("""
                DELETE FROM api_queries 
                WHERE query_timestamp < ?
                """, (cutoff_time.isoformat(),))
                
                conn.commit()
                
                self.logger.info(f"Cleared {count_to_delete} cached records older than {older_than_hours} hours")
                
                return {
                    'success': True,
                    'deleted_count': count_to_delete,
                    'cutoff_time': cutoff_time.isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Error clearing cache: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about cached flight data"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Total cached searches
                cursor.execute("SELECT COUNT(*) FROM flight_searches")
                total_searches = cursor.fetchone()[0]
                
                # Searches in last 24 hours
                yesterday = datetime.now() - timedelta(hours=24)
                cursor.execute("""
                SELECT COUNT(*) FROM api_queries 
                WHERE query_timestamp > ?
                """, (yesterday.isoformat(),))
                recent_searches = cursor.fetchone()[0]
                
                # Popular routes
                cursor.execute("""
                SELECT departure_id, arrival_id, COUNT(*) as search_count
                FROM flight_searches
                GROUP BY departure_id, arrival_id
                ORDER BY search_count DESC
                LIMIT 5
                """)
                popular_routes = cursor.fetchall()
                
                return {
                    'total_cached_searches': total_searches,
                    'recent_searches_24h': recent_searches,
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

# Example usage and testing
if __name__ == "__main__":
    # Test the enhanced client
    client = EnhancedFlightSearchClient()
    
    # Test search (will check cache first)
    result = client.search_flights(
        departure_id="LAX",
        arrival_id="JFK", 
        outbound_date="2025-09-15",
        return_date="2025-09-22",
        adults=2
    )
    
    print("Search Result:")
    print(f"Success: {result['success']}")
    print(f"Source: {result['source']}")
    if result['success']:
        print(f"Message: {result['message']}")
    else:
        print(f"Error: {result['error']}")
    
    # Get cache statistics
    stats = client.get_cache_stats()
    print(f"\nCache Statistics: {stats}")
