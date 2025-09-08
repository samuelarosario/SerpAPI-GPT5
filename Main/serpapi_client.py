"""
SerpAPI Google Flights Client
Handles API requests, authentication, and response management
"""

import requests
import json
import time
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from urllib.parse import urlencode
import hashlib
import random
from time import perf_counter
import os, sys, pathlib

# Ensure project and Main directories on path so `config` resolves when imported via tests
ROOT_DIR = pathlib.Path(__file__).resolve().parents[1]
MAIN_DIR = pathlib.Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))
if str(MAIN_DIR) not in sys.path:
    sys.path.append(str(MAIN_DIR))

from core.metrics import METRICS  # type: ignore
from core.structured_logging import log_event, log_exception  # type: ignore

from Main.config import (
    SERPAPI_CONFIG, DEFAULT_SEARCH_PARAMS, RATE_LIMIT_CONFIG, 
    get_api_key
)

from core.common_validation import RateLimiter, FlightSearchValidator  # type: ignore
from core.logging_setup import init_logging  # type: ignore
init_logging()

class SerpAPIFlightClient:
    """SerpAPI Google Flights API Client"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize the client (API key must come from environment variable)."""
        self.api_key = api_key or get_api_key()
        if not self.api_key:
            # Security: do NOT suggest plaintext file storage per agent instructions
            raise ValueError("SerpAPI key not found. Set SERPAPI_KEY environment variable (no plaintext storage).")
        
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
        """Search for flights using SerpAPI.

        Accepts all standard search params plus optional:
            enforce_horizon (bool): toggle horizon validation
            enforce_infant_rule (bool): toggle infant seating rule
        """
        enforce_horizon = kwargs.pop('enforce_horizon', True)
        enforce_infant_rule = kwargs.pop('enforce_infant_rule', True)
        # Build parameters
        params = self.build_search_params(**kwargs)
        
        # Validate parameters
        is_valid, errors = FlightSearchValidator.validate_search_params(
            params,
            enforce_horizon=enforce_horizon,
            enforce_infant_rule=enforce_infant_rule
        )
        if not is_valid:
            raise ValueError(f"Invalid search parameters: {'; '.join(errors)}")

        # Generate search ID (kept inside method scope)
        search_id = self.generate_search_id(params)
        log_event(
            'search.start',
            search_id=search_id,
            params_hash=hashlib.md5(json.dumps(params, sort_keys=True).encode()).hexdigest(),
            adults=params.get('adults'),
            route=f"{params.get('departure_id')}-{params.get('arrival_id')}"
        )
        
        # Check rate limits
        if self.rate_limiter and not self.rate_limiter.can_make_request():
            raise Exception("Rate limit exceeded. Please wait before making another request.")

        try:
            # Make API request
            response_data = self._make_request(params, search_id=search_id)
            
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
            log_event('search.success', search_id=search_id, flights_best=len(response_data.get('best_flights',[])) if isinstance(response_data, dict) else None)
            
        except Exception as e:
            # Handle API errors
            self.logger.error(f"Flight search failed: {str(e)}")
            log_exception('search.error', search_id=search_id, exc=e)
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
    
    def _make_request(self, params: Dict[str, Any], *, search_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Make HTTP request to SerpAPI with retries and jittered exponential backoff.

        Jitter rationale: Avoids synchronized retry storms when multiple processes
        encounter upstream rate limiting or transient failures simultaneously.
        """
        
        url = f"{self.base_url}?{urlencode(params)}"
        
        start_overall = perf_counter()
        for attempt in range(self.max_retries + 1):
            try:
                # Mask API key in logs
                safe_url = url.replace(self.api_key, '***') if self.api_key else url
                prefix = f"[{search_id}] " if search_id else ""
                self.logger.info(f"{prefix}API request attempt {attempt + 1} -> {safe_url}")
                log_event('api.attempt', search_id=search_id, attempt=attempt+1)
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                
                data = response.json()
                
                # Check for API errors
                if 'error' in data:
                    raise Exception(f"API Error: {data['error']}")
                
                self.logger.info("API request successful")
                log_event('api.success', search_id=search_id, attempt=attempt+1, status_code=response.status_code)
                METRICS.inc('api_calls')
                total_ms = int((perf_counter() - start_overall) * 1000)
                METRICS.inc('api_time_ms_total', total_ms)
                return data
                
            except requests.exceptions.RequestException as e:
                prefix = f"[{search_id}] " if search_id else ""
                self.logger.warning(f"{prefix}Request attempt {attempt + 1} failed: {e}")
                if attempt > 0:
                    METRICS.inc('retry_attempts')
                log_event('api.retry', search_id=search_id, attempt=attempt+1, error=str(e))
                
                if attempt < self.max_retries:
                    base_delay = self.retry_delay * (2 ** attempt)
                    jitter = random.uniform(0, 0.4)
                    time.sleep(base_delay + jitter)  # Exponential backoff + constant jitter component
                else:
                    self.logger.error(f"{prefix}All {self.max_retries + 1} attempts failed")
                    METRICS.inc('api_failures')
                    log_exception('api.failed', search_id=search_id, exc=e, attempts=self.max_retries+1)
                    raise Exception(f"API request failed after {self.max_retries + 1} attempts: {e}")
            
            except Exception as e:
                prefix = f"[{search_id}] " if search_id else ""
                self.logger.error(f"{prefix}Unexpected error: {e}")
                METRICS.inc('api_failures')
                log_exception('api.exception', search_id=search_id, exc=e)
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
