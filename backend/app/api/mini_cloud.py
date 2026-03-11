from __future__ import annotations

import uuid
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.control_plane.contracts import PLATFORM_CONTRACT
from app.control_plane.failure_injection import (
    inject_burst_traffic,
    inject_slow_downstream,
    inject_stale_heartbeat,
    inject_worker_crash,
)
from app.control_plane.policies import (
    PolicyConfig,
    load_policy_config,
    match_route_policy,
    validate_policy_config,
    write_policy_config,
)
from app.control_plane.runtime import (
    autoscaler,
    control_loop_tick,
    last_control_loop_state,
    registry,
    restore_state,
    reset_state,
    scheduler,
    set_simulated_latency,
    snapshot_state,
)
from app.control_plane import runtime
from app.control_plane.autoscaler import AutoscalerSignal
from app.metrics.prometheus import MetricsCollector


router = APIRouter(prefix="/mini-cloud", tags=["mini-cloud"])
_rate_window_cache: Dict[str, list[float]] = {}


class RegisterInstanceRequest(BaseModel):
    instance_id: str
    url: str
    ttl_seconds: int = Field(default=30, ge=1)
    weight: int = Field(default=1, ge=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HeartbeatRequest(BaseModel):
    healthy: bool = True
    health_status: Optional[str] = None


class HealthStatusRequest(BaseModel):
    health_status: str = Field(default="healthy")


class RouteRequest(BaseModel):
    path: str = Field(default="/")
    strategy: Optional[str] = None
    auth_token: Optional[str] = None
    api_key: Optional[str] = None
    scopes: list[str] = Field(default_factory=list)
    client_id: str = "anonymous"


class EnqueueJobRequest(BaseModel):
    job_type: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    max_retries: int = Field(default=3, ge=0)


class LeaseRequest(BaseModel):
    worker_id: str


class FailJobRequest(BaseModel):
    worker_id: str
    reason: str = "unknown_error"


class AckJobRequest(BaseModel):
    worker_id: str


class AutoscaleRequest(BaseModel):
    queue_depth: int = Field(ge=0)
    latency_p95_ms: float = Field(ge=0)


class SlowDownstreamRequest(BaseModel):
    latency_ms: float = Field(ge=1)


class BurstTrafficRequest(BaseModel):
    rps: int = Field(ge=1)
    duration_seconds: int = Field(ge=1)


def _enforce_auth(mode: str, scopes_required: list[str], payload: RouteRequest) -> None:
    if mode == "none":
        return

    if mode == "api_key":
        if not payload.api_key:
            raise HTTPException(status_code=401, detail="api key required")
        return

    if mode == "jwt":
        if not payload.auth_token:
            raise HTTPException(status_code=401, detail="auth token required")
        missing_scopes = [
            scope for scope in scopes_required if scope not in payload.scopes]
        if missing_scopes:
            raise HTTPException(
                status_code=403, detail=f"missing scopes: {','.join(missing_scopes)}")
        return

    raise HTTPException(
        status_code=400, detail=f"unsupported auth mode: {mode}")


def _enforce_rate_limit(policy_name: str, limit: int, window_seconds: int, subject: str) -> None:
    cache_key = f"{policy_name}:{subject}"
    now = time.time()
    cutoff = now - max(1, window_seconds)
    events = [ts for ts in _rate_window_cache.get(
        cache_key, []) if ts >= cutoff]
    if len(events) >= max(1, limit):
        raise HTTPException(
            status_code=429, detail="policy rate limit exceeded")
    events.append(now)
    _rate_window_cache[cache_key] = events


@router.get("/contract")
async def get_contract():
    return PLATFORM_CONTRACT.model_dump()


@router.get("/policies")
async def get_policies(path: Optional[str] = Query(default=None)):
    return load_policy_config(path).model_dump()


@router.post("/policies/validate")
async def validate_policies(config: PolicyConfig):
    """Validate a policy config payload without applying it.

    Returns 200 with ``{"valid": true}`` when the config is internally
    consistent, or 422 with a list of cross-reference errors when it is not.
    """
    errors = validate_policy_config(config)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})
    return {"valid": True, "version": config.version}


