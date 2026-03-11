"""In-process runtime state for mini-cloud control loops."""

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from .autoscaler import AutoscalerLoop
from .autoscaler import AutoscalerSignal
from .discovery import ServiceRegistry
from .scheduler import ControlLoopScheduler, Job, JobPayload


registry = ServiceRegistry()
scheduler = ControlLoopScheduler()
autoscaler = AutoscalerLoop()

simulated_latency_p95_ms = 50.0
last_control_loop_state: Dict[str, Any] = {
    "expired_instances": [],
    "autoscaler_decision": {"replicas": autoscaler.current_replicas, "action": "none", "reason": "init"},
}


def set_simulated_latency(latency_ms: float) -> None:
    global simulated_latency_p95_ms
    simulated_latency_p95_ms = max(1.0, float(latency_ms))


def _default_state_path() -> Path:
    # backend/app/control_plane/runtime.py -> backend/data/control_plane_state.json
    return Path(__file__).resolve().parents[2] / "data" / "control_plane_state.json"


def reset_state() -> None:
    registry._services.clear()  # noqa: SLF001
    registry._rr_counters.clear()  # noqa: SLF001
    registry._weighted_rr_state.clear()  # noqa: SLF001

    scheduler._jobs.clear()  # noqa: SLF001
    scheduler._queue.clear()  # noqa: SLF001
    scheduler._dlq.clear()  # noqa: SLF001

    autoscaler.current_replicas = autoscaler.min_replicas
    autoscaler.last_scaled_at = 0.0

    set_simulated_latency(50.0)
    last_control_loop_state["expired_instances"] = []
    last_control_loop_state["autoscaler_decision"] = {
        "replicas": autoscaler.current_replicas,
        "action": "none",
        "reason": "reset",
    }


def snapshot_state(path: Optional[str] = None) -> Dict[str, Any]:
    target = Path(path) if path else _default_state_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    payload: Dict[str, Any] = {
            "version": "control-plane-state/v1",
            "saved_at": time.time(),
            "registry": {
                    "services": {
                            service: {instance_id: instance.to_dict()
                                                                    for instance_id, instance in instances.items()}
                            for service, instances in registry._services.items()  # noqa: SLF001
                    },
                    "rr_counters": dict(registry._rr_counters),  # noqa: SLF001
            },
            "scheduler": {
                    "queue": list(scheduler._queue),  # noqa: SLF001
                    "jobs": {
                            job_id: {
                                    "id": job.id,
                                    "job_type": job.data.job_type,
                                    "payload": job.data.payload,
                                    "max_retries": job.data.max_retries,
                                    "created_at": job.created_at,
                                    "available_at": job.available_at,
                                    "attempts": job.attempts,
                                    "lease_owner": job.lease_owner,
                                    "lease_expires_at": job.lease_expires_at,
                            }
                            for job_id, job in scheduler._jobs.items()  # noqa: SLF001
                    },
                    "dlq": list(scheduler._dlq),  # noqa: SLF001
                    "lease_seconds": scheduler.lease_seconds,
                    "base_backoff_seconds": scheduler.base_backoff_seconds,
                    "max_backoff_seconds": scheduler.max_backoff_seconds,
            },
            "autoscaler": {
                    "current_replicas": autoscaler.current_replicas,
                    "last_scaled_at": autoscaler.last_scaled_at,
                    "min_replicas": autoscaler.min_replicas,
                    "max_replicas": autoscaler.max_replicas,
            },
            "simulated_latency_p95_ms": simulated_latency_p95_ms,
            "last_control_loop_state": last_control_loop_state,
    }

    with target.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return {"path": str(target), "saved_at": payload["saved_at"]}


