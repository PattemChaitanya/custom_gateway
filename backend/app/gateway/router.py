"""Gateway proxy router.

Registers the catch-all proxy endpoint:

    /gw/{api_id}/{path:path}[?env=<slug>]

Accepts all standard HTTP methods.  For every request the pipeline runs:
  1. Resolve API record (404 if not found)
  2. Check lifecycle status — draft→503, deprecated→410
  3. Resolve target URL — priority order:
       a. Mini-cloud ServiceRegistry (config.service_name)
       b. BackendPool LB (first attached pool)
       c. env deployment override (target_url_override)
       d. static config.target_url
  4. Enforce AuthPolicy   — apiKey / jwt / open
  5. Enforce RateLimit    — per-ip / per-key / global
  6. Inject connector secrets — resolve ${secret:<name>} placeholders
  7. Schema validation    — JSON Schema on request body (POST/PUT/PATCH)
  8. Proxy to upstream    — forward via shared httpx client
  9. Return upstream response with X-Gateway-* tracing headers
"""

import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connector import get_db
from app.logging_config import get_logger

from .pipeline import enforce_auth, enforce_rate_limit, enforce_schema_validation
from .proxy import proxy_request
from .resolver import (
    check_api_lifecycle,
    get_target_url,
    resolve_api,
    select_pool_backend,
    select_service_backend,
)
from .secret_injector import inject_connector_secrets

logger = get_logger("gateway.router")

router = APIRouter(prefix="/gw", tags=["gateway"])

# All standard HTTP methods handled by the single catch-all route
_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


@router.api_route(
    "/{api_id}/{path:path}",
    methods=_METHODS,
    summary="Gateway — proxy request to a registered API's upstream",
    response_description="Upstream HTTP response forwarded verbatim",
    responses={
        400: {"description": "API has no target_url configured"},
        401: {"description": "Authentication required or failed"},
        404: {"description": "API not found"},
        410: {"description": "API is deprecated"},
        429: {"description": "Rate limit exceeded"},
        503: {"description": "API not yet deployed (still in draft)"},
        502: {"description": "Upstream connection failed"},
        504: {"description": "Upstream timed out"},
    },
)
async def gateway_proxy(
    api_id: int,
    path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    env: Optional[str] = Query(
        None,
        description=(
            "Environment slug (e.g. 'production', 'staging'). "
            "When provided the gateway uses the deployment's target_url_override "
            "for that environment. Falls back to api.config.target_url."
        ),
    ),
) -> Response:
    """Route an inbound HTTP request through the gateway enforcement pipeline.

    **api_id** — ID of the registered API (retrieve with ``GET /apis/``).

    **path** — Remaining URL path appended to the API's ``target_url``.

    **env** *(optional query param)* — Environment slug. When supplied the
    gateway picks the per-environment ``target_url_override`` if one is
    configured on the deployment.

    ### Lifecycle rules
    - ``draft`` APIs return **503** — deploy first via ``POST /apis/{id}/deployments``.
    - ``deprecated`` APIs return **410 Gone**.
    - ``active`` APIs are proxied normally.

    ### Example
    ```
    GET /gw/1/users?env=staging
    ```
    Proxies to the staging deployment's override URL (or global target_url as
    fallback) for API id=1.
    """
    t_start = time.monotonic()

    # ── Step 1: Resolve API ────────────────────────────────────────────────
    api = await resolve_api(db, api_id)
    if not api:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API with id={api_id} not found",
        )

    # ── Step 2: Lifecycle check ────────────────────────────────────────────
    blocked = check_api_lifecycle(api)
    if blocked:
        http_code, message = blocked
        raise HTTPException(status_code=http_code, detail=message)

    # ── Step 3: Resolve upstream target URL ───────────────────────────────
    # Priority: mini-cloud registry > backend pool > env override > static url
    _svc_url = select_service_backend(api)        # (a) mini-cloud
    _pool_url = select_pool_backend(api)          # (b) BackendPool LB
    # (c/d) env override / config
    _static_url = get_target_url(api, env_slug=env)

    target_url = _svc_url or _pool_url or _static_url
    if not target_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"API '{api.name}' (id={api_id}) has no target URL configured. "
                "Options: set config.service_name (mini-cloud), attach a BackendPool, "
                "set config.target_url, or provide a target_url_override on a deployment."
            ),
        )
    _url_source = "mini-cloud" if _svc_url else (
        "pool" if _pool_url else "static")

    # ── Step 4: Auth enforcement ───────────────────────────────────────────
    await enforce_auth(api, request, db)

    # ── Step 5: Rate-limit enforcement ────────────────────────────────────
    await enforce_rate_limit(api, request)

    # ── Step 6: Connector secret injection ────────────────────────────────
    # Resolve ${secret:<name>} placeholders in the connector config.
    # - extra_headers are merged into the upstream request (auth tokens, etc.)
    # - connector_url overrides target_url when the connector specifies one
    extra_headers, connector_url = await inject_connector_secrets(api, db)
    if connector_url:
        target_url = connector_url

    # ── Step 7: Schema validation ──────────────────────────────────────────
    # Validate POST/PUT/PATCH request bodies against the first API schema (if any).
    await enforce_schema_validation(api, request)

    # ── Step 8: Proxy ─────────────────────────────────────────────────────
    logger.info(
        "[GW] api=%s(%s) env=%s src=%s %s /%s → %s",
        api.name,
        api_id,
        env or "default",
        _url_source,
        request.method,
        path,
        target_url,
    )

    response = await proxy_request(request, target_url, path, api_id, extra_headers=extra_headers)

    # Inject gateway tracing headers
    elapsed_ms = int((time.monotonic() - t_start) * 1000)
    response.headers["x-gateway-latency-ms"] = str(elapsed_ms)
    response.headers["x-gateway-url-source"] = _url_source
    if env:
        response.headers["x-gateway-env"] = env

    return response
