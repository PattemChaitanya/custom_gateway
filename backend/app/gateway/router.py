"""Gateway proxy router.

Registers two catch-all proxy endpoints:

    /gw/{account_slug}/{api_id}/{path:path}[?env=<slug>]   ← account-scoped (Phase 3)
    /gw/{api_id}/{path:path}[?env=<slug>]                   ← legacy unscoped route

The account-scoped route is the preferred form.  It resolves the Account by
slug first; if the account is not found or is not active the gateway returns
404.  The API lookup is then scoped to that account — an api_id that exists
under a different account also returns 404 (no cross-tenant info leakage).

The legacy route performs no account check and is preserved for backward
compatibility.  It is recommended to migrate all clients to the scoped form.

Both routes share the same enforcement pipeline:
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
from app.db.models import Account
from app.logging_config import get_logger

from .metering import check_quota, record_request
from .pipeline import enforce_api_key_rate_limit, enforce_auth, enforce_body_size, enforce_rate_limit, enforce_schema_validation
from .proxy import proxy_request
from .resolver import (
    EnvironmentNotDeployedError,
    check_api_lifecycle,
    get_target_url,
    resolve_account_by_slug,
    resolve_api,
    select_pool_backend,
    select_service_backend,
)
from .secret_injector import inject_connector_secrets

logger = get_logger("gateway.router")

router = APIRouter(prefix="/gw", tags=["gateway"])

# All standard HTTP methods handled by the single catch-all route
_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


_GATEWAY_RESPONSES = {
    400: {"description": "API has no target_url configured"},
    401: {"description": "Authentication required or failed"},
    404: {"description": "API or account not found"},
    410: {"description": "API is deprecated"},
    429: {"description": "Rate limit exceeded"},
    503: {"description": "API not yet deployed (still in draft)"},
    502: {"description": "Upstream connection failed"},
    504: {"description": "Upstream timed out"},
}


async def _run_pipeline(
    *,
    api_id: int,
    path: str,
    request: Request,
    db: AsyncSession,
    env: Optional[str],
    version: Optional[str],
    account_id: Optional[int],
    account_slug: Optional[str],
    account: Optional[Account] = None,
) -> Response:
    """Shared enforcement pipeline used by both gateway routes.

    *account_id*, *account_slug*, and *account* are set when the caller
    provides an account context (account-scoped route).  All three are
    ``None`` on the legacy unscoped route (no quota enforcement there).
    """
    t_start = time.monotonic()

    # ── Step 0: Daily quota enforcement (account-scoped requests only) ────
    if account is not None:
        await check_quota(db, account)

    # ── Step 1: Resolve API (scoped to account when provided) ─────────────
    api = await resolve_api(db, api_id, account_id=account_id)
    if not api:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API with id={api_id} not found",
        )

    # ── Step 1b: Version enforcement ──────────────────────────────────────
    if version is not None:
        api_version = getattr(api, "version", None) or ""

        def _norm(v: str) -> str:
            return v.strip().lstrip("vV").lower()

        if _norm(version) != _norm(api_version):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Version mismatch: requested '{version}' but API "
                    f"'{api.name}' (id={api_id}) is registered as version "
                    f"'{api_version}'. Update the API version or omit the "
                    "version parameter."
                ),
            )

    # ── Step 2: Lifecycle check ────────────────────────────────────────────
    blocked = check_api_lifecycle(api)
    if blocked:
        http_code, message = blocked
        raise HTTPException(status_code=http_code, detail=message)

    # ── Step 3: Resolve upstream target URL ───────────────────────────────
    _svc_url = select_service_backend(api)
    _pool_url = select_pool_backend(api)
    try:
        _static_url = get_target_url(api, env_slug=env)
    except EnvironmentNotDeployedError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

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
    _url_source = "mini-cloud" if _svc_url else ("pool" if _pool_url else "static")

    # ── Step 4: Auth enforcement ───────────────────────────────────────────
    await enforce_auth(api, request, db)

    # ── Step 4b: Per-API-key rate-limit (rpm from APIKey.metadata_json) ──
    await enforce_api_key_rate_limit(api, request, db)

    # ── Step 5: Rate-limit enforcement ────────────────────────────────────
    await enforce_rate_limit(api, request)

    # ── Step 5b: Per-API body size enforcement ────────────────────────────
    await enforce_body_size(api, request)

    # ── Step 6: Connector secret injection ────────────────────────────────
    extra_headers, connector_url = await inject_connector_secrets(api, db)
    if connector_url:
        target_url = connector_url

    # ── Step 7: Schema validation ──────────────────────────────────────────
    await enforce_schema_validation(api, request)

    # ── Step 8: Proxy ─────────────────────────────────────────────────────
    logger.info(
        "[GW] account=%s api=%s(%s) env=%s src=%s %s /%s → %s",
        account_slug or "—",
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

    # ── Step 9: Record usage metric ───────────────────────────────────────
    await record_request(
        db,
        account_id=account_id,
        api_id=api_id,
        status_code=response.status_code,
        latency_ms=elapsed_ms,
        method=request.method,
        endpoint=f"/{path}" if path else "/",
    )
    response.headers["x-gateway-latency-ms"] = str(elapsed_ms)
    response.headers["x-gateway-url-source"] = _url_source
    if env:
        response.headers["x-gateway-env"] = env
    if account_slug:
        response.headers["x-gateway-account"] = account_slug
    api_version = getattr(api, "version", None)
    if api_version:
        response.headers["x-gateway-api-version"] = str(api_version)

    return response


# ---------------------------------------------------------------------------
# Route 1: Account-scoped — /gw/{account_slug}/{api_id}/{path:path}
# ---------------------------------------------------------------------------
# ``account_slug`` uses a regex pattern that matches only slugs that are NOT
# purely numeric (e.g. "acme-corp", "my-account").  This prevents ambiguity
# with the legacy /gw/{api_id}/{path} route where the first segment is always
# an integer.
# ---------------------------------------------------------------------------

@router.api_route(
    "/{account_slug:str}/{api_id:int}/{path:path}",
    methods=_METHODS,
    summary="Gateway (account-scoped) — proxy request scoped to a registered account",
    response_description="Upstream HTTP response forwarded verbatim",
    responses=_GATEWAY_RESPONSES,
)
async def gateway_proxy_account_scoped(
    account_slug: str,
    api_id: int,
    path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    env: Optional[str] = Query(
        None,
        description="Environment slug (e.g. 'production', 'staging').",
    ),
    version: Optional[str] = Query(
        None,
        description="API version to enforce (e.g. 'v1', '2.0').",
    ),
) -> Response:
    """Route a request through the gateway, scoped to *account_slug*.

    The account slug is resolved to an ``Account`` record.  If the account
    does not exist or is suspended/deleted the gateway returns **404**.

    The ``api_id`` lookup is then scoped to that account — an API that exists
    under a different account is treated as not found (no cross-tenant leakage).

    ### Example
    ```
    GET /gw/acme-corp/7/users?env=production
    ```
    Routes to API id=7 **only if it belongs to account "acme-corp"**.
    """
    # Reject purely numeric slugs — those belong to the legacy route.
    # FastAPI cannot express "not an integer" as a path type constraint, so we
    # check here and fall through with a 404 that looks identical to the legacy
    # route's "API not found" response.
    if account_slug.isdigit():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API with id={account_slug} not found",
        )

    # Resolve the account
    account = await resolve_account_by_slug(db, account_slug)
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account '{account_slug}' not found or not active",
        )

    return await _run_pipeline(
        api_id=api_id,
        path=path,
        request=request,
        db=db,
        env=env,
        version=version,
        account_id=account.id,
        account_slug=account_slug,
        account=account,
    )


# ---------------------------------------------------------------------------
# Route 2: Legacy unscoped — /gw/{api_id}/{path:path}
# ---------------------------------------------------------------------------

@router.api_route(
    "/{api_id}/{path:path}",
    methods=_METHODS,
    summary="Gateway (legacy) — proxy request to a registered API's upstream",
    response_description="Upstream HTTP response forwarded verbatim",
    responses=_GATEWAY_RESPONSES,
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
    version: Optional[str] = Query(
        None,
        description=(
            "API version to enforce (e.g. 'v1', '2.0'). "
            "When provided the gateway returns 400 if the API's registered "
            "version does not match."
        ),
    ),
) -> Response:
    """Route an inbound HTTP request through the gateway enforcement pipeline.

    **Deprecated in favour of the account-scoped route**
    ``/gw/{account_slug}/{api_id}/{path}``.  This route performs no
    account-level isolation and is preserved for backward compatibility.

    **api_id** — ID of the registered API (retrieve with ``GET /apis/``).

    **path** — Remaining URL path appended to the API's ``target_url``.

    ### Example
    ```
    GET /gw/1/users?env=staging
    ```
    """
    return await _run_pipeline(
        api_id=api_id,
        path=path,
        request=request,
        db=db,
        env=env,
        version=version,
        account_id=None,
        account_slug=None,
    )
