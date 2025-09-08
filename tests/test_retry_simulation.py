import os, sys
import pytest
sys.path.append(os.path.join(os.getcwd(), 'Main'))
from serpapi_client import SerpAPIFlightClient  # type: ignore

class DummyResp:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {"best_flights": [], "other_flights": []}
    def raise_for_status(self):
        if self.status_code >= 400:
            from requests import HTTPError
            raise HTTPError(f"{self.status_code} error")
    def json(self):
        return self._payload

def test_retry_path(monkeypatch):
    monkeypatch.setenv('SERPAPI_KEY','DUMMY')
    client = SerpAPIFlightClient()
    attempts = {'count':0}
    def fake_get(url, timeout):
        attempts['count'] += 1
        if attempts['count'] < 3:
            from requests import RequestException
            raise RequestException('temp network glitch')
        return DummyResp(200)
    monkeypatch.setattr(client.session,'get', fake_get)
    result = client.search_flights(departure_id='AAA', arrival_id='BBB', outbound_date='2030-12-31', enforce_horizon=False)
    assert result['success'] is True
    assert attempts['count'] == 3