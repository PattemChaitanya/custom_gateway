"""Centralized audit logging middleware.

Intercepts every API request/response and writes a structured audit log entry
with a semantic event name (e.g. ``secret:create``, ``api:delete``,
``auth:login``).  Read-only operations (GET/HEAD/OPTIONS) are logged only when
they target sensitive resources.

The middleware runs **after** the authorization middleware so that
``request.state.user`` is already populated with the decoded JWT payload.
"""

import re
import time
from typing import Callable, Optional, Tuple

from fastapi import FastAPI, Request, Response
from starlette.responses import StreamingResponse

from app.logging_config import get_logger

logger = get_logger("audit_middleware")

# ---------------------------------------------------------------------------
# Event taxonomy
# ---------------------------------------------------------------------------
# Each entry maps a (method, path-regex) to an (event_name, resource_type).
# Order matters: first match wins.
# READ operations (GET) are only mapped for security-sensitive endpoints.
# ---------------------------------------------------------------------------

_ROUTE_EVENT_MAP: list[Tuple[str, str, str, str]] = [
    # ── Auth ─────────────────────────────────────────────────────────────
    ("POST", r"^/auth/login$",
     "auth:login",               "auth"),
    ("POST", r"^/auth/register$",
     "auth:register",            "auth"),
    ("POST", r"^/auth/logout$",
     "auth:logout",              "auth"),
    ("POST", r"^/auth/refresh-tokens$",
     "auth:token_refresh",       "auth"),
    ("POST", r"^/auth/reset-password$",
     "auth:password_reset",      "auth"),
    ("POST", r"^/auth/send-code$",
     "auth:send_code",           "auth"),
    ("POST", r"^/auth/send-otp$",
     "auth:send_otp",           "auth"),
    ("POST", r"^/auth/send-email-code$",
     "auth:send_email_code",     "auth"),
    ("POST", r"^/auth/resend-otp$",
     "auth:resend_otp",          "auth"),
    ("POST", r"^/auth/verify-email$",
     "auth:verify_email",        "auth"),
    ("POST", r"^/auth/verify-otp$",
     "auth:verify_otp",          "auth"),
    ("POST", r"^/auth/users/[^/]+/roles$",
     "auth:set_roles",           "user"),
    ("GET",  r"^/auth/users/[^/]+/roles$",
     "auth:get_roles",           "user"),
    ("GET",  r"^/auth/users$",
     "auth:list_users",          "user"),
    ("GET",  r"^/auth/me$",
     "auth:me",                  "user"),

    # ── Users ────────────────────────────────────────────────────────────
    ("GET",  r"^/user/?$",
     "user:list",                "user"),
    ("GET",  r"^/user/me$",
     "user:me",                  "user"),
    ("GET",  r"^/user/\d+$",
     "user:read",                "user"),

    # ── APIs ─────────────────────────────────────────────────────────────
    ("POST",   r"^/apis/?$",
     "api:create",               "api"),
    ("GET",    r"^/apis/?$",
     "api:list",                 "api"),
    ("GET",    r"^/apis/\d+$",
     "api:read",                 "api"),
    ("PUT",    r"^/apis/\d+$",
     "api:update",               "api"),
    ("DELETE", r"^/apis/\d+$",
     "api:delete",               "api"),

    # ── Deployments ──────────────────────────────────────────────────────
    ("POST",   r"^/apis/\d+/deployments$",
     "deployment:create",        "deployment"),
    ("GET",    r"^/apis/\d+/deployments$",
     "deployment:list",          "deployment"),
    ("GET",    r"^/apis/\d+/deployments/\d+$",
     "deployment:read",          "deployment"),
    ("DELETE", r"^/apis/\d+/deployments/\d+$",
     "deployment:delete",        "deployment"),
    ("PATCH",  r"^/apis/\d+/status$",
     "deployment:status_update", "deployment"),

    # ── Auth Policies ────────────────────────────────────────────────────
    ("POST",   r"^/apis/\d+/auth-policies$",
     "auth_policy:create",       "auth_policy"),
    ("GET",    r"^/apis/\d+/auth-policies$",
     "auth_policy:list",         "auth_policy"),
    ("GET",    r"^/apis/\d+/auth-policies/\d+$",
     "auth_policy:read",         "auth_policy"),
    ("PUT",    r"^/apis/\d+/auth-policies/\d+$",
     "auth_policy:update",       "auth_policy"),
    ("DELETE", r"^/apis/\d+/auth-policies/\d+$",
     "auth_policy:delete",       "auth_policy"),

    # ── Rate Limits ──────────────────────────────────────────────────────
    ("POST",   r"^/apis/\d+/rate-limits$",
     "rate_limit:create",        "rate_limit"),
    ("GET",    r"^/apis/\d+/rate-limits$",
     "rate_limit:list",          "rate_limit"),
    ("GET",    r"^/apis/\d+/rate-limits/\d+$",
     "rate_limit:read",          "rate_limit"),
    ("PUT",    r"^/apis/\d+/rate-limits/\d+$",
     "rate_limit:update",        "rate_limit"),
    ("DELETE", r"^/apis/\d+/rate-limits/\d+$",
     "rate_limit:delete",        "rate_limit"),

    # ── Schemas ──────────────────────────────────────────────────────────
    ("POST",   r"^/apis/\d+/schemas$",
     "schema:create",            "schema"),
    ("GET",    r"^/apis/\d+/schemas$",
     "schema:list",              "schema"),
    ("GET",    r"^/apis/\d+/schemas/\d+$",
     "schema:read",              "schema"),
    ("PUT",    r"^/apis/\d+/schemas/\d+$",
     "schema:update",            "schema"),
    ("DELETE", r"^/apis/\d+/schemas/\d+$",
     "schema:delete",            "schema"),

    # ── Backend Pools ────────────────────────────────────────────────────
    ("POST",   r"^/apis/\d+/backend-pools$",
     "backend_pool:create",      "backend_pool"),
    ("GET",    r"^/apis/\d+/backend-pools$",
     "backend_pool:list",        "backend_pool"),
    ("GET",    r"^/apis/\d+/backend-pools/\d+$",
     "backend_pool:read",        "backend_pool"),
    ("PUT",    r"^/apis/\d+/backend-pools/\d+$",
     "backend_pool:update",      "backend_pool"),
    ("DELETE", r"^/apis/\d+/backend-pools/\d+$",
     "backend_pool:delete",      "backend_pool"),
    ("PATCH",  r"^/apis/\d+/backend-pools/\d+/backends/.+/health$",
     "backend_pool:health_update", "backend_pool"),

    # ── API Keys ─────────────────────────────────────────────────────────
    ("POST",   r"^/api/keys/?$",
     "api_key:create",           "api_key"),
    ("GET",    r"^/api/keys/?$",
     "api_key:list",             "api_key"),
    ("POST",   r"^/api/keys/\d+/revoke$",
     "api_key:revoke",           "api_key"),
    ("DELETE", r"^/api/keys/\d+$",
     "api_key:delete",           "api_key"),
    ("GET",    r"^/api/keys/\d+/stats$",
     "api_key:read_stats",       "api_key"),
    ("GET",    r"^/api/keys/verify$",
     "api_key:verify",           "api_key"),
    ("GET",    r"^/api/keys/environments$",
     "environment:list",         "environment"),
    ("POST",   r"^/api/keys/environments$",
     "environment:create",       "environment"),
    ("DELETE", r"^/api/keys/environments/\d+$",
     "environment:delete",       "environment"),

    # ── Secrets ──────────────────────────────────────────────────────────
    ("POST",   r"^/api/secrets/?$",
     "secret:create",            "secret"),
    ("GET",    r"^/api/secrets/?$",
     "secret:list",              "secret"),
    ("GET",    r"^/api/secrets/[^/]+$",
     "secret:read",              "secret"),
    ("PUT",    r"^/api/secrets/[^/]+$",
     "secret:update",            "secret"),
    ("DELETE", r"^/api/secrets/[^/]+$",
     "secret:delete",            "secret"),
    ("POST",   r"^/api/secrets/[^/]+/rotate$",
     "secret:rotate",            "secret"),

    # ── Connectors ───────────────────────────────────────────────────────
    ("POST",   r"^/api/connectors/?$",
     "connector:create",         "connector"),
    ("GET",    r"^/api/connectors/?$",
     "connector:list",           "connector"),
    ("GET",    r"^/api/connectors/\d+$",
     "connector:read",           "connector"),
    ("PUT",    r"^/api/connectors/\d+$",
     "connector:update",         "connector"),
    ("DELETE", r"^/api/connectors/\d+$",
     "connector:delete",         "connector"),
    ("POST",   r"^/api/connectors/\d+/test$",
     "connector:test",           "connector"),

    # ── Authorizers / RBAC ───────────────────────────────────────────────
    ("POST",   r"^/api/authorizers/roles$",
     "role:create",              "role"),
    ("GET",    r"^/api/authorizers/roles$",
     "role:list",                "role"),
    ("GET",    r"^/api/authorizers/roles/\d+$",
     "role:read",                "role"),
    ("PUT",    r"^/api/authorizers/roles/\d+$",
     "role:update",              "role"),
    ("DELETE", r"^/api/authorizers/roles/\d+$",
     "role:delete",              "role"),
    ("POST",   r"^/api/authorizers/permissions$",
     "permission:create",        "permission"),
    ("GET",    r"^/api/authorizers/permissions$",
     "permission:list",          "permission"),
    ("GET",    r"^/api/authorizers/permissions/\d+$",
     "permission:read",        "permission"),
    ("PUT",    r"^/api/authorizers/permissions/\d+$",
     "permission:update",      "permission"),
    ("DELETE", r"^/api/authorizers/permissions/\d+$",
     "permission:delete",      "permission"),
    ("POST",   r"^/api/authorizers/user-roles$",
     "user_role:assign",         "user_role"),
    ("DELETE", r"^/api/authorizers/user-roles/\d+$",
     "user_role:remove",        "user_role"),
    ("GET",    r"^/api/authorizers/user-roles/\d+$",
     "user_role:read",          "user_role"),

    # ── Admin ────────────────────────────────────────────────────────────
    ("POST",   r"^/api/admin/init-rbac$",
     "admin:init_rbac",          "admin"),
    ("GET",    r"^/api/admin/rbac-status$",
     "admin:rbac_status",        "admin"),

    # ── Audit Logs (read-only, but security-sensitive) ───────────────────
    ("GET",    r"^/api/audit-logs$",
     "audit:list",               "audit_log"),
    ("GET",    r"^/api/audit-logs/statistics$",
     "audit:statistics",         "audit_log"),
    ("GET",    r"^/api/audit-logs/user/\d+$",
     "audit:user_activity",      "audit_log"),
    ("GET",    r"^/api/audit-logs/failed$",
     "audit:failed_attempts",    "audit_log"),

    # ── Mini-Cloud ───────────────────────────────────────────────────────
    ("GET",    r"^/mini-cloud/contract$",
     "minicloud:get_contract",   "minicloud"),
    ("GET",    r"^/mini-cloud/policies$",
     "minicloud:get_policies",   "minicloud"),
    ("POST",   r"^/mini-cloud/policies/validate$",
     "minicloud:validate_policy", "minicloud"),
    ("PUT",    r"^/mini-cloud/policies$",
     "minicloud:update_policy",  "minicloud"),
    ("POST",   r"^/mini-cloud/services/[^/]+/instances$",
     "minicloud:register_instance", "minicloud"),
    ("POST",   r"^/mini-cloud/services/[^/]+/instances/[^/]+/heartbeat$",
     "minicloud:heartbeat",      "minicloud"),
    ("POST",   r"^/mini-cloud/services/[^/]+/instances/[^/]+/health-status$",
     "minicloud:health_status",  "minicloud"),
    ("GET",    r"^/mini-cloud/services/[^/]+/instances$",
     "minicloud:list_instances", "minicloud"),
    ("POST",   r"^/mini-cloud/services/[^/]+/route$",
     "minicloud:route",          "minicloud"),
    ("POST",   r"^/mini-cloud/jobs/enqueue$",
     "minicloud:job_enqueue",    "minicloud"),
    ("POST",   r"^/mini-cloud/jobs/lease$",
     "minicloud:job_lease",      "minicloud"),
    ("POST",   r"^/mini-cloud/jobs/ack$",
     "minicloud:job_ack",        "minicloud"),
    ("POST",   r"^/mini-cloud/jobs/fail$",
     "minicloud:job_fail",       "minicloud"),
    ("POST",   r"^/mini-cloud/autoscale$",
     "minicloud:autoscale",      "minicloud"),
    ("POST",   r"^/mini-cloud/inject/slow-downstream$",
     "minicloud:inject_latency", "minicloud"),
    ("POST",   r"^/mini-cloud/inject/burst-traffic$",
     "minicloud:inject_traffic", "minicloud"),

    # ── Gateway proxy ────────────────────────────────────────────────────
    ("*",      r"^/gw/.+",
     "gateway:proxy",            "gateway"),
]

