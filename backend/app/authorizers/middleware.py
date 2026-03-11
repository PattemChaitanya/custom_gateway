"""Authorization middleware.

This middleware is intentionally lightweight: it extracts and validates the
JWT access token (when present) and stores the decoded user payload on
``request.state.user``.  Actual permission enforcement is done at the route
level via ``Depends(require_permission(...))``, which has full access to the
dependency-injection system and can raise properly-typed HTTP exceptions.
"""

from typing import Callable, Optional
from fastapi import FastAPI, Request, Response
from app.logging_config import get_logger

logger = get_logger("auth_middleware")

# Public paths that never require a token
_PUBLIC_PREFIXES = (
    "/docs",
    "/openapi.json",
    "/redoc",
    "/health",
    "/metrics",
    "/auth/login",
    "/auth/register",
    "/auth/send-code",
    "/auth/verify",
)


def _extract_token(request: Request) -> Optional[str]:
    """Pull the Bearer token from Authorization header or access_token cookie."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):].strip()
    return request.cookies.get("access_token")


def register_authorization_middleware(app: FastAPI) -> None:
    """Register the auth-enrichment middleware.

    Populates ``request.state.user`` with the decoded JWT payload so that
    downstream code (e.g. logging, audit, deployment tracking) can access the
    current user without an extra DB round-trip.
    """

    @app.middleware("http")
    async def authorization_middleware(request: Request, call_next: Callable) -> Response:
        # Always serve public paths without touching the token
        if any(request.url.path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)

        # Best-effort JWT decode — errors are silently ignored here because
        # the route-level dependency will reject unauthenticated requests with
        # a proper 401.  We only store the user if the token is valid.
        token = _extract_token(request)
        if token:
            try:
                from jose import jwt as _jwt
                import os
                secret = os.getenv("SECRET_KEY", "changeme-secret-key")
                payload = _jwt.decode(
                    token,
                    secret,
                    algorithms=[os.getenv("JWT_ALGORITHM", "HS256")],
                    options={"verify_exp": True},
                )
                # Store as a simple namespace so attribute access works
                from types import SimpleNamespace
                ns = SimpleNamespace(**payload)
                ns.get = lambda k, d=None: getattr(ns, k, d)
                request.state.user = ns
            except Exception:
                # Invalid / expired token — route deps will enforce 401 if needed
                request.state.user = None
        else:
            request.state.user = None

        return await call_next(request)

    logger.info("Authorization middleware registered")