@router.put("/policies")
async def update_policies(config: PolicyConfig, path: Optional[str] = Query(default=None)):
    """Validate and atomically write a new policy config to disk.

    Subsequent route calls pick up the new policy without a restart because
    ``load_policy_config`` reads from disk on every request.
    Returns 422 when the config has cross-reference errors.
    """
    errors = validate_policy_config(config)
    if errors:
        raise HTTPException(status_code=422, detail={"errors": errors})
    target = write_policy_config(config, path)
    return {"written": True, "path": str(target), "version": config.version}


@router.post("/services/{service}/instances")
async def register_instance(service: str, payload: RegisterInstanceRequest):
    instance = registry.register_instance(
        service=service,
        instance_id=payload.instance_id,
        url=payload.url,
        ttl_seconds=payload.ttl_seconds,
        weight=payload.weight,
        metadata=payload.metadata,
    )
    return instance.to_dict()


@router.post("/services/{service}/instances/{instance_id}/heartbeat")
async def heartbeat(service: str, instance_id: str, payload: HeartbeatRequest):
    try:
        instance = registry.heartbeat(
            service,
            instance_id,
            healthy=payload.healthy,
            health_status=payload.health_status,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not instance:
        raise HTTPException(status_code=404, detail="instance not found")
    return instance.to_dict()


@router.post("/services/{service}/instances/{instance_id}/health-status")
async def set_health_status(service: str, instance_id: str, payload: HealthStatusRequest):
    try:
        ok = registry.set_health_status(
            service, instance_id, payload.health_status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(status_code=404, detail="instance not found")
    instance = registry.list_instances(service)
    selected = next(
        (i for i in instance if i.instance_id == instance_id), None)
    if not selected:
        raise HTTPException(status_code=404, detail="instance not found")
    return selected.to_dict()


@router.get("/services/{service}/instances")
async def list_instances(service: str, healthy_only: bool = Query(default=False)):
    registry.expire_instances()
    return [i.to_dict() for i in registry.list_instances(service, healthy_only=healthy_only)]


@router.post("/services/{service}/route")
async def route_request(service: str, payload: RouteRequest, policy_path: Optional[str] = Query(default=None)):
    request_id = str(uuid.uuid4())
    registry.expire_instances()

    policy_cfg = load_policy_config(policy_path)
    route_policy = match_route_policy(
        policy_cfg, service=service, path=payload.path)
    strategy = payload.strategy or (
        route_policy.strategy if route_policy else "round_robin")

    if route_policy:
        auth_cfg = policy_cfg.auth.get(route_policy.auth_policy)
        if auth_cfg is None:
            raise HTTPException(
                status_code=500, detail=f"auth policy not found: {route_policy.auth_policy}")

        rate_cfg = policy_cfg.rate_limits.get(route_policy.rate_limit_policy)
        if rate_cfg is None:
            raise HTTPException(
                status_code=500, detail=f"rate-limit policy not found: {route_policy.rate_limit_policy}")

        try:
            _enforce_auth(auth_cfg.mode, auth_cfg.scopes, payload)
            _enforce_rate_limit(
                policy_name=rate_cfg.name,
                limit=rate_cfg.limit,
                window_seconds=rate_cfg.window_seconds,
                subject=payload.client_id,
            )
        except HTTPException as exc:
            MetricsCollector.record_route_error(
                service=service, error_type=f"policy_{exc.status_code}")
            MetricsCollector.record_route(
                service=service,
                strategy=strategy,
                status="error",
                duration_seconds=0.0,
            )
            raise

    try:
        selected = registry.select_instance(service, strategy=strategy)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not selected:
        MetricsCollector.record_route_error(
            service=service, error_type="no_healthy_instance")
        MetricsCollector.record_route(
            service=service,
            strategy=strategy,
            status="error",
            duration_seconds=0.0,
        )
        raise HTTPException(
            status_code=503, detail="no healthy instance available")

    MetricsCollector.record_route(
        service=service,
        strategy=strategy,
        status="ok",
        duration_seconds=0.0,
    )
    return {
        "request_id": request_id,
        "service": service,
        "target": selected.to_dict(),
        "applied_route_policy": route_policy.model_dump() if route_policy else None,
    }


@router.post("/scheduler/jobs")
async def enqueue_job(payload: EnqueueJobRequest):
    job_id = scheduler.enqueue(
        payload.job_type, payload.payload, max_retries=payload.max_retries)
    return {"job_id": job_id}


@router.post("/scheduler/jobs/lease")
async def lease_job(payload: LeaseRequest):
    job = scheduler.lease_next(payload.worker_id)
    if job is None:
        return {"job": None}
    return {"job": job.__dict__}


@router.post("/scheduler/jobs/{job_id}/ack")
async def ack_job(job_id: str, payload: AckJobRequest):
    ok = scheduler.ack(job_id, payload.worker_id)
    if not ok:
        raise HTTPException(status_code=409, detail="cannot ack job")
    return {"status": "acked"}


@router.post("/scheduler/jobs/{job_id}/fail")
async def fail_job(job_id: str, payload: FailJobRequest):
    ok = scheduler.fail(job_id, payload.worker_id, reason=payload.reason)
    if not ok:
        raise HTTPException(status_code=409, detail="cannot fail job")
    return {"status": "failed"}


@router.get("/scheduler/dlq")
async def get_dlq():
    return {"dlq": scheduler.dead_letter_queue()}


@router.post("/autoscaler/evaluate")
async def evaluate_autoscaler(payload: AutoscaleRequest):
    decision = autoscaler.evaluate(
        AutoscalerSignal(
            queue_depth=payload.queue_depth,
            latency_p95_ms=payload.latency_p95_ms,
        )
    )
    return decision


@router.post("/failures/stale-heartbeat/{service}/{instance_id}")
async def stale_heartbeat(service: str, instance_id: str, seconds_ago: int = Query(default=300, ge=1)):
    ok = inject_stale_heartbeat(
        registry, service, instance_id, seconds_ago=seconds_ago)
    if not ok:
        raise HTTPException(status_code=404, detail="instance not found")
    return {"status": "injected", "failure": "stale_heartbeat"}


@router.post("/failures/worker-crash/{job_id}")
async def worker_crash(job_id: str):
    ok = inject_worker_crash(scheduler, job_id)
    if not ok:
        raise HTTPException(status_code=404, detail="job not found")
    return {"status": "injected", "failure": "worker_crash"}


@router.post("/failures/slow-downstream")
async def slow_downstream(payload: SlowDownstreamRequest):
    set_simulated_latency(payload.latency_ms)
    return inject_slow_downstream(payload.latency_ms)


@router.post("/failures/burst-traffic")
async def burst_traffic(payload: BurstTrafficRequest):
    burst = inject_burst_traffic(payload.rps, payload.duration_seconds)
    for _ in range(burst["total_requests"]):
        scheduler.enqueue("burst_traffic", {
                          "service": "simulated"}, max_retries=1)
    return {**burst, "queue_depth_after_enqueue": scheduler.queue_depth()}


@router.post("/control-loop/tick")
async def tick_control_loop():
    return control_loop_tick()


@router.get("/control-loop/status")
async def get_control_loop_status():
    return {
        "queue_depth": scheduler.queue_depth(),
        "simulated_latency_p95_ms": runtime.simulated_latency_p95_ms,
        "autoscaler_replicas": autoscaler.current_replicas,
        "last_state": last_control_loop_state,
    }


@router.post("/reset")
async def reset_mini_cloud_state():
    reset_state()
    _rate_window_cache.clear()
    return {"status": "reset"}


@router.post("/control-loop/snapshot")
async def snapshot_control_plane(path: Optional[str] = Query(default=None)):
    return snapshot_state(path)


@router.post("/control-loop/restore")
async def restore_control_plane(path: Optional[str] = Query(default=None)):
    return restore_state(path)


# ---------------------------------------------------------------------------
# Gateway ↔ Mini-Cloud link endpoints (Phase 9)
# ---------------------------------------------------------------------------

@router.get(
    "/services/{service}/resolve",
    summary="Preview which instance the gateway would route to",
)
async def resolve_service(
    service: str,
    strategy: str = Query(default="round_robin",
                          description="Routing strategy"),
):
    """Return the instance the gateway would select right now for *service*.

    Useful for debugging routing decisions before traffic hits the gateway.
    Does not consume a slot (no connection counting side-effects).
    """
    registry.expire_instances()
    try:
        instance = registry.select_instance(service, strategy=strategy)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not instance:
        raise HTTPException(
            status_code=503,
            detail=f"No healthy instance available for service '{service}'",
        )
    return {
        "service": service,
        "strategy": strategy,
        "selected": instance.to_dict(),
    }


class LinkAPIRequest(BaseModel):
    routing_strategy: str = Field(
        default="round_robin",
        description="Routing strategy the gateway uses when selecting an instance",
    )


@router.post(
    "/services/{service}/link-api/{api_id}",
    summary="Link a registered API to a mini-cloud service",
)
async def link_api_to_service(
    service: str,
    api_id: int,
    payload: LinkAPIRequest,
):
    """Write ``service_name`` (and optionally ``routing_strategy``) into an
    API's ``config`` column so the gateway resolves its upstream from the
    mini-cloud ``ServiceRegistry`` instead of a static URL.

    After calling this endpoint, every request to ``/gw/{api_id}/...`` will
    automatically pick a healthy instance of *service* from the registry.

    To revert to static routing, remove ``service_name`` from the API's config
    via ``PUT /apis/{api_id}``.
    """
    from sqlalchemy import select as sa_select
    from app.db.connector import get_db
    from app.db.models import API

    # Validate service exists (optional — allow pre-registration)
    instances = registry.list_instances(service)

    # We need a DB session; import async generator and collect one session
    db_gen = get_db()
    db = await db_gen.__anext__()
    try:
        result = await db.execute(sa_select(API).where(API.id == api_id))
        api = result.scalar_one_or_none()
        if not api:
            raise HTTPException(
                status_code=404, detail=f"API {api_id} not found"
            )

        config = dict(api.config or {})
        config["service_name"] = service
        config["routing_strategy"] = payload.routing_strategy
        api.config = config
        await db.commit()
        await db.refresh(api)

        return {
            "api_id": api_id,
            "service_name": service,
            "routing_strategy": payload.routing_strategy,
            "known_instances": len(instances),
            "message": (
                f"Gateway will now route /gw/{api_id}/... to healthy instances "
                f"of service '{service}' via {payload.routing_strategy}."
            ),
        }
    finally:
        await db_gen.aclose()


@router.delete(
    "/services/{service}/link-api/{api_id}",
    summary="Unlink a mini-cloud service from a registered API",
)
async def unlink_api_from_service(service: str, api_id: int):
    """Remove ``service_name`` from the API's config, reverting to static URL routing."""
    from sqlalchemy import select as sa_select
    from app.db.connector import get_db
    from app.db.models import API

    db_gen = get_db()
    db = await db_gen.__anext__()
    try:
        result = await db.execute(sa_select(API).where(API.id == api_id))
        api = result.scalar_one_or_none()
        if not api:
            raise HTTPException(
                status_code=404, detail=f"API {api_id} not found")

        config = dict(api.config or {})
        removed = config.pop("service_name", None)
        config.pop("routing_strategy", None)
        api.config = config
        await db.commit()

        return {
            "api_id": api_id,
            "unlinked_service": removed,
            "message": "Gateway reverted to static URL routing for this API.",
        }
    finally:
        await db_gen.aclose()
