"""
SerpAPI Google Flights Client
Handles API requests, authentication, and response management
"""

import requests
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlencode
import hashlib

from config import (
    SERPAPI_CONFIG, DEFAULT_SEARCH_PARAMS, RATE_LIMIT_CONFIG, 
    VALIDATION_RULES, get_api_key
)

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
        """Validate airport code format"""
        if not code:
            return False
        return (len(code) == VALIDATION_RULES['airport_code_length'] and 
                code.isupper() and code.isalpha())
    
    @staticmethod
    def validate_date(date_str: str) -> bool:
        """Validate date format and range"""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            today = datetime.now().date()
            min_date = today + timedelta(days=VALIDATION_RULES['min_search_days_ahead'])
            max_date = today + timedelta(days=VALIDATION_RULES['max_search_days_ahead'])
            
            return min_date <= date_obj.date() <= max_date
        except ValueError:
            return False
    
    @staticmethod
    def validate_passengers(adults: int, children: int, infants_seat: int, infants_lap: int) -> bool:
        """Validate passenger counts"""
        total = adults + children + infants_seat + infants_lap
        return (adults >= 1 and 
                total <= VALIDATION_RULES['max_passengers'] and
                all(count >= 0 for count in [adults, children, infants_seat, infants_lap]))
    
    @staticmethod
    def validate_search_params(params: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate complete search parameters"""
        errors = []
        
        # Check required fields
        for field in VALIDATION_RULES['required_fields']:
            if field not in params or not params[field]:
                errors.append(f"Required field missing: {field}")
        
        # Validate airport codes
        if 'departure_id' in params:
            if not FlightSearchValidator.validate_airport_code(params['departure_id']):
                errors.append(f"Invalid departure airport code: {params['departure_id']}")
        
        if 'arrival_id' in params:
            if not FlightSearchValidator.validate_airport_code(params['arrival_id']):
                errors.append(f"Invalid arrival airport code: {params['arrival_id']}")
        
        # Validate dates
        if 'outbound_date' in params:
            if not FlightSearchValidator.validate_date(params['outbound_date']):
                errors.append(f"Invalid outbound date: {params['outbound_date']}")
        
        if 'return_date' in params:
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

class SerpAPIFlightClient:
    """SerpAPI Google Flights API Client"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the client"""
        self.api_key = api_key or get_api_key()
        if not self.api_key:
            raise ValueError("SerpAPI key not found. Set SERPAPI_KEY environment variable or place in ../Temp/api_key.txt")
        
        self.base_url = SERPAPI_CONFIG['base_url']
        self.engine = SERPAPI_CONFIG['engine']
        self.timeout = SERPAPI_CONFIG['timeout']
        self.max_retries = SERPAPI_CONFIG['max_retries']
        self.retry_delay = SERPAPI_CONFIG['retry_delay']
        
        self.rate_limiter = RateLimiter() if RATE_LIMIT_CONFIG['enable_rate_limiting'] else None
        self.session = requests.Session()
        
        # Setup logging
        self.logger = logging.getLogger(__name__)
    
    def generate_search_id(self, params: Dict[str, Any]) -> str:
        """Generate unique search ID based on parameters"""
        # Create a hash of the search parameters
        param_string = json.dumps(params, sort_keys=True)
        search_hash = hashlib.md5(param_string.encode()).hexdigest()[:12]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"search_{timestamp}_{search_hash}"
    
    def build_search_params(self, **kwargs) -> Dict[str, Any]:
        """Build complete search parameters with defaults"""
        params = DEFAULT_SEARCH_PARAMS.copy()
        params.update(kwargs)
        
        # Add required API parameters
        params['engine'] = self.engine
        params['api_key'] = self.api_key
        
        # Remove None values
        params = {k: v for k, v in params.items() if v is not None}
        
        return params
    
    def search_flights(self, **kwargs) -> Dict[str, Any]:
        """
        Search for flights using SerpAPI
        
        Args:
            departure_id: Departure airport code
            arrival_id: Arrival airport code
            outbound_date: Departure date (YYYY-MM-DD)
            return_date: Return date (YYYY-MM-DD) - optional for one-way
            **kwargs: Additional search parameters
        
        Returns:
            Dict containing search results and metadata
        """
        
        # Build parameters
        params = self.build_search_params(**kwargs)
        
        # Validate parameters
        is_valid, errors = FlightSearchValidator.validate_search_params(params)
        if not is_valid:
            raise ValueError(f"Invalid search parameters: {'; '.join(errors)}")
        
        # Generate search ID
        search_id = self.generate_search_id(params)
        
        # Check rate limits
        if self.rate_limiter and not self.rate_limiter.can_make_request():
            raise Exception("Rate limit exceeded. Please wait before making another request.")

        try:
            # Make API request
            response_data = self._make_request(params)
            
            # Record request if rate limiting is enabled
            if self.rate_limiter:
                self.rate_limiter.record_request()
            
            # Process response
            result = {
                'success': True,
                'search_id': search_id,
                'search_timestamp': datetime.now().isoformat(),
                'search_parameters': params,
                'data': response_data,
                'status': 'success',
                'error': None
            }
            
        except Exception as e:
            # Handle API errors
            self.logger.error(f"Flight search failed: {str(e)}")
            result = {
                'success': False,
                'search_id': search_id,
                'search_timestamp': datetime.now().isoformat(),
                'search_parameters': params,
                'data': None,
                'status': 'error',
                'error': str(e)
            }
        
        return result
    
    def _make_request(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Make HTTP request to SerpAPI with retries"""
        
        url = f"{self.base_url}?{urlencode(params)}"
        
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.info(f"Making API request (attempt {attempt + 1})")
                
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                
                data = response.json()
                
                # Check for API errors
                if 'error' in data:
                    raise Exception(f"API Error: {data['error']}")
                
                self.logger.info("API request successful")
                return data
                
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Request attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    self.logger.error(f"All {self.max_retries + 1} attempts failed")
                    raise Exception(f"API request failed after {self.max_retries + 1} attempts: {e}")
            
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                raise
        
        # This should never be reached due to the exception handling above
        return None

    def search_one_way(self, departure_id: str, arrival_id: str, 
                      outbound_date: str, **kwargs) -> Dict[str, Any]:
        """Search for one-way flights"""
        kwargs.update({
            'departure_id': departure_id,
            'arrival_id': arrival_id,
            'outbound_date': outbound_date,
            'type': 2  # One way
        })
        return self.search_flights(**kwargs)
    
    def search_round_trip(self, departure_id: str, arrival_id: str,
                         outbound_date: str, return_date: str, **kwargs) -> Dict[str, Any]:
        """Search for round-trip flights"""
        kwargs.update({
            'departure_id': departure_id,
            'arrival_id': arrival_id,
            'outbound_date': outbound_date,
            'return_date': return_date,
            'type': 1  # Round trip
        })
        return self.search_flights(**kwargs)
    
    def search_multi_city(self, multi_city_json: str, **kwargs) -> Dict[str, Any]:
        """Search for multi-city flights"""
        kwargs.update({
            'multi_city_json': multi_city_json,
            'type': 3  # Multi-city
        })
        return self.search_flights(**kwargs)

def test_client():
    """Test the SerpAPI client"""
    print("🧪 Testing SerpAPI Flight Client...")
    
    try:
        client = SerpAPIFlightClient()
        print("✅ Client initialized successfully")
        
        # Test parameter validation
        test_params = {
            'departure_id': 'LAX',
            'arrival_id': 'JFK',
            'outbound_date': '2025-09-15',
            'return_date': '2025-09-22'
        }
        
        is_valid, errors = FlightSearchValidator.validate_search_params(test_params)
        print(f"✅ Parameter validation: {'Valid' if is_valid else 'Invalid'}")
        
        if not is_valid:
            for error in errors:
                print(f"   - {error}")
        
        # Test search ID generation
        search_id = client.generate_search_id(test_params)
        print(f"✅ Search ID generated: {search_id}")
        
        print("🎉 Client test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Client test failed: {e}")
        return False

if __name__ == "__main__":
    test_client()
