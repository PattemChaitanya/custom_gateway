"""Point 7 – Autoscaling Simulation

API-level integration tests for the AutoscalerLoop via:
  POST /mini-cloud/autoscaler/evaluate
  POST /mini-cloud/control-loop/tick
  GET  /mini-cloud/control-loop/status
  POST /mini-cloud/failures/slow-downstream
  POST /mini-cloud/failures/burst-traffic

Thresholds (AutoscalerLoop defaults):
  scale_up_queue_depth  = 25       scale_up_latency_ms  = 400
  scale_down_queue_depth = 5       scale_down_latency_ms = 120
  cooldown_seconds       = 30       min_replicas = 1   max_replicas = 10
"""

import pytest
from httpx import AsyncClient, ASGITransport

BASE = "http://testserver"


async def _reset(ac: AsyncClient) -> None:
    r = await ac.post("/mini-cloud/reset")
    assert r.status_code == 200


async def _evaluate(ac: AsyncClient, queue_depth: int, latency_p95_ms: float) -> dict:
    r = await ac.post(
        "/mini-cloud/autoscaler/evaluate",
        json={"queue_depth": queue_depth, "latency_p95_ms": latency_p95_ms},
    )
    assert r.status_code == 200
    return r.json()


# ---------------------------------------------------------------------------
# 1. Scale-up on high queue depth
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scale_up_on_high_queue_depth():
    """queue_depth >= 25 triggers scale_up from min_replicas."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        result = await _evaluate(ac, queue_depth=30, latency_p95_ms=50.0)

    assert result["action"] == "scale_up"
    assert result["replicas"] == 2
    assert result["reason"] == "queue_or_latency_high"


# ---------------------------------------------------------------------------
# 2. Scale-up on high latency alone
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scale_up_on_high_latency_alone():
    """latency_p95_ms >= 400 triggers scale_up even with low queue depth."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        result = await _evaluate(ac, queue_depth=0, latency_p95_ms=500.0)

    assert result["action"] == "scale_up"
    assert result["reason"] == "queue_or_latency_high"


# ---------------------------------------------------------------------------
# 3. Steady state — mid-range signals produce no action
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_steady_state_mid_range_signals():
    """Signals between scale_up and scale_down thresholds → action=none, reason=steady."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        # queue=10: above scale_down(5), below scale_up(25)
        # latency=200: above scale_down(120), below scale_up(400)
        result = await _evaluate(ac, queue_depth=10, latency_p95_ms=200.0)

    assert result["action"] == "none"
    assert result["reason"] == "steady"


# ---------------------------------------------------------------------------
# 4. Cooldown blocks second consecutive scale-up
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cooldown_blocks_consecutive_scale_up():
    """Two back-to-back high-signal evaluations: first scales up, second is blocked by cooldown."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        first = await _evaluate(ac, queue_depth=100, latency_p95_ms=800.0)
        second = await _evaluate(ac, queue_depth=100, latency_p95_ms=800.0)

    assert first["action"] == "scale_up"
    assert second["action"] == "none"
    assert second["reason"] == "cooldown"
    # no change during cooldown
    assert second["replicas"] == first["replicas"]


# ---------------------------------------------------------------------------
# 5. Max replicas ceiling never exceeded
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_max_replicas_ceiling_not_exceeded():
    """Bypassing cooldown and calling scale_up 15 times never exceeds max_replicas=10."""
    from app.main import app
    from app.control_plane import runtime

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        last = {}
        for _ in range(15):
            runtime.autoscaler.last_scaled_at = 0.0   # bypass cooldown each iteration
            last = await _evaluate(ac, queue_depth=100, latency_p95_ms=800.0)

    assert last["replicas"] == runtime.autoscaler.max_replicas   # at ceiling
    assert last["replicas"] <= 10


# ---------------------------------------------------------------------------
# 6. Min replicas floor never breached
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_min_replicas_floor_not_breached():
    """At min_replicas with low signals, scale_down is suppressed; replicas stay >= min."""
    from app.main import app
    from app.control_plane import runtime

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        # Already at min_replicas=1 — low signals cannot scale further down
        result = await _evaluate(ac, queue_depth=0, latency_p95_ms=50.0)

    assert result["action"] == "none"
    assert result["replicas"] >= runtime.autoscaler.min_replicas


# ---------------------------------------------------------------------------
# 7. Scale-down after cooldown bypass
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_scale_down_after_cooldown_bypass():
    """scale_up followed by cooldown bypass → scale_down on low signals."""
    from app.main import app
    from app.control_plane import runtime

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)

        up = await _evaluate(ac, queue_depth=100, latency_p95_ms=800.0)
        assert up["action"] == "scale_up"
        assert up["replicas"] == 2

        runtime.autoscaler.last_scaled_at = 0.0   # reset cooldown timer
        down = await _evaluate(ac, queue_depth=0, latency_p95_ms=50.0)

    assert down["action"] == "scale_down"
    assert down["replicas"] == 1
    assert down["reason"] == "queue_and_latency_low"


# ---------------------------------------------------------------------------
# 8. GET /control-loop/status reflects current replica count
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_control_loop_status_reflects_replica_count():
    """After evaluate triggers scale_up, /control-loop/status shows the new replica count."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        await _evaluate(ac, queue_depth=50, latency_p95_ms=600.0)

        status = await ac.get("/mini-cloud/control-loop/status")
        assert status.status_code == 200
        data = status.json()

    assert data["autoscaler_replicas"] == 2


# ---------------------------------------------------------------------------
# 9. slow-downstream injection → control-loop tick triggers scale_up
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_tick_drives_scale_up_via_slow_downstream():
    """Injecting 500 ms downstream latency and ticking the loop produces scale_up."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)

        r = await ac.post(
            "/mini-cloud/failures/slow-downstream",
            json={"latency_ms": 500.0},
        )
        assert r.status_code == 200

        tick = await ac.post("/mini-cloud/control-loop/tick")
        assert tick.status_code == 200
        data = tick.json()

    assert data["simulated_latency_p95_ms"] == 500.0
    assert data["autoscaler"]["action"] == "scale_up"


# ---------------------------------------------------------------------------
# 10. burst-traffic injection fills the queue; tick then scales up
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_burst_traffic_fills_queue_and_tick_scales_up():
    """POST burst-traffic (10 rps × 3 s = 30 jobs) → queue_depth > 25 → tick scales up."""
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)

        burst = await ac.post(
            "/mini-cloud/failures/burst-traffic",
            json={"rps": 10, "duration_seconds": 3},
        )
        assert burst.status_code == 200
        burst_data = burst.json()
        assert burst_data["total_requests"] == 30
        assert burst_data["queue_depth_after_enqueue"] == 30

        tick = await ac.post("/mini-cloud/control-loop/tick")
        assert tick.status_code == 200
        data = tick.json()

    assert data["queue_depth"] >= 25
    assert data["autoscaler"]["action"] == "scale_up"
