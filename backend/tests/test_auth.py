from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def test_root_info(client):
    resp = client.get("/auth/")
    assert resp.status_code == 200
    assert resp.json() == {"Auth": "This is the Auth endpoint"}


def test_register_and_login_and_me(client):
    # register
    payload = {"email": "alice@example.com", "password": "secret"}
    r = client.post("/auth/register", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data.get("message") == "User registered" or data.get("error") == "user_exists"

    # login
    r = client.post("/auth/login", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data and "refresh_token" in data
    access = data["access_token"]

    # me (send token as Bearer header)
    headers = {"Authorization": f"Bearer {access}"}
    r = client.get("/auth/me", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data.get("message") == "Current user"
    assert data.get("email") == "alice@example.com"


def test_refresh_and_reset_and_verify(client):
    # refresh - use the refresh token from login
    login = client.post("/auth/login", json={"email": "charlie@example.com", "password": "pwd"})
    # register and login a user to get a refresh token
    client.post("/auth/register", json={"email": "charlie@example.com", "password": "pwd"})
    login = client.post("/auth/login", json={"email": "charlie@example.com", "password": "pwd"})
    refresh_token = login.json().get("refresh_token")
    r = client.post("/auth/refresh-tokens", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    assert r.json().get("message") == "Tokens refreshed"

    # logout (revoke refresh token) and ensure it can no longer be used
    lo = client.post("/auth/logout", json={"refresh_token": refresh_token})
    assert lo.status_code == 200
    assert lo.json().get("message") == "User logged out"

    # using the revoked refresh token should fail
    r2 = client.post("/auth/refresh-tokens", json={"refresh_token": refresh_token})
    assert r2.status_code == 200
    assert r2.json().get("error") is not None

    # reset password
    r = client.post("/auth/reset-password", json={"email": "bob@example.com"})
    assert r.status_code == 200
    assert r.json().get("message") == "Password reset link sent"

    # verify email
    r = client.post("/auth/verify-email", json={"email": "bob@example.com", "code": "1234"})
    assert r.status_code == 200
    assert r.json().get("message") == "Email verified"

    # verify otp
    r = client.post("/auth/verify-otp", json={"otp": "9999"})
    assert r.status_code == 200
    assert r.json().get("message") == "OTP verified"
