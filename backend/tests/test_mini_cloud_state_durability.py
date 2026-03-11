"""Point 9 – State Durability (API-level)

Tests that verify the snapshot/restore cycle via:
  POST /mini-cloud/control-loop/snapshot?path=<file>
  POST /mini-cloud/control-loop/restore?path=<file>
  POST /mini-cloud/reset
  GET  /mini-cloud/control-loop/status

Each test seeds state via the mini-cloud API, snapshots it to a tmp file,
corrupts/resets in-memory state, then restores and asserts full fidelity.
"""

import json
import pytest
from httpx import AsyncClient, ASGITransport

BASE = "http://testserver"


async def _reset(ac: AsyncClient) -> None:
    r = await ac.post("/mini-cloud/reset")
    assert r.status_code == 200


async def _register(ac: AsyncClient, service: str, instance_id: str, weight: int = 1) -> None:
    r = await ac.post(
        f"/mini-cloud/services/{service}/instances",
        json={"instance_id": instance_id, "url": f"http://{instance_id}",
              "ttl_seconds": 120, "weight": weight},
    )
    assert r.status_code == 200


async def _enqueue(ac: AsyncClient, job_type: str = "task", max_retries: int = 3) -> str:
    r = await ac.post("/mini-cloud/scheduler/jobs", json={"job_type": job_type, "payload": {}, "max_retries": max_retries})
    assert r.status_code == 200
    return r.json()["job_id"]


async def _snapshot(ac: AsyncClient, path: str) -> dict:
    r = await ac.post("/mini-cloud/control-loop/snapshot", params={"path": path})
    assert r.status_code == 200
    return r.json()


async def _restore(ac: AsyncClient, path: str) -> dict:
    r = await ac.post("/mini-cloud/control-loop/restore", params={"path": path})
    assert r.status_code == 200
    return r.json()


# ---------------------------------------------------------------------------
# 1. Snapshot creates a valid JSON file
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_snapshot_api_creates_file(tmp_path):
    """snapshot API writes a versioned JSON file to the given path."""
    from app.main import app

    state_file = str(tmp_path / "cp.json")
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        result = await _snapshot(ac, state_file)

    assert result["path"] == state_file
    raw = json.loads(open(state_file, encoding="utf-8").read())
    assert raw["version"] == "control-plane-state/v1"
    assert "registry" in raw
    assert "scheduler" in raw
    assert "autoscaler" in raw


# ---------------------------------------------------------------------------
# 2. Restore recovers the service registry
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_restore_api_recovers_registry(tmp_path):
    """All registered instances are preserved across snapshot → reset → restore."""
    from app.main import app

    state_file = str(tmp_path / "cp.json")
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        await _register(ac, "alpha", "a-1", weight=2)
        await _register(ac, "alpha", "a-2", weight=4)

        await _snapshot(ac, state_file)
        await _reset(ac)   # wipe all state

        result = await _restore(ac, state_file)
        assert result["restored"] is True

        instances = await ac.get("/mini-cloud/services/alpha/instances")
        assert instances.status_code == 200
        ids = {i["instance_id"] for i in instances.json()}

    assert ids == {"a-1", "a-2"}


# ---------------------------------------------------------------------------
# 3. Restore recovers queued scheduler jobs
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_restore_api_recovers_scheduler_queue(tmp_path):
    """Unprocessed queued jobs survive a snapshot → reset → restore cycle."""
    from app.main import app

    state_file = str(tmp_path / "cp.json")
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        await _enqueue(ac, "reconcile")
        await _enqueue(ac, "reconcile")
        await _enqueue(ac, "reconcile")

        status_before = await ac.get("/mini-cloud/control-loop/status")
        depth_before = status_before.json()["queue_depth"]

        await _snapshot(ac, state_file)
        await _reset(ac)

        # Queue depth is 0 after reset
        status_wiped = await ac.get("/mini-cloud/control-loop/status")
        assert status_wiped.json()["queue_depth"] == 0

        await _restore(ac, state_file)

        status_after = await ac.get("/mini-cloud/control-loop/status")
        depth_after = status_after.json()["queue_depth"]

    assert depth_before == 3
    assert depth_after == 3


