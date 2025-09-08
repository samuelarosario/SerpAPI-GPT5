import os
os.environ["WEBAPP_TESTING"] = "1"

from fastapi.testclient import TestClient

from WebApp.app.main import app

client = TestClient(app)

TEST_EMAIL = "user@example.com"
TEST_PASSWORD = "StrongPassw0rd!"

def test_register_and_login():
    # register
    r = client.post("/auth/register", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    if r.status_code == 201:
        # duplicate register blocked
        r2 = client.post("/auth/register", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
        assert r2.status_code == 400
    else:
        # Allow test to continue if already seeded by startup logic
        assert r.status_code == 400, r.text

    # login
    r3 = client.post("/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    assert r3.status_code == 200, r3.text
    data = r3.json()
    assert "access_token" in data and data["token_type"] == "bearer"
    assert "refresh_token" in data

    # refresh
    r4 = client.post("/auth/refresh", params={"token": data["refresh_token"]})
    assert r4.status_code == 200
    refreshed = r4.json()
    assert refreshed["access_token"] != data["access_token"]
