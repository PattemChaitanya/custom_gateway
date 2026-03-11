"""Failure injection helpers for chaos-style control plane tests."""

from __future__ import annotations

import time
from typing import Dict

from .discovery import ServiceRegistry
from .scheduler import ControlLoopScheduler


def inject_stale_heartbeat(registry: ServiceRegistry, service: str, instance_id: str, seconds_ago: int = 300) -> bool:
    instance = registry._services.get(service, {}).get(instance_id)  # noqa: SLF001
    if not instance:
        return False
    instance.last_heartbeat = time.time() - max(1, seconds_ago)
    return True


def inject_worker_crash(scheduler: ControlLoopScheduler, job_id: str) -> bool:
    job = scheduler._jobs.get(job_id)  # noqa: SLF001
    if not job:
        return False
    job.lease_expires_at = time.time() - 1
    return True


def inject_slow_downstream(latency_ms: float) -> Dict[str, float]:
    return {"simulated_latency_ms": max(1.0, latency_ms)}


def inject_burst_traffic(rps: int, duration_seconds: int) -> Dict[str, int]:
    return {
        "rps": max(1, rps),
        "duration_seconds": max(1, duration_seconds),
        "total_requests": max(1, rps) * max(1, duration_seconds),
    }
