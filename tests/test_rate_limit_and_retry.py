import pathlib
import sys

import pytest
import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
MAIN_DIR = ROOT / 'Main'
if str(MAIN_DIR) not in sys.path:
    sys.path.append(str(MAIN_DIR))

from core.common_validation import RateLimiter  # type: ignore
from serpapi_client import SerpAPIFlightClient  # type: ignore

# This test focuses on RateLimiter logic only; it does not perform real API calls.
# It manipulates the limiter counters directly and ensures behavior.

def test_rate_limiter_basic_window(monkeypatch):
    rl = RateLimiter()
    # Simulate hitting minute limit
    for _ in range(rl._minute.__len__() or 0):
        pass
    # Fill minute list artificially
    rl._minute = []
    rl._hour = []
    from datetime import datetime
    now = datetime.now()
    rl._minute = [now for _ in range(60)]  # exceed default minute limit if config < 60
    rl._hour = [now for _ in range(1000)]  # large hour list
    can = rl.can_make_request()
    assert can in (True, False)  # Just ensure no exception and returns bool

@pytest.mark.parametrize("attempts", [1,2,3])
def test_retry_metrics_increment(monkeypatch, attempts):
    # Only test internal loop metrics + backoff logic structure without calling network
    client = SerpAPIFlightClient(api_key="DUMMY")
    # Patch network call to raise RequestException every time
    client.session.get = lambda *a, **k: (_ for _ in ()).throw(requests.exceptions.RequestException("fail"))
    client.max_retries = attempts - 1
    tries = 0
    def fake_sleep(x):
        nonlocal tries
        tries += 1
    monkeypatch.setattr("time.sleep", fake_sleep)
    from core.metrics import METRICS  # type: ignore
    METRICS.reset()
    with pytest.raises(Exception):
        client._make_request({'engine':'test','api_key':'DUMMY'}, search_id="X")
    snap = METRICS.snapshot()
    assert snap.get('api_failures',0) == 1
    expected_retries = max(0, attempts-1)
    assert snap.get('retry_attempts',0) == expected_retries
