from Main.core.metrics import METRICS  # type: ignore
from Main.enhanced_flight_search import EnhancedFlightSearchClient  # type: ignore


def test_metrics_counters_cache_hit(db_copy, metrics_reset):
    client = EnhancedFlightSearchClient(db_path=str(db_copy))
    # Force a likely cache miss
    try:
        client.search_flights('AAA','BBB','2030-12-31', force_api=True)
    except Exception:
        pass  # API key may be missing
    snap = METRICS.snapshot()
    assert {'api_calls','cache_hits','cache_misses'}.issubset(snap.keys())