# ---------------------------------------------------------------------------
# 4. Restore recovers DLQ entries
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_restore_api_recovers_dlq(tmp_path):
    """Jobs that exhaust retries and land in DLQ survive snapshot/restore."""
    from app.main import app

    state_file = str(tmp_path / "cp.json")
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)

        # Enqueue job with max_retries=0 → fails immediately to DLQ
        job_id = await _enqueue(ac, "doomed", max_retries=0)
        leased = await ac.post("/mini-cloud/scheduler/jobs/lease", json={"worker_id": "w1"})
        assert leased.json()["job"] is not None
        # Fail → goes straight to DLQ (attempts=1 > max_retries=0)
        await ac.post(f"/mini-cloud/scheduler/jobs/{job_id}/fail", json={"worker_id": "w1", "reason": "fatal"})

        dlq_before = await ac.get("/mini-cloud/scheduler/dlq")
        assert len(dlq_before.json()["dlq"]) == 1

        await _snapshot(ac, state_file)
        await _reset(ac)

        dlq_wiped = await ac.get("/mini-cloud/scheduler/dlq")
        assert dlq_wiped.json()["dlq"] == []

        await _restore(ac, state_file)

        dlq_after = await ac.get("/mini-cloud/scheduler/dlq")

    assert len(dlq_after.json()["dlq"]) == 1
    assert dlq_after.json()["dlq"][0]["job_id"] == job_id


# ---------------------------------------------------------------------------
# 5. Restore recovers autoscaler replica count
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_restore_api_recovers_autoscaler_replicas(tmp_path):
    """Autoscaler current_replicas is preserved across snapshot → reset → restore."""
    from app.main import app
    from app.control_plane import runtime

    state_file = str(tmp_path / "cp.json")
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)

        # Scale up to 5 replicas by bypassing cooldown each time
        for _ in range(4):
            runtime.autoscaler.last_scaled_at = 0.0
            await ac.post("/mini-cloud/autoscaler/evaluate", json={"queue_depth": 100, "latency_p95_ms": 800})

        status_before = await ac.get("/mini-cloud/control-loop/status")
        replicas_before = status_before.json()["autoscaler_replicas"]

        await _snapshot(ac, state_file)
        await _reset(ac)

        status_wiped = await ac.get("/mini-cloud/control-loop/status")
        assert status_wiped.json()["autoscaler_replicas"] == 1

        await _restore(ac, state_file)
        status_after = await ac.get("/mini-cloud/control-loop/status")

    assert replicas_before == 5
    assert status_after.json()["autoscaler_replicas"] == 5


# ---------------------------------------------------------------------------
# 6. Restore recovers simulated latency
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_restore_api_recovers_simulated_latency(tmp_path):
    """simulated_latency_p95_ms is preserved across snapshot → reset → restore."""
    from app.main import app

    state_file = str(tmp_path / "cp.json")
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        await _reset(ac)
        await ac.post("/mini-cloud/failures/slow-downstream", json={"latency_ms": 650.0})

        await _snapshot(ac, state_file)
        await _reset(ac)

        status_wiped = await ac.get("/mini-cloud/control-loop/status")
        # reset default
        assert status_wiped.json()["simulated_latency_p95_ms"] == 50.0

        await _restore(ac, state_file)
        status_after = await ac.get("/mini-cloud/control-loop/status")

    assert status_after.json()["simulated_latency_p95_ms"] == 650.0


# ---------------------------------------------------------------------------
# 7. Restore with missing file returns restored=false
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_restore_missing_file_returns_false(tmp_path):
    """Restoring from a non-existent path returns restored=false, no exception."""
    from app.main import app

    no_such_file = str(tmp_path / "does_not_exist.json")
    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        r = await ac.post("/mini-cloud/control-loop/restore", params={"path": no_such_file})
        assert r.status_code == 200
        data = r.json()

    assert data["restored"] is False
    assert "state_file_not_found" in data.get("reason", "")


# ---------------------------------------------------------------------------
# 8. Reset wipes all dimensions completely
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_reset_wipes_all_dimensions():
    """POST /reset returns all dimensions to their cold-start defaults."""
    from app.main import app
    from app.control_plane import runtime

    async with AsyncClient(transport=ASGITransport(app=app), base_url=BASE) as ac:
        # Seed everything
        await _reset(ac)
        await _register(ac, "wipe-svc", "w-1")
        await _enqueue(ac, "task_to_wipe")
        runtime.autoscaler.last_scaled_at = 0.0
        await ac.post("/mini-cloud/autoscaler/evaluate", json={"queue_depth": 100, "latency_p95_ms": 800})
        await ac.post("/mini-cloud/failures/slow-downstream", json={"latency_ms": 999.0})

        # Verify state is non-default before reset
        status_before = await ac.get("/mini-cloud/control-loop/status")
        d = status_before.json()
        assert d["queue_depth"] == 1
        assert d["autoscaler_replicas"] == 2
        assert d["simulated_latency_p95_ms"] == 999.0

        # Reset
        await _reset(ac)

        # Verify everything is wiped
        status_after = await ac.get("/mini-cloud/control-loop/status")
        s = status_after.json()
        instances = await ac.get("/mini-cloud/services/wipe-svc/instances")

    assert s["queue_depth"] == 0
    assert s["autoscaler_replicas"] == 1
    assert s["simulated_latency_p95_ms"] == 50.0
    assert instances.json() == []
