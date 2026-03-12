from fastapi.testclient import TestClient


def test_audit_log_routes_are_registered():
    from app.main import app

    client = TestClient(app)

    list_resp = client.get("/api/audit-logs")
    stats_resp = client.get("/api/audit-logs/statistics")

    # Endpoints require auth, so unauthenticated requests should be 401, not 404.
    assert list_resp.status_code == 401
    assert stats_resp.status_code == 401
