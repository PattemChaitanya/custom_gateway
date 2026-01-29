import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_api_crud_endpoints(monkeypatch):
    # Import app here so conftest's alembic migrations (autouse fixture)
    # run before the application binds to the DB URL.
    from app.main import app
    # Use test DB configured by conftest (DATABASE_URL set)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        # create
        payload = {"name": "int-api", "version": "v1", "description": "integration test"}
        create_resp = await ac.post("/apis/", json=payload)
        assert create_resp.status_code == 201
        data = create_resp.json()
        api_id = data["id"]

        # get
        get_resp = await ac.get(f"/apis/{api_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["name"] == "int-api"

        # list
        list_resp = await ac.get("/apis/")
        assert list_resp.status_code == 200
        assert any(a["id"] == api_id for a in list_resp.json())

        # update
        update_payload = {"description": "updated"}
        upd_resp = await ac.put(f"/apis/{api_id}", json=update_payload)
        assert upd_resp.status_code == 200
        assert upd_resp.json()["description"] == "updated"

        # delete
        del_resp = await ac.delete(f"/apis/{api_id}")
        assert del_resp.status_code == 204


@pytest.mark.asyncio
async def test_duplicate_api_create_returns_conflict():
    from app.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        payload = {"name": "dup-api", "version": "v1"}
        r1 = await ac.post("/apis/", json=payload)
        assert r1.status_code == 201
        r2 = await ac.post("/apis/", json=payload)
        assert r2.status_code == 409
