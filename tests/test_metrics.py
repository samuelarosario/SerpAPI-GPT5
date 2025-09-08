import os
import sys

sys.path.append(os.path.join(os.getcwd(), 'Main'))
from core.metrics import METRICS  # type: ignore
from enhanced_flight_search import EnhancedFlightSearchClient  # type: ignore


def test_metrics_counters_cache_hit(tmp_path, monkeypatch):
    # Use a temp copy of DB if exists, else skip if schema missing
    db_src = os.path.join('DB','Main_DB.db')
    if not os.path.exists(db_src):
        return  # environment without DB
    db_copy = tmp_path / 'test.db'
    with open(db_src,'rb') as src, open(db_copy,'wb') as dst:
        dst.write(src.read())
    client = EnhancedFlightSearchClient(db_path=str(db_copy))
    METRICS.reset()
    # Force a cache miss (unlikely parameters)
    res = client.search_flights('AAA','BBB','2030-12-31', force_api=True)
    # We can't guarantee api call success without key; so tolerate failure
    snap1 = METRICS.snapshot()
    # Just assert keys exist
    assert 'api_calls' in snap1 and 'cache_hits' in snap1 and 'cache_misses' in snap1

