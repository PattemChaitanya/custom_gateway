import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_expired_instance_never_receives_traffic():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")
        reg = await ac.post(
            "/mini-cloud/services/orders/instances",
            json={
                "instance_id": "orders-1",
                "url": "http://orders-1",
                "ttl_seconds": 1,
                "weight": 1,
            },
        )
        assert reg.status_code == 200

        await ac.post(
            "/mini-cloud/failures/stale-heartbeat/orders/orders-1",
            params={"seconds_ago": 60},
        )

        route = await ac.post("/mini-cloud/services/orders/route", json={"strategy": "round_robin"})
        assert route.status_code == 503


@pytest.mark.asyncio
async def test_scheduler_worker_crash_releases_job_after_lease_expiry():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")
        enqueue = await ac.post("/mini-cloud/scheduler/jobs", json={"job_type": "reconcile", "payload": {}})
        assert enqueue.status_code == 200
        job_id = enqueue.json()["job_id"]

        first_lease = await ac.post("/mini-cloud/scheduler/jobs/lease", json={"worker_id": "w1"})
        assert first_lease.status_code == 200
        leased_job = first_lease.json()["job"]
        assert leased_job is not None
        assert leased_job["id"] == job_id

        crash = await ac.post(f"/mini-cloud/failures/worker-crash/{job_id}")
        assert crash.status_code == 200

        second_lease = await ac.post("/mini-cloud/scheduler/jobs/lease", json={"worker_id": "w2"})
        assert second_lease.status_code == 200
        leased_job_2 = second_lease.json()["job"]
        assert leased_job_2 is not None
        assert leased_job_2["id"] == job_id


@pytest.mark.asyncio
async def test_autoscaler_respects_min_max_replicas():
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")
        for _ in range(8):
            result = await ac.post(
                "/mini-cloud/autoscaler/evaluate",
                json={"queue_depth": 100, "latency_p95_ms": 800},
            )
            assert result.status_code == 200

        payload = result.json()
        assert payload["replicas"] <= 10
        assert payload["replicas"] >= 1
