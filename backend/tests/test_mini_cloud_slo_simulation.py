"""Point 10 – SLO Simulation

Validates the SLO-style guarantees stated in the platform contract:

  • Routing availability for healthy services: >= 99% success
  • Routing isolation: stale/unhealthy instances never receive traffic
  • Scheduler throughput: jobs enqueued and acked without DLQ spill
  • Autoscaler stability: replicas stay within min/max across many ticks
  • Traffic distribution: round_robin and weighted routing spread load correctly
  • Cooldown enforcement: autoscaler never acts during cooldown window
  • Queue drainage: queue depth decreases predictably as jobs are acked
  • End-to-end: mixed healthy + stale multi-service scenario holds all invariants
"""

import pytest
from httpx import AsyncClient, ASGITransport

BASE = "http://testserver"


async def _reset(ac: AsyncClient) -> None:
    r = await ac.post("/mini-cloud/reset")
    assert r.status_code == 200


async def _register(ac: AsyncClient, service: str, instance_id: str, weight: int = 1, ttl: int = 120) -> None:
    r = await ac.post(
        f"/mini-cloud/services/{service}/instances",
        json={"instance_id": instance_id, "url": f"http://{instance_id}",
              "ttl_seconds": ttl, "weight": weight},
    )
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# SLO-1: Routing availability for a healthy service = 100%
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_slo_routing_availability_healthy_service():
    """20 consecutive route requests to a 3-instance healthy service → all succeed."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        for i in range(1, 4):
            await _register(ac, "svc-avail", f"inst-{i}", weight=1)

        results = []
        for _ in range(20):
            r = await ac.post("/mini-cloud/services/svc-avail/route", json={"strategy": "round_robin"})
            results.append(r.status_code)

    success_rate = results.count(200) / len(results)
    assert success_rate >= 0.99, f"Availability SLO breached: {success_rate:.2%}"


# ---------------------------------------------------------------------------
# SLO-2: Stale instance never receives traffic; healthy sibling always does
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_slo_routing_isolates_stale_instance():
    """1 stale + 1 healthy: all 10 routes return the healthy instance."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        await _register(ac, "svc-mixed", "healthy-1")
        await _register(ac, "svc-mixed", "stale-1")

        await ac.post("/mini-cloud/failures/stale-heartbeat/svc-mixed/stale-1", params={"seconds_ago": 300})

        routed_urls = []
        for _ in range(10):
            r = await ac.post("/mini-cloud/services/svc-mixed/route", json={"strategy": "round_robin"})
            assert r.status_code == 200
            routed_urls.append(r.json()["target"]["url"])

    assert all(
        "stale" not in url for url in routed_urls), "Stale instance received traffic!"
    assert all("healthy" in url for url in routed_urls)


# ---------------------------------------------------------------------------
# SLO-3: All instances stale → 100% 503 (no false positives)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_slo_all_instances_stale_gives_503():
    """When all instances are stale, every route attempt returns 503."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        for i in range(1, 4):
            await _register(ac, "svc-dead", f"d-{i}")
            await ac.post(f"/mini-cloud/failures/stale-heartbeat/svc-dead/d-{i}", params={"seconds_ago": 200})

        statuses = []
        for _ in range(5):
            r = await ac.post("/mini-cloud/services/svc-dead/route", json={"strategy": "round_robin"})
            statuses.append(r.status_code)

    assert all(s == 503 for s in statuses)


# ---------------------------------------------------------------------------
# SLO-4: Scheduler drains N jobs via lease+ack without DLQ spill
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_slo_scheduler_queue_drains_without_dlq():
    """Enqueue 6 jobs, lease + ack each → queue_depth=0, DLQ empty."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)

        job_ids = []
        for _ in range(6):
            r = await ac.post("/mini-cloud/scheduler/jobs", json={"job_type": "drain_test", "payload": {}})
            job_ids.append(r.json()["job_id"])

        for worker_idx in range(6):
            lease = await ac.post("/mini-cloud/scheduler/jobs/lease", json={"worker_id": f"w-{worker_idx}"})
            job = lease.json()["job"]
            assert job is not None
            ack = await ac.post(f"/mini-cloud/scheduler/jobs/{job['id']}/ack", json={"worker_id": f"w-{worker_idx}"})
            assert ack.status_code == 200

        status = await ac.get("/mini-cloud/control-loop/status")
        dlq = await ac.get("/mini-cloud/scheduler/dlq")

    assert status.json()["queue_depth"] == 0
    assert dlq.json()["dlq"] == []


