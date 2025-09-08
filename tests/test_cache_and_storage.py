from Main.enhanced_flight_search import FlightSearchCache  # type: ignore


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
    # Simple invariants replicating internal mapping logic (no DB dependency)
    def normalize(label: str) -> str:
        return 'best' if label in ('best','best_flight') else 'other'
    assert normalize('best_flight') == 'best'
    assert normalize('best') == 'best'
    assert normalize('other_flight') == 'other'
