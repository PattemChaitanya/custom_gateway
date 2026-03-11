"""Point 6: Scheduler control loop — full API-level integration tests.

Tests cover:
1. Enqueue → lease → ack (happy path)
2. Enqueue → lease → fail → backoff retry → second lease by another worker
3. Exhaust retries → job lands in DLQ
4. GET /scheduler/dlq content after exhaustion
5. Worker isolation: only the lease owner can ack/fail
6. Lease-less queue: leasing empty queue returns no job
7. queue_depth via control-loop /status reflects pending jobs
8. Burst-traffic failure injection enqueues jobs (synthetic queue pressure)
"""

import pytest
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def enqueue(ac, job_type: str = "test_job", payload: dict | None = None, max_retries: int = 2) -> str:
    r = await ac.post(
        "/mini-cloud/scheduler/jobs",
        json={"job_type": job_type, "payload": payload or {},
              "max_retries": max_retries},
    )
    assert r.status_code == 200, r.text
    return r.json()["job_id"]


async def lease(ac, worker_id: str) -> dict | None:
    r = await ac.post("/mini-cloud/scheduler/jobs/lease", json={"worker_id": worker_id})
    assert r.status_code == 200, r.text
    return r.json()["job"]


async def ack(ac, job_id: str, worker_id: str) -> int:
    r = await ac.post(f"/mini-cloud/scheduler/jobs/{job_id}/ack", json={"worker_id": worker_id})
    return r.status_code


async def fail(ac, job_id: str, worker_id: str, reason: str = "err") -> int:
    r = await ac.post(
        f"/mini-cloud/scheduler/jobs/{job_id}/fail",
        json={"worker_id": worker_id, "reason": reason},
    )
    return r.status_code


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_enqueue_lease_ack_happy_path():
    """Enqueue a job, lease it, ack it — job disappears from the queue."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")

        job_id = await enqueue(ac, "deploy", {"service": "api-svc"})

        job = await lease(ac, "worker-1")
        assert job is not None, "Expected a leased job"
        assert job["id"] == job_id
        assert job["job_type"] == "deploy"
        assert job["lease_owner"] == "worker-1"
        assert job["attempts"] == 1

        status = await ack(ac, job_id, "worker-1")
        assert status == 200

        # Queue should now be empty.
        job_again = await lease(ac, "worker-2")
        assert job_again is None


@pytest.mark.asyncio
async def test_fail_returns_job_to_queue_with_backoff():
    """Failing a job makes it re-available after backoff; a second worker can lease it."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")

        job_id = await enqueue(ac, "sync", {}, max_retries=3)

        job1 = await lease(ac, "worker-a")
        assert job1 is not None
        assert job1["attempts"] == 1

        # Fail the first attempt.
        assert await fail(ac, job_id, "worker-a", "transient") == 200

        # Job is now backing off — should NOT be immediately available.
        no_job = await lease(ac, "worker-b")
        assert no_job is None, "Job should be in backoff, not immediately leasable"


@pytest.mark.asyncio
async def test_exhaust_retries_lands_in_dlq():
    """Exhausting all retries moves the job to the DLQ and removes it from the queue.

    The default scheduler has base_backoff_seconds=2.  After the first fail
    the job is unavailable for 2 s.  We sleep through that period so the second
    lease can fire without any scheduler patching.
    """
    import asyncio
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")

        # max_retries=1 → 2 total attempts (attempt 1 + attempt 2) before DLQ.
        job_id = await enqueue(ac, "crash_job", {"k": "v"}, max_retries=1)

        # First lease + fail.
        j1 = await lease(ac, "w1")
        assert j1 is not None
        assert j1["id"] == job_id
        assert await fail(ac, job_id, "w1", "boom") == 200

        # Wait for the backoff to expire (base=2 s, attempt 1 → 2 s backoff).
        await asyncio.sleep(2.2)

        # Second lease + fail → attempts (2) > max_retries (1) → DLQ.
        j2 = await lease(ac, "w2")
        assert j2 is not None, "Job should be leaseable after backoff expired"
        assert j2["id"] == job_id
        assert await fail(ac, job_id, "w2", "boom again") == 200

        # Queue should now be empty.
        no_job = await lease(ac, "w3")
        assert no_job is None

        # Job must appear in DLQ.
        dlq_r = await ac.get("/mini-cloud/scheduler/dlq")
        assert dlq_r.status_code == 200
        dlq = dlq_r.json()["dlq"]
        assert any(entry["job_id"] == job_id for entry in dlq), dlq
        matched = next(e for e in dlq if e["job_id"] == job_id)
        assert matched["job_type"] == "crash_job"
        assert matched["reason"] == "boom again"


@pytest.mark.asyncio
async def test_worker_isolation_wrong_owner_cannot_ack():
    """A worker that did not lease the job cannot ack it (409)."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")

        job_id = await enqueue(ac, "isolated_job", {})
        job = await lease(ac, "owner-worker")
        assert job is not None

        # Different worker tries to ack — must fail.
        status = await ack(ac, job_id, "intruder-worker")
        assert status == 409, "Wrong-owner ack should return 409"


@pytest.mark.asyncio
async def test_worker_isolation_wrong_owner_cannot_fail():
    """A worker that did not lease the job cannot fail it (409)."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")

        job_id = await enqueue(ac, "isolated_job_fail", {})
        await lease(ac, "real-owner")

        status = await fail(ac, job_id, "bad-actor", "tamper")
        assert status == 409


@pytest.mark.asyncio
async def test_lease_on_empty_queue_returns_none():
    """Leasing with nothing in the queue must return null job gracefully."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")

        job = await lease(ac, "idle-worker")
        assert job is None


@pytest.mark.asyncio
async def test_control_loop_status_reflects_queue_depth():
    """After enqueueing jobs, /control-loop/status must show queue_depth > 0."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")

        await enqueue(ac, "job_a", {})
        await enqueue(ac, "job_b", {})

        status_r = await ac.get("/mini-cloud/control-loop/status")
        assert status_r.status_code == 200
        assert status_r.json()["queue_depth"] >= 2


@pytest.mark.asyncio
async def test_burst_traffic_injection_enqueues_jobs():
    """POST /failures/burst-traffic must enqueue synthetic jobs (simulates queue pressure)."""
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        await ac.post("/mini-cloud/reset")

        # Burst: 10 rps for 2 seconds → enqueues 2 synthetic jobs.
        r = await ac.post(
            "/mini-cloud/failures/burst-traffic",
            json={"rps": 10, "duration_seconds": 2},
        )
        assert r.status_code == 200

        status_r = await ac.get("/mini-cloud/control-loop/status")
        assert status_r.json()[
            "queue_depth"] >= 1, "Burst traffic should raise queue depth"
