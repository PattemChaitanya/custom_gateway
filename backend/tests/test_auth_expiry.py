from fastapi.testclient import TestClient
from app.main import app
from time import sleep

from app.api.auth import auth_service


client = TestClient(app)


def test_expired_refresh_token(monkeypatch):
    # shorten refresh expiry to 1 second for this test
    monkeypatch.setattr(auth_service, "REFRESH_TOKEN_EXPIRE_SECONDS", 1)

    # register and login a user to get a very short-lived refresh token
    client.post("/auth/register", json={"email": "temp@example.com", "password": "pwd"})
    login = client.post("/auth/login", json={"email": "temp@example.com", "password": "pwd"})
    data = login.json()
    refresh_token = data.get("refresh_token")
    assert refresh_token is not None

    # wait for token to expire
    sleep(2)

    # refresh should now fail due to expiry
    r = client.post("/auth/refresh-tokens", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    assert r.json().get("error") is not None