# Pre-compile regexes for performance
_COMPILED_ROUTES: list[Tuple[str, re.Pattern, str, str]] = [
    (method, re.compile(pattern), event, rtype)
    for method, pattern, event, rtype in _ROUTE_EVENT_MAP
]

# Paths that should never be audit-logged (infrastructure / health)
_SKIP_PREFIXES = (
    "/docs",
    "/openapi.json",
    "/redoc",
    "/health",
    "/metrics",
    "/",
)


def _resolve_event(method: str, path: str) -> Optional[Tuple[str, str]]:
    """Return ``(event_name, resource_type)`` for the request, or ``None``."""
    for route_method, pattern, event, rtype in _COMPILED_ROUTES:
        if route_method == "*" or route_method == method:
            if pattern.search(path):
                return event, rtype
    return None


def _extract_resource_id(path: str) -> Optional[str]:
    """Best-effort extraction of a resource identifier from the URL path."""
    parts = [p for p in path.rstrip("/").split("/") if p]
    if len(parts) < 2:
        return None

    # Skip action segments and collection names — these are not resource IDs
    _NON_ID_SEGMENTS = {
        # actions
        "revoke", "rotate", "test", "verify", "stats",
        "heartbeat", "health-status", "route", "health",
        "validate", "enqueue", "lease", "ack", "fail",
        "autoscale", "slow-downstream", "burst-traffic",
        "init-rbac", "rbac-status", "statistics", "failed",
        # collection names (list / create endpoints)
        "apis", "keys", "secrets", "connectors",
        "deployments", "rate-limits", "auth-policies", "schemas",
        "backend-pools", "environments", "roles", "permissions",
        "user-roles", "instances", "audit-logs",
        # top-level prefixes
        "auth", "user", "api", "gw", "mini-cloud",
        "login", "register", "logout", "refresh-tokens",
        "reset-password", "send-code", "send-otp", "send-email-code",
        "resend-otp", "verify-email", "verify-otp", "me", "users",
        "contract", "policies", "jobs", "services", "inject",
        "authorizers", "admin",
    }

    # Try last segment first; if it's a known action, try the one before it
    candidate = parts[-1]
    if candidate in _NON_ID_SEGMENTS:
        # For paths like /api/keys/12/revoke -> try parts[-2] = "12"
        if len(parts) >= 3:
            fallback = parts[-2]
            if fallback not in _NON_ID_SEGMENTS:
                return fallback
        return None

    return candidate


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

