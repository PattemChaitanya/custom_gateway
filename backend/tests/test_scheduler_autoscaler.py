import time

from app.control_plane.autoscaler import AutoscalerLoop, AutoscalerSignal
from app.control_plane.scheduler import ControlLoopScheduler


def test_scheduler_retry_and_dead_letter_queue():
    scheduler = ControlLoopScheduler(
        lease_seconds=1, base_backoff_seconds=1, max_backoff_seconds=2)
    job_id = scheduler.enqueue(
        "sync_state", {"service": "orders"}, max_retries=1)

    first = scheduler.lease_next("worker-a")
    assert first is not None
    assert first.id == job_id

    assert scheduler.fail(job_id, "worker-a", "temporary") is True

    time.sleep(1.1)
    second = scheduler.lease_next("worker-b")
    assert second is not None
    assert second.id == job_id

    assert scheduler.fail(job_id, "worker-b", "permanent") is True
    dlq = scheduler.dead_letter_queue()

    assert len(dlq) == 1
    assert dlq[0]["job_id"] == job_id


def test_autoscaler_respects_bounds_and_cooldown():
    loop = AutoscalerLoop(min_replicas=2, max_replicas=3, cooldown_seconds=30)

    result1 = loop.evaluate(AutoscalerSignal(
        queue_depth=50, latency_p95_ms=800), now=100.0)
    assert result1["action"] == "scale_up"
    assert result1["replicas"] == 3

    result2 = loop.evaluate(AutoscalerSignal(
        queue_depth=80, latency_p95_ms=900), now=110.0)
    assert result2["action"] == "none"
    assert result2["reason"] == "cooldown"
    assert result2["replicas"] == 3

    result3 = loop.evaluate(AutoscalerSignal(
        queue_depth=0, latency_p95_ms=10), now=140.0)
    assert result3["action"] == "scale_down"
    assert result3["replicas"] == 2
