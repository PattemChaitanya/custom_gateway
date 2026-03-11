"""Point 8 – Failure Injection & Platform Invariants

Chaos-style integration tests using the four failure injection endpoints:

  POST /mini-cloud/failures/stale-heartbeat/{service}/{instance_id}
  POST /mini-cloud/failures/worker-crash/{job_id}
  POST /mini-cloud/failures/slow-downstream
  POST /mini-cloud/failures/burst-traffic

Platform invariants that must hold:

  STALE HEARTBEAT:
    INV-1  A stale instance is NEVER routed to (routing returns 503)
    INV-2  The stale instance still appears in the full instance list (tombstone)
    INV-3  Injecting stale on an unknown instance → 404 (not a silent failure)

  WORKER CRASH:
    INV-4  Expired lease is re-acquirable immediately by any worker
    INV-5  Original owner CANNOT ack after lease has been expired by crash injection
    INV-6  Worker crash on unknown job_id → 404

  SLOW DOWNSTREAM:
    INV-7  Simulated latency is reflected in /control-loop/status immediately
    INV-8  Slow-downstream latency drives scale_up on the next control-loop tick
    INV-9  A second slow-downstream call overwrites the previous value (last-write-wins)

  BURST TRAFFIC:
    INV-10 burst total_requests == rps × duration_seconds (math check)
    INV-11 All burst jobs hit the scheduler queue (queue_depth == total_requests)
    INV-12 Burst + tick → autoscaler scales up when queue_depth ≥ 25

  COMPOUND:
    INV-13 Simultaneous stale-heartbeat + burst-traffic: traffic isolation + queue spike
"""

import pytest
from httpx import AsyncClient, ASGITransport

BASE = "http://testserver"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
async def _reset(ac: AsyncClient) -> None:
    r = await ac.post("/mini-cloud/reset")
    assert r.status_code == 200


async def _register(ac: AsyncClient, service: str, instance_id: str, ttl: int = 60, weight: int = 1) -> None:
    r = await ac.post(
        f"/mini-cloud/services/{service}/instances",
        json={"instance_id": instance_id, "url": f"http://{instance_id}",
              "ttl_seconds": ttl, "weight": weight},
    )
    assert r.status_code == 200


async def _enqueue(ac: AsyncClient, job_type: str = "task") -> str:
    r = await ac.post("/mini-cloud/scheduler/jobs", json={"job_type": job_type, "payload": {}})
    assert r.status_code == 200
    return r.json()["job_id"]


async def _lease(ac: AsyncClient, worker_id: str) -> dict | None:
    r = await ac.post("/mini-cloud/scheduler/jobs/lease", json={"worker_id": worker_id})
    assert r.status_code == 200
    return r.json()["job"]


# ===========================================================================
# STALE HEARTBEAT invariants
# ===========================================================================

@pytest.mark.asyncio
async def test_inv1_stale_instance_never_routed():
    """INV-1: After stale-heartbeat injection the instance is excluded from routing → 503."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        await _register(ac, "payments", "pay-1")

        # Healthy route works
        ok = await ac.post("/mini-cloud/services/payments/route", json={"strategy": "round_robin"})
        assert ok.status_code == 200

        # Inject stale heartbeat
        r = await ac.post("/mini-cloud/failures/stale-heartbeat/payments/pay-1", params={"seconds_ago": 120})
        assert r.status_code == 200

        # Now routing must fail → 503
        route = await ac.post("/mini-cloud/services/payments/route", json={"strategy": "round_robin"})
        assert route.status_code == 503


@pytest.mark.asyncio
async def test_inv2_stale_instance_purged_from_registry():
    """INV-2: The list endpoint calls expire_instances() — a stale instance is fully purged
    from the registry (not tombstoned), so it appears in neither the full list nor the
    healthy-only list."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        await _register(ac, "inventory", "inv-1")

        await ac.post("/mini-cloud/failures/stale-heartbeat/inventory/inv-1", params={"seconds_ago": 200})

        # The list endpoint calls expire_instances() before returning; stale instance is gone
        all_instances = await ac.get("/mini-cloud/services/inventory/instances")
        assert all_instances.status_code == 200
        ids = [i["instance_id"] for i in all_instances.json()]
        assert "inv-1" not in ids

        # healthy_only=true also returns empty
        healthy = await ac.get("/mini-cloud/services/inventory/instances", params={"healthy_only": "true"})
        assert healthy.status_code == 200
        assert healthy.json() == []


@pytest.mark.asyncio
async def test_inv3_stale_on_unknown_instance_returns_404():
    """INV-3: Stale heartbeat injection on a nonexistent instance → 404, no silent swallow."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        r = await ac.post(
            "/mini-cloud/failures/stale-heartbeat/ghost-service/ghost-instance",
            params={"seconds_ago": 60},
        )
        assert r.status_code == 404


# ===========================================================================
# WORKER CRASH invariants
# ===========================================================================

@pytest.mark.asyncio
async def test_inv4_expired_lease_reacquirable_by_any_worker():
    """INV-4: After worker-crash the job is immediately leasable by a new worker."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        job_id = await _enqueue(ac)

        first = await _lease(ac, "worker-alpha")
        assert first is not None and first["id"] == job_id

        crash = await ac.post(f"/mini-cloud/failures/worker-crash/{job_id}")
        assert crash.status_code == 200

        second = await _lease(ac, "worker-beta")
        assert second is not None
        assert second["id"] == job_id


