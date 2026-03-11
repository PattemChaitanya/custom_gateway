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
            json={"instance_id": "r-1",
                  "url": "http://router-1", "ttl_seconds": 300},
        )
        assert reg.status_code == 200

        bad = await ac.post(
            "/mini-cloud/services/router-svc/route",
            json={"path": "/", "strategy": "random_bad",
                  "client_id": "route-strategy-test"},
        )
        assert bad.status_code == 400


@pytest.mark.asyncio
async def test_round_robin_failover_uses_only_routable_instances():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        reset = await ac.post("/mini-cloud/reset")
        assert reset.status_code == 200

        reg1 = await ac.post(
            "/mini-cloud/services/failover-svc/instances",
            json={"instance_id": "f-1",
                  "url": "http://failover-1", "ttl_seconds": 300},
        )
        assert reg1.status_code == 200, reg1.text

        reg2 = await ac.post(
            "/mini-cloud/services/failover-svc/instances",
            json={"instance_id": "f-2",
                  "url": "http://failover-2", "ttl_seconds": 300},
        )
        assert reg2.status_code == 200, reg2.text

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

        healthy_list = await ac.get(
            "/mini-cloud/services/failover-svc/instances",
            params={"healthy_only": True},
        )
        assert healthy_list.status_code == 200
        healthy_ids = {item["instance_id"] for item in healthy_list.json()}
        assert healthy_ids == {"f-1"}, healthy_list.text

        for _ in range(5):
            routed = await ac.post(
                "/mini-cloud/services/failover-svc/route",
                json={"path": "/", "strategy": "round_robin",
                      "client_id": "failover-client"},
            )
            assert routed.status_code == 200, routed.text
            assert routed.json()["target"]["instance_id"] == "f-1"


@pytest.mark.asyncio
async def test_weighted_round_robin_biases_heavier_instance():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        reset = await ac.post("/mini-cloud/reset")
        assert reset.status_code == 200

        reg1 = await ac.post(
            "/mini-cloud/services/wrr-svc/instances",
            json={"instance_id": "w-light", "url": "http://wrr-light",
                  "ttl_seconds": 300, "weight": 1},
        )
        assert reg1.status_code == 200, reg1.text

        reg2 = await ac.post(
            "/mini-cloud/services/wrr-svc/instances",
            json={"instance_id": "w-heavy", "url": "http://wrr-heavy",
                  "ttl_seconds": 300, "weight": 3},
        )
        assert reg2.status_code == 200, reg2.text

        healthy_list = await ac.get(
            "/mini-cloud/services/wrr-svc/instances",
            params={"healthy_only": True},
        )
        assert healthy_list.status_code == 200
        assert len(healthy_list.json()) == 2, healthy_list.text

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
