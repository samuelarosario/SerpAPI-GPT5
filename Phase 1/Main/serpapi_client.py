"""Phase 1 copy - SerpAPI Google Flights Client (refactored to use common_validation)
"""
import requests
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from urllib.parse import urlencode
import hashlib

from config import (
    SERPAPI_CONFIG, DEFAULT_SEARCH_PARAMS, RATE_LIMIT_CONFIG, get_api_key
)
from common_validation import RateLimiter, FlightSearchValidator
from logging_setup import init_logging

init_logging()

class SerpAPIFlightClient:
    """SerpAPI Google Flights API Client (Phase 1)"""
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_api_key()
        self.base_url = SERPAPI_CONFIG['base_url']
        self.engine = SERPAPI_CONFIG['engine']
        self.timeout = SERPAPI_CONFIG['timeout']
        self.max_retries = SERPAPI_CONFIG['max_retries']
        self.retry_delay = SERPAPI_CONFIG['retry_delay']
        self.rate_limiter = RateLimiter() if RATE_LIMIT_CONFIG['enable_rate_limiting'] else None
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)

    def generate_search_id(self, params: Dict[str, Any]) -> str:
        param_string = json.dumps(params, sort_keys=True)
        search_hash = hashlib.md5(param_string.encode()).hexdigest()[:12]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"search_{timestamp}_{search_hash}"

    def build_search_params(self, **kwargs) -> Dict[str, Any]:
        params = DEFAULT_SEARCH_PARAMS.copy()
        params.update(kwargs)
        params['engine'] = self.engine
        params['api_key'] = self.api_key
        return {k: v for k, v in params.items() if v is not None}

    def search_flights(self, **kwargs) -> Dict[str, Any]:
        params = self.build_search_params(**kwargs)
        is_valid, errors = FlightSearchValidator.validate_search_params(params)
        if not is_valid:
            return {
                'success': False,
                'error': '; '.join(errors),
                'search_parameters': params,
                'status': 'validation_error'
            }
        search_id = self.generate_search_id(params)
        if self.rate_limiter and not self.rate_limiter.can_make_request():
            return {
                'success': False,
                'error': 'Rate limit exceeded',
                'search_id': search_id,
                'search_parameters': params,
                'status': 'rate_limited'
            }
        try:
            data = self._make_request(params)
            if self.rate_limiter:
                self.rate_limiter.record_request()
            return {
                'success': True,
                'search_id': search_id,
                'search_timestamp': datetime.now().isoformat(),
                'search_parameters': params,
                'data': data,
                'status': 'success',
                'error': None
            }
        except Exception as e:
            self.logger.error(f"Flight search failed: {e}")
            return {
                'success': False,
                'search_id': search_id,
                'search_timestamp': datetime.now().isoformat(),
                'search_parameters': params,
                'data': None,
                'status': 'error',
                'error': str(e)
            }

    def _make_request(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}?{urlencode(params)}"
        for attempt in range(self.max_retries + 1):
            try:
                self.logger.info(f"API request attempt {attempt+1}")
                resp = self.session.get(url, timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                if 'error' in data:
                    raise Exception(data['error'])
                return data
            except requests.exceptions.RequestException as e:
                self.logger.warning(f"Attempt {attempt+1} failed: {e}")
                if attempt < self.max_retries:
                    time.sleep(self.retry_delay * (2 ** attempt))
                else:
                    raise
        return None

    def search_one_way(self, departure_id: str, arrival_id: str, outbound_date: str, **kwargs):
        kwargs.update({'departure_id': departure_id, 'arrival_id': arrival_id, 'outbound_date': outbound_date, 'type': 2})
        return self.search_flights(**kwargs)

    def search_round_trip(self, departure_id: str, arrival_id: str, outbound_date: str, return_date: str, **kwargs):
        kwargs.update({'departure_id': departure_id, 'arrival_id': arrival_id, 'outbound_date': outbound_date, 'return_date': return_date, 'type': 1})
        return self.search_flights(**kwargs)

if __name__ == '__main__':
    print('Phase 1 client smoke test:')
    try:
        client = SerpAPIFlightClient()
        test = client.search_flights(departure_id='LAX', arrival_id='JFK', outbound_date='2099-01-15')
        print('Result status:', test['status'])
    except Exception as e:
        print('Initialization / test failed (expected if no key):', e)
