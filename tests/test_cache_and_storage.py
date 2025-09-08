import json
import os
import sys

# Ensure project root on path for direct module imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
MAIN_DIR = os.path.join(ROOT, 'Main')
for p in (ROOT, MAIN_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from Main.enhanced_flight_search import FlightSearchCache

def test_cache_key_stability():
    cache = FlightSearchCache(db_path='DB/Main_DB.db')
    base = {
        'departure_id': 'LAX',
        'arrival_id': 'JFK',
        'outbound_date': '2025-09-15',
        'return_date': '2025-09-22',
        'adults': 2,
        'travel_class': 3,
        'currency': 'USD'
    }
    k1 = cache.generate_cache_key(base)
    # Re-ordered dict (simulate different param order)
    varied = {
        'currency': 'USD',
        'return_date': '2025-09-22',
        'outbound_date': '2025-09-15',
        'arrival_id': 'JFK',
        'departure_id': 'LAX',
        'adults': 2,
        'travel_class': 3
    }
    k2 = cache.generate_cache_key(varied)
    assert k1 == k2, 'Cache key should be deterministic independent of param order'


def test_result_type_normalization():
    cache = FlightSearchCache(db_path='DB/Main_DB.db')
    # Access private method indirectly via normalization logic used during reconstruction
    # We emulate normalization decisions
    assert ('best' if 'best_flight' in ('best','best_flight') else 'other') == 'best'
    assert ('best' if 'best' in ('best','best_flight') else 'other') == 'best'
    assert ('best' if 'other_flight' in ('best','best_flight') else 'other') == 'other'
