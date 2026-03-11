import json
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_route_enforces_jwt_scope_policy():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")
        reg = await ac.post(
            "/mini-cloud/services/orders/instances",
            json={"instance_id": "orders-policy-1",
                  "url": "http://orders-policy-1", "ttl_seconds": 30},
        )
        assert reg.status_code == 200

        unauthorized = await ac.post(
            "/mini-cloud/services/orders/route",
            json={"path": "/orders/42", "client_id": "policy-test-client"},
        )
        assert unauthorized.status_code == 401

        forbidden = await ac.post(
            "/mini-cloud/services/orders/route",
            json={
                "path": "/orders/42",
                "auth_token": "Bearer fake",
                "scopes": ["gateway.write"],
                "client_id": "policy-test-client",
            },
        )
        assert forbidden.status_code == 403

        ok = await ac.post(
            "/mini-cloud/services/orders/route",
            json={
                "path": "/orders/42",
                "auth_token": "Bearer fake",
                "scopes": ["gateway.read", "gateway.write"],
                "client_id": "policy-test-client",
            },
        )
        assert ok.status_code == 200
        assert ok.json()[
            "applied_route_policy"]["auth_policy"] == "jwt_default"


@pytest.mark.asyncio
async def test_route_enforces_rate_limit_from_custom_policy(tmp_path):
    from app.main import app

    custom_policy = {
        "version": "policies/test",
        "routes": [
            {
                "path_prefix": "/tiny",
                "service": "tiny",
                "strategy": "round_robin",
                "auth_policy": "open",
                "rate_limit_policy": "tight",
            }
        ],
        "auth": {"open": {"name": "open", "mode": "none", "scopes": []}},
        "rate_limits": {"tight": {"name": "tight", "limit": 2, "window_seconds": 60}},
    }
    policy_path = tmp_path / "policies.test.json"
    policy_path.write_text(json.dumps(custom_policy), encoding="utf-8")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")
        reg = await ac.post(
            "/mini-cloud/services/tiny/instances",
            json={"instance_id": "tiny-1",
                  "url": "http://tiny-1", "ttl_seconds": 30},
        )
        assert reg.status_code == 200

        for _ in range(2):
            ok = await ac.post(
                "/mini-cloud/services/tiny/route",
                params={"policy_path": str(policy_path)},
                json={"path": "/tiny/a", "client_id": "rate-client"},
            )
            assert ok.status_code == 200

        limited = await ac.post(
            "/mini-cloud/services/tiny/route",
            params={"policy_path": str(policy_path)},
            json={"path": "/tiny/a", "client_id": "rate-client"},
        )
        assert limited.status_code == 429


@pytest.mark.asyncio
async def test_control_loop_tick_updates_status():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")
        burst = await ac.post("/mini-cloud/failures/burst-traffic", json={"rps": 5, "duration_seconds": 2})
        assert burst.status_code == 200
        assert burst.json()["queue_depth_after_enqueue"] >= 10

        slow = await ac.post("/mini-cloud/failures/slow-downstream", json={"latency_ms": 900})
        assert slow.status_code == 200

        tick = await ac.post("/mini-cloud/control-loop/tick")
        assert tick.status_code == 200
        assert tick.json()["autoscaler"]["replicas"] >= 1

        status = await ac.get("/mini-cloud/control-loop/status")
        assert status.status_code == 200
        assert status.json()["queue_depth"] >= 10
        assert status.json()["simulated_latency_p95_ms"] == 900.0