def register_audit_middleware(app: FastAPI) -> None:
    """Register the centralized audit-logging middleware.

    Must be registered **before** the authorization middleware in the
    ``add_middleware`` / ``@app.middleware("http")`` chain so that it
    executes **after** authorization (Starlette middleware onion model:
    last-registered = outermost, so we register *first* to be innermost).
    """

    @app.middleware("http")
    async def audit_middleware(request: Request, call_next: Callable) -> Response:
        path = request.url.path

        # Skip infrastructure and audit-query endpoints (prevent self-logging loop)
        if path in ("/", "/health", "/metrics", "/metrics/summary"):
            return await call_next(request)
        if any(path.startswith(p) for p in ("/docs", "/openapi.json", "/redoc", "/api/audit-logs")):
            return await call_next(request)

        method = request.method

        # Resolve the semantic event
        event_info = _resolve_event(method, path)
        if event_info is None:
            # Unknown route — don't block, just skip auditing
            return await call_next(request)

        event_name, resource_type = event_info
        resource_id = _extract_resource_id(path)

        # Capture timing
        start = time.time()
        status_code = 500
        error_msg: Optional[str] = None

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            error_msg = str(exc)[:500]
            raise
        finally:
            duration_ms = int((time.time() - start) * 1000)

            # Extract user info from request.state (set by auth middleware)
            user = getattr(request.state, "user", None)
            user_id: Optional[int] = None
            if user is not None:
                uid = getattr(user, "user_id", None) or getattr(
                    user, "sub", None) or getattr(user, "id", None)
                if uid is not None:
                    try:
                        user_id = int(uid)
                    except (ValueError, TypeError):
                        pass

            ip_address = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent")
            request_id = getattr(request.state, "request_id", None)

            audit_status = "success" if status_code < 400 else "failure"

            # Build metadata
            metadata = {
                "method": method,
                "path": path,
                "status_code": status_code,
                "duration_ms": duration_ms,
                "request_id": request_id,
            }
            if error_msg:
                metadata["error"] = error_msg

            # Persist audit log asynchronously (best-effort; never break the response)
            try:
                await _persist_audit_log(
                    action=event_name,
                    resource_type=resource_type,
                    resource_id=resource_id,
                    user_id=user_id,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    metadata=metadata,
                    status=audit_status,
                    error_message=error_msg,
                )
            except Exception:
                logger.warning(
                    "Failed to persist audit log for %s %s", method, path,
                    exc_info=True,
                )

    logger.info("Centralized audit middleware registered")


async def _persist_audit_log(
    *,
    action: str,
    resource_type: str,
    resource_id: Optional[str],
    user_id: Optional[int],
    ip_address: Optional[str],
    user_agent: Optional[str],
    metadata: dict,
    status: str,
    error_message: Optional[str],
) -> None:
    """Write an audit log row using its own short-lived DB session."""
    from app.db import get_db_manager

    db_manager = get_db_manager()
    async with db_manager.get_session() as session:
        from app.logging.audit import AuditLogger

        auditor = AuditLogger(session)
        await auditor.log_event(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            metadata=metadata,
            status=status,
            error_message=error_message,
        )

        # Commit since this is an independent session
        if hasattr(session, "commit"):
            await session.commit()
