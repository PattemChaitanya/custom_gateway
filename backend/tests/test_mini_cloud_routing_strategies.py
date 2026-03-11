import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_route_rejects_unsupported_strategy():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")
        reg = await ac.post(
            "/mini-cloud/services/router-svc/instances",
            json={"instance_id": "r-1", "url": "http://router-1", "ttl_seconds": 30},
        )
        assert reg.status_code == 200

        bad = await ac.post(
            "/mini-cloud/services/router-svc/route",
            json={"path": "/", "strategy": "random_bad", "client_id": "route-strategy-test"},
        )
        assert bad.status_code == 400


@pytest.mark.asyncio
async def test_round_robin_failover_uses_only_routable_instances():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")
        await ac.post(
            "/mini-cloud/services/failover-svc/instances",
            json={"instance_id": "f-1", "url": "http://failover-1", "ttl_seconds": 30},
        )
        await ac.post(
            "/mini-cloud/services/failover-svc/instances",
            json={"instance_id": "f-2", "url": "http://failover-2", "ttl_seconds": 30},
        )

        # Keep one degraded (still routable), force one unhealthy (not routable).
        degraded = await ac.post(
            "/mini-cloud/services/failover-svc/instances/f-1/health-status",
            json={"health_status": "degraded"},
        )
        assert degraded.status_code == 200
        unhealthy = await ac.post(
            "/mini-cloud/services/failover-svc/instances/f-2/health-status",
            json={"health_status": "unhealthy"},
        )
        assert unhealthy.status_code == 200

        for _ in range(5):
            routed = await ac.post(
                "/mini-cloud/services/failover-svc/route",
                json={"path": "/", "strategy": "round_robin", "client_id": "failover-client"},
            )
            assert routed.status_code == 200, routed.text
            assert routed.json()["target"]["instance_id"] == "f-1"


@pytest.mark.asyncio
async def test_weighted_round_robin_biases_heavier_instance():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")
        await ac.post(
            "/mini-cloud/services/wrr-svc/instances",
            json={"instance_id": "w-light", "url": "http://wrr-light", "ttl_seconds": 30, "weight": 1},
        )
        await ac.post(
            "/mini-cloud/services/wrr-svc/instances",
            json={"instance_id": "w-heavy", "url": "http://wrr-heavy", "ttl_seconds": 30, "weight": 3},
        )

        picks = []
        for _ in range(24):
            routed = await ac.post(
                "/mini-cloud/services/wrr-svc/route",
                json={
                    "path": "/",
                    "strategy": "weighted_round_robin",
                    "client_id": "wrr-client",
                },
            )
            assert routed.status_code == 200, routed.text
            picks.append(routed.json()["target"]["instance_id"])

        assert picks.count("w-heavy") > picks.count("w-light")