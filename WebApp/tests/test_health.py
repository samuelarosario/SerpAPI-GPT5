import os
os.environ["WEBAPP_TESTING"] = "1"

from fastapi.testclient import TestClient

from WebApp.app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