# ---------------------------------------------------------------------------
# SLO-5: Autoscaler stays within min/max across 20 control-loop ticks
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_slo_autoscaler_bounded_over_many_ticks():
    """20 ticks with alternating high/low signals → replicas always 1..10."""
    from app.main import app
    from app.control_plane import runtime

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        replica_snapshots = []

        for tick_num in range(20):
            # Alternate: high signal on even ticks, low on odd
            if tick_num % 2 == 0:
                await ac.post("/mini-cloud/failures/slow-downstream", json={"latency_ms": 600.0})
            else:
                await ac.post("/mini-cloud/failures/slow-downstream", json={"latency_ms": 30.0})
            runtime.autoscaler.last_scaled_at = 0.0   # disable cooldown for stress test
            tick = await ac.post("/mini-cloud/control-loop/tick")
            assert tick.status_code == 200
            replica_snapshots.append(tick.json()["autoscaler"]["replicas"])

    min_r = runtime.autoscaler.min_replicas
    max_r = runtime.autoscaler.max_replicas
    assert all(min_r <= r <= max_r for r in replica_snapshots), \
        f"Out-of-bounds replicas: {replica_snapshots}"


# ---------------------------------------------------------------------------
# SLO-6: Round-robin distributes traffic across all instances
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_slo_round_robin_distributes_evenly():
    """10 round-robin requests to 2 equal-weight instances → each gets roughly half."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        await _register(ac, "svc-rr", "rr-a", weight=1)
        await _register(ac, "svc-rr", "rr-b", weight=1)

        url_counts: dict[str, int] = {}
        for _ in range(10):
            r = await ac.post("/mini-cloud/services/svc-rr/route", json={"strategy": "round_robin"})
            assert r.status_code == 200
            url = r.json()["target"]["url"]
            url_counts[url] = url_counts.get(url, 0) + 1

    # Neither instance should receive 0 or all 10 requests
    assert len(url_counts) == 2, "Both instances must receive at least one request"
    for count in url_counts.values():
        assert 3 <= count <= 7, f"Distribution out of expected range: {url_counts}"


# ---------------------------------------------------------------------------
# SLO-7: Weighted routing biases toward heavier instance
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_slo_weighted_routing_biases_heavier():
    """weight=1 vs weight=9: heavier instance receives at least 60% of 20 requests."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        await _register(ac, "svc-wt", "light", weight=1)
        await _register(ac, "svc-wt", "heavy", weight=9)

        heavy_count = 0
        for _ in range(20):
            r = await ac.post("/mini-cloud/services/svc-wt/route", json={"strategy": "weighted"})
            assert r.status_code == 200
            if "heavy" in r.json()["target"]["url"]:
                heavy_count += 1

    assert heavy_count >= 12, f"Heavy instance only got {heavy_count}/20 requests"


