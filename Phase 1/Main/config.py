# Phase 1 copy of config (lightweight reference)
from pathlib import Path
import os
import sys
from dotenv import load_dotenv

# Ensure project root two levels up for loading .env relative if needed
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / '.env')

SERPAPI_CONFIG = {
    'base_url': 'https://serpapi.com/search',
    'engine': 'google_flights',
    'timeout': 30,
    'max_retries': 3,
    'retry_delay': 1.0,
}

DEFAULT_SEARCH_PARAMS = {
    'currency': 'USD', 'hl': 'en', 'gl': 'us',
    'adults': 1, 'children': 0, 'infants_in_seat': 0, 'infants_on_lap': 0,
    'travel_class': 1, 'type': 1,
    'deep_search': False, 'show_hidden': False,
}

RATE_LIMIT_CONFIG = {
    'requests_per_minute': 60,
    'requests_per_hour': 1000,
    'enable_rate_limiting': True,
}

VALIDATION_RULES = {
    'airport_code_length': 3,
    'max_search_days_ahead': 365,
    'min_search_days_ahead': 1,
    'max_passengers': 9,
    'required_fields': ['departure_id', 'arrival_id', 'outbound_date'],
}

def get_api_key():
    key = os.getenv('SERPAPI_KEY')
    if not key:
        raise ValueError('SERPAPI_KEY missing for Phase 1 sandbox')
    return key
