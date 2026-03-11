import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_discovery_health_status_endpoint_flow():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")

        reg = await ac.post(
            "/mini-cloud/services/discovery-svc/instances",
            json={"instance_id": "disc-1",
                  "url": "http://disc-1", "ttl_seconds": 30},
        )
        assert reg.status_code == 200

        degraded = await ac.post(
            "/mini-cloud/services/discovery-svc/instances/disc-1/health-status",
            json={"health_status": "degraded"},
        )
        assert degraded.status_code == 200
        assert degraded.json()["health_status"] == "degraded"
        assert degraded.json()["healthy"] is True

        route_ok = await ac.post(
            "/mini-cloud/services/discovery-svc/route",
            json={
                "path": "/",
                "strategy": "round_robin",
                "client_id": "discovery-health-status",
            },
        )
        assert route_ok.status_code == 200

        unhealthy = await ac.post(
            "/mini-cloud/services/discovery-svc/instances/disc-1/health-status",
            json={"health_status": "unhealthy"},
        )
        assert unhealthy.status_code == 200
        assert unhealthy.json()["healthy"] is False

        route_blocked = await ac.post(
            "/mini-cloud/services/discovery-svc/route",
            json={
                "path": "/",
                "strategy": "round_robin",
                "client_id": "discovery-health-status",
            },
        )
        assert route_blocked.status_code == 503
