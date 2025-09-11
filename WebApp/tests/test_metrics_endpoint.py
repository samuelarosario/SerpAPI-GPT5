import os
os.environ["WEBAPP_TESTING"] = "1"

from fastapi.testclient import TestClient
from WebApp.app.main import app


def test_metrics_enabled():
    # default is enabled via settings
    client = TestClient(app)
    r = client.get("/metrics")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, dict)
    # expected core counters exist
    assert "api_calls" in data
    assert "cache_hits" in data


def test_metrics_disabled(monkeypatch):
    from WebApp.app.core.config import settings
    monkeypatch.setenv("WEBAPP_ENABLE_METRICS", "0")
    # Recreate settings to pick up env override is non-trivial; instead simulate flag
    settings.enable_metrics_endpoint = False
    client = TestClient(app)
    r = client.get("/metrics")
    assert r.status_code == 404
    # restore
    settings.enable_metrics_endpoint = True
