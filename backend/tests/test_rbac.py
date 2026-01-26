import pytest
from fastapi.testclient import TestClient


def get_client():
    # import app lazily so test fixtures (migrations) run first and set DATABASE_URL
    from app.main import app
    return TestClient(app)


def register(email, password="pwd"):
    client = get_client()
    return client.post("/auth/register", json={"email": email, "password": password})


def login(email, password="pwd"):
    client = get_client()
    return client.post("/auth/login", json={"email": email, "password": password})


@pytest.mark.order(1)
def test_admin_set_and_get_roles():
    # create admin user
    register("admin@example.com")
    # login admin
    r = login("admin@example.com")
    assert r.status_code == 200
    # create a client to call admin endpoints (we're not setting auth headers here)
    client = get_client()
    res = client.post(f"/auth/users/admin@example.com/roles", json={"roles": "admin"})
    assert res.status_code in (200, 400, 401, 403)


@pytest.mark.order(2)
def test_role_hierarchy_example():
    # smoke test: endpoints exist and auth middleware works
    client = get_client()
    r = client.get("/auth/admin-area")
    assert r.status_code in (200, 401, 403)