def restore_state(path: Optional[str] = None) -> Dict[str, Any]:
    target = Path(path) if path else _default_state_path()
    if not target.exists():
        return {"restored": False, "reason": "state_file_not_found", "path": str(target)}

    with target.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    reset_state()

    registry_blob = payload.get("registry", {})
    services_blob = registry_blob.get("services", {})
    for service, instances in services_blob.items():
        registry._services[service] = {}  # noqa: SLF001
        for instance_id, instance_data in instances.items():
            instance = registry.register_instance(
                service=service,
                instance_id=instance_id,
                url=instance_data["url"],
                ttl_seconds=int(instance_data.get("ttl_seconds", 30)),
                weight=int(instance_data.get("weight", 1)),
                metadata=instance_data.get("metadata", {}),
            )
            instance.healthy = bool(instance_data.get("healthy", True))
            instance.registered_at = float(instance_data.get(
                "registered_at", instance.registered_at))
            instance.last_heartbeat = float(instance_data.get(
                "last_heartbeat", instance.last_heartbeat))
    registry._rr_counters.update({k: int(v) for k, v in registry_blob.get("rr_counters", {}).items()})  # noqa: SLF001

    scheduler_blob = payload.get("scheduler", {})
    scheduler.lease_seconds = int(scheduler_blob.get(
        "lease_seconds", scheduler.lease_seconds))
    scheduler.base_backoff_seconds = int(
        scheduler_blob.get("base_backoff_seconds",
                           scheduler.base_backoff_seconds)
    )
    scheduler.max_backoff_seconds = int(
        scheduler_blob.get("max_backoff_seconds",
                           scheduler.max_backoff_seconds)
    )
    jobs_blob = scheduler_blob.get("jobs", {})
    for job_id, job_data in jobs_blob.items():
        scheduler._jobs[job_id] = Job(  # noqa: SLF001
                id=job_data["id"],
                data=JobPayload(
                        job_type=job_data["job_type"],
                        payload=job_data.get("payload", {}),
                        max_retries=int(job_data.get("max_retries", 3)),
                ),
                created_at=float(job_data.get("created_at", time.time())),
                available_at=float(job_data.get("available_at", time.time())),
                attempts=int(job_data.get("attempts", 0)),
                lease_owner=job_data.get("lease_owner"),
                lease_expires_at=job_data.get("lease_expires_at"),
        )
    scheduler._queue.extend(list(scheduler_blob.get("queue", [])))  # noqa: SLF001
    scheduler._dlq.extend(list(scheduler_blob.get("dlq", [])))  # noqa: SLF001

    autoscaler_blob = payload.get("autoscaler", {})
    autoscaler.current_replicas = int(autoscaler_blob.get(
        "current_replicas", autoscaler.current_replicas))
    autoscaler.last_scaled_at = float(autoscaler_blob.get(
        "last_scaled_at", autoscaler.last_scaled_at))

    set_simulated_latency(
        float(payload.get("simulated_latency_p95_ms", simulated_latency_p95_ms)))
    last_control_loop_state.update(payload.get("last_control_loop_state", {}))

    return {
            "restored": True,
            "path": str(target),
            "services": sum(len(v) for v in registry._services.values()),  # noqa: SLF001
            "jobs": len(scheduler._jobs),  # noqa: SLF001
    }


def control_loop_tick() -> Dict[str, Any]:
    expired = registry.expire_instances()
    decision = autoscaler.evaluate(
        AutoscalerSignal(
            queue_depth=scheduler.queue_depth(),
            latency_p95_ms=simulated_latency_p95_ms,
        )
    )
    last_control_loop_state["expired_instances"] = expired
    last_control_loop_state["autoscaler_decision"] = decision
    return {
        "expired_instances": expired,
        "queue_depth": scheduler.queue_depth(),
        "simulated_latency_p95_ms": simulated_latency_p95_ms,
        "autoscaler": decision,
    }


async def run_control_loop(stop_event: asyncio.Event, interval_seconds: float = 5.0) -> None:
    interval = max(0.1, float(interval_seconds))
    while not stop_event.is_set():
        control_loop_tick()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval)
        except asyncio.TimeoutError:
            continue
