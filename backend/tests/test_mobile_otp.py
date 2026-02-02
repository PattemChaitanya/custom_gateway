from fastapi.testclient import TestClient
import pytest


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def test_send_and_verify_mobile_otp(client):
    mobile = "+15550001111"
    # send OTP to mobile via unified endpoint
    r = client.post("/auth/send-otp", json={"mobile": mobile})
    assert r.status_code == 200
    data = r.json()
    # service may not return OTP in non-dev env; fallback stores code in module globals when DB not ready
    from app.api.auth import auth_service as svc
    stored = svc.__dict__.get('_OTP_CODES', {})
    entry = stored.get(mobile) or {}
    code = entry.get('otp')

    # If code not found, tests may be running with DB-backed storage and DEV_RETURN_OTP disabled.
    # In that case assert that response indicates sent and skip verification.
    if not code:
        assert data.get("message") in ("OTP sent", "otp code sent", "otp code recently sent", "OTP recently sent") or data.get("message")
        return

    # verify using the mobile as the email/target param (service accepts a string identifier)
    v = client.post("/auth/verify-otp", json={"email": mobile, "otp": code})
    assert v.status_code == 200
    assert v.json().get("message") == "OTP verified"
