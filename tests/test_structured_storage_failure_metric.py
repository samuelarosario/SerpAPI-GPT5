import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
import importlib

# Ensure config is resolvable (root already inserted)
importlib.invalidate_caches()
from core.metrics import METRICS  # type: ignore

from Main.enhanced_flight_search import EnhancedFlightSearchClient  # type: ignore

# We will monkeypatch the internal _store_structured_data to raise

def test_structured_storage_failure_increments_metric(monkeypatch):
    client = EnhancedFlightSearchClient(api_key='DUMMY')
    # Prime metrics
    METRICS.reset()

    def boom(*a, **k):
        raise RuntimeError('forced failure')

    monkeypatch.setattr(client, '_store_structured_data', boom)

    # Also monkeypatch API client to simulate minimal successful API return
    class DummyAPI:
        def _base(self, **kw):
            return {
                'success': True,
                'search_id': 'TEST123',
                'data': {
                    'best_flights': [],
                    'other_flights': []
                }
            }
        def search_round_trip(self, **kw):
            return self._base(**kw)
        def search_one_way(self, **kw):
            return self._base(**kw)
    client.api_client = DummyAPI()

    from datetime import datetime, timedelta
    future_date = (datetime.now() + timedelta(days=10)).strftime('%Y-%m-%d')
    # Force cache bypass (age 0) to exercise structured storage path
    result = client.search_flights('AAA','BBB', future_date, max_cache_age_hours=0)
    assert result['success'] is True
    snap = METRICS.snapshot()
    assert snap.get('structured_storage_failures', 0) == 1