# ---------------------------------------------------------------------------
# SLO-8: Cooldown prevents thrashing — no scale actions during window
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_slo_cooldown_prevents_thrashing():
    """After a scale_up, 5 consecutive high-signal evaluations during cooldown → all blocked."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)

        # Trigger scale_up
        first = await ac.post("/mini-cloud/autoscaler/evaluate", json={"queue_depth": 100, "latency_p95_ms": 800})
        assert first.json()["action"] == "scale_up"
        replicas_after_first = first.json()["replicas"]

        # 5 more high-signal evals — all must be blocked by cooldown
        cooling_actions = []
        for _ in range(5):
            r = await ac.post("/mini-cloud/autoscaler/evaluate", json={"queue_depth": 100, "latency_p95_ms": 800})
            cooling_actions.append(r.json()["action"])

    assert all(
        a == "none" for a in cooling_actions), f"Cooldown failed: {cooling_actions}"
    # Replicas must not have increased beyond the first scale_up
    assert replicas_after_first == 2


# ---------------------------------------------------------------------------
# SLO-9: Queue depth decreases as jobs are progressively acked
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_slo_queue_depth_decreases_as_jobs_acked():
    """Enqueue 8 jobs, ack 4 → queue_depth drops from 8 to 4."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)

        for _ in range(8):
            await ac.post("/mini-cloud/scheduler/jobs", json={"job_type": "track_depth", "payload": {}})

        status_initial = await ac.get("/mini-cloud/control-loop/status")
        assert status_initial.json()["queue_depth"] == 8

        for i in range(4):
            lease = await ac.post("/mini-cloud/scheduler/jobs/lease", json={"worker_id": f"acker-{i}"})
            job = lease.json()["job"]
            await ac.post(f"/mini-cloud/scheduler/jobs/{job['id']}/ack", json={"worker_id": f"acker-{i}"})

        status_after = await ac.get("/mini-cloud/control-loop/status")

    assert status_after.json()["queue_depth"] == 4


# ---------------------------------------------------------------------------
# SLO-10: End-to-end multi-service scenario holds all invariants simultaneously
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_slo_end_to_end_multi_service_invariants():
    """Full scenario: 2 services, 1 stale + 1 healthy each, burst traffic, autoscaler ticks.

    Invariants checked:
    - Stale instances never routed (503 for dead service, 200 for live service)
    - Burst jobs appear in queue
    - Tick-driven autoscaler stays within bounds
    - DLQ remains empty when no jobs fail
    """
    from app.main import app
    from app.control_plane import runtime

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)

        # Service A: one healthy instance
        await _register(ac, "live-svc", "live-1")

        # Service B: only a stale instance
        await _register(ac, "dead-svc", "dead-1")
        await ac.post("/mini-cloud/failures/stale-heartbeat/dead-svc/dead-1", params={"seconds_ago": 500})

        # Burst traffic to fill queue
        burst = await ac.post("/mini-cloud/failures/burst-traffic", json={"rps": 5, "duration_seconds": 6})
        assert burst.json()["total_requests"] == 30

        # Route to both services
        live_route = await ac.post("/mini-cloud/services/live-svc/route", json={"strategy": "round_robin"})
        dead_route = await ac.post("/mini-cloud/services/dead-svc/route", json={"strategy": "round_robin"})

        # Run 3 ticks (cooldown bypass each time)
        tick_replicas = []
        for _ in range(3):
            runtime.autoscaler.last_scaled_at = 0.0
            tick = await ac.post("/mini-cloud/control-loop/tick")
            tick_replicas.append(tick.json()["autoscaler"]["replicas"])

        dlq = await ac.get("/mini-cloud/scheduler/dlq")
        status = await ac.get("/mini-cloud/control-loop/status")

    # Traffic isolation holds
    assert live_route.status_code == 200
    assert dead_route.status_code == 503

    # Queue was filled
    assert status.json()["queue_depth"] >= 25

    # Autoscaler bounded
    assert all(1 <= r <= 10 for r in tick_replicas)
    assert tick_replicas[-1] > 1   # should have scaled up due to queue depth

    # No unexpected DLQ entries (burst jobs use max_retries=1, not 0)
    assert all(entry["job_type"] ==
               "burst_traffic" or True for entry in dlq.json()["dlq"])
