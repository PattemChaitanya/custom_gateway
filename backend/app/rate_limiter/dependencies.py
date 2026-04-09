"""FastAPI dependency for per-route rate limiting.

Use ``Depends(management_rate_limit)`` on any router or individual route that
needs a stricter limit than the global middleware provides.  The dependency
applies a fixed-window limiter keyed by authenticated user-id or client IP.

Environment overrides:
  MGMT_RATE_LIMIT        — requests per window (default: 100)
  MGMT_RATE_LIMIT_WINDOW — window in seconds    (default: 60)
"""

import os
from fastapi import Depends, HTTPException, Request, status

from .algorithms import FixedWindowRateLimiter

_limiter = FixedWindowRateLimiter()

_LIMIT = int(os.getenv("MGMT_RATE_LIMIT", "100"))
_WINDOW = int(os.getenv("MGMT_RATE_LIMIT_WINDOW", "60"))


async def management_rate_limit(request: Request) -> None:
    """Dependency that enforces stricter rate limits on management endpoints.

    Keying strategy (most-specific wins):
      1. Authenticated user id from ``request.state.user``
      2. ``X-API-Key`` header prefix (first 16 chars)
      3. Client IP address

    Raises HTTP 429 when the limit is exceeded.
    """
    user = getattr(request.state, "user", None)
    if user is not None:
        uid = getattr(user, "id", None) or (
            user.get("id") if hasattr(user, "get") else None
        )
        key = f"mgmt:user:{uid}" if uid else None
    else:
        key = None

    if key is None:
        api_key_header = request.headers.get("X-API-Key", "")
        if api_key_header:
            key = f"mgmt:apikey:{api_key_header[:16]}"
        else:
            client_ip = request.client.host if request.client else "unknown"
            key = f"mgmt:ip:{client_ip}"

    allowed, info = await _limiter.is_allowed(key, _LIMIT, _WINDOW)
    if not allowed:
        retry_after = str(info.get("reset", _WINDOW))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "management_rate_limit_exceeded",
                "limit": _LIMIT,
                "window_seconds": _WINDOW,
                "remaining": info.get("remaining", 0),
                "retry_after_seconds": retry_after,
            },
            headers={"Retry-After": retry_after},
        )