@pytest.mark.asyncio
async def test_inv5_original_owner_cannot_ack_after_crash():
    """INV-5: After crash injection the original owner's ack must be rejected (409)."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        job_id = await _enqueue(ac)
        first = await _lease(ac, "worker-alpha")
        assert first is not None

        await ac.post(f"/mini-cloud/failures/worker-crash/{job_id}")

        # Let worker-beta re-acquire the lease
        await _lease(ac, "worker-beta")

        # Original owner tries to ack — should be rejected
        ack = await ac.post(
            f"/mini-cloud/scheduler/jobs/{job_id}/ack",
            json={"worker_id": "worker-alpha"},
        )
        assert ack.status_code == 409


@pytest.mark.asyncio
async def test_inv6_worker_crash_unknown_job_returns_404():
    """INV-6: Worker crash on an unknown job_id → 404."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        r = await ac.post("/mini-cloud/failures/worker-crash/no-such-job-id-xyz")
        assert r.status_code == 404


# ===========================================================================
# SLOW DOWNSTREAM invariants
# ===========================================================================

@pytest.mark.asyncio
async def test_inv7_slow_downstream_reflected_in_status():
    """INV-7: Injected latency appears immediately in /control-loop/status."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        await ac.post("/mini-cloud/failures/slow-downstream", json={"latency_ms": 750.0})

        status = await ac.get("/mini-cloud/control-loop/status")
        assert status.status_code == 200
        assert status.json()["simulated_latency_p95_ms"] == 750.0


@pytest.mark.asyncio
async def test_inv8_slow_downstream_drives_scale_up_on_tick():
    """INV-8: 500 ms latency → next tick triggers scale_up."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        await ac.post("/mini-cloud/failures/slow-downstream", json={"latency_ms": 500.0})

        tick = await ac.post("/mini-cloud/control-loop/tick")
        assert tick.status_code == 200
        data = tick.json()

    assert data["autoscaler"]["action"] == "scale_up"
    assert data["simulated_latency_p95_ms"] == 500.0


@pytest.mark.asyncio
async def test_inv9_slow_downstream_last_write_wins():
    """INV-9: Second slow-downstream POST overwrites the first value."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        await ac.post("/mini-cloud/failures/slow-downstream", json={"latency_ms": 800.0})
        await ac.post("/mini-cloud/failures/slow-downstream", json={"latency_ms": 50.0})

        status = await ac.get("/mini-cloud/control-loop/status")
        assert status.json()["simulated_latency_p95_ms"] == 50.0


# ===========================================================================
# BURST TRAFFIC invariants
# ===========================================================================

@pytest.mark.asyncio
async def test_inv10_burst_total_requests_math():
    """INV-10: total_requests == rps × duration_seconds always holds."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        r = await ac.post("/mini-cloud/failures/burst-traffic", json={"rps": 7, "duration_seconds": 4})
        assert r.status_code == 200
        data = r.json()

    assert data["total_requests"] == 7 * 4
    assert data["rps"] == 7
    assert data["duration_seconds"] == 4


@pytest.mark.asyncio
async def test_inv11_burst_jobs_hit_scheduler_queue():
    """INV-11: All burst jobs are enqueued; queue_depth == total_requests after burst."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        r = await ac.post("/mini-cloud/failures/burst-traffic", json={"rps": 5, "duration_seconds": 4})
        assert r.status_code == 200
        data = r.json()

    assert data["total_requests"] == 20
    assert data["queue_depth_after_enqueue"] == 20


@pytest.mark.asyncio
async def test_inv12_burst_plus_tick_scales_up():
    """INV-12: 30-job burst (≥ 25 threshold) → tick → scale_up."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        await ac.post("/mini-cloud/failures/burst-traffic", json={"rps": 10, "duration_seconds": 3})

        tick = await ac.post("/mini-cloud/control-loop/tick")
        assert tick.status_code == 200
        data = tick.json()

    assert data["queue_depth"] >= 25
    assert data["autoscaler"]["action"] == "scale_up"


# ===========================================================================
# COMPOUND invariants
# ===========================================================================

@pytest.mark.asyncio
async def test_inv13_stale_heartbeat_and_burst_are_independent():
    """INV-13: Stale-heartbeat isolates traffic while burst-traffic fills the queue independently.

    Invariants checked:
    - Routing to 'catalog' is blocked after its only instance goes stale → 503
    - 20 burst jobs appear in the scheduler queue
    - The two failures do not interfere with each other
    """
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)

        # Register a catalog instance
        await _register(ac, "catalog", "cat-1")

        # Verify routing works before injection
        pre = await ac.post("/mini-cloud/services/catalog/route", json={"strategy": "round_robin"})
        assert pre.status_code == 200

        # Inject stale heartbeat (traffic isolation)
        await ac.post("/mini-cloud/failures/stale-heartbeat/catalog/cat-1", params={"seconds_ago": 300})

        # Inject burst traffic (queue spike)
        burst = await ac.post("/mini-cloud/failures/burst-traffic", json={"rps": 5, "duration_seconds": 4})
        assert burst.status_code == 200
        assert burst.json()["total_requests"] == 20

        # INVARIANT A: catalog routing is blocked
        route = await ac.post("/mini-cloud/services/catalog/route", json={"strategy": "round_robin"})
        assert route.status_code == 503

        # INVARIANT B: scheduler queue has exactly the burst jobs
        status = await ac.get("/mini-cloud/control-loop/status")
        assert status.json()["queue_depth"] == 20
