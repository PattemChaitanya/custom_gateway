"""HTTP proxy layer — forwards gateway requests to upstream backends.

Uses a module-level shared ``httpx.AsyncClient`` (connection-pooled) so that
TCP connections to upstream services are reused across gateway requests rather
than opened fresh on every call.

Hop-by-hop headers (defined in RFC 7230 §6.1) are stripped from both the
forwarded request and the upstream response to ensure correct HTTP proxy
semantics.
"""

from typing import Optional

import httpx
from fastapi import HTTPException, Request, status
from fastapi.responses import Response

from app.logging_config import get_logger

logger = get_logger("gateway.proxy")

# ---------------------------------------------------------------------------
# Hop-by-hop headers — must NOT be forwarded (RFC 7230 §6.1)
# ---------------------------------------------------------------------------
_HOP_BY_HOP_HEADERS = frozenset(
    {
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        # "host" is reconstructed by httpx from the upstream URL
        "host",
    }
)

# ---------------------------------------------------------------------------
# Shared async HTTP client (singleton)
# ---------------------------------------------------------------------------
_client: Optional[httpx.AsyncClient] = None


def _get_client() -> httpx.AsyncClient:
    """Return the shared httpx client, creating it on first use."""
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=30.0,
                                  write=10.0, pool=5.0),
            follow_redirects=True,
            limits=httpx.Limits(
                max_connections=200,
                max_keepalive_connections=50,
                keepalive_expiry=30.0,
            ),
        )
    return _client


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_upstream_url(target_url: str, path: str, query_string: str) -> str:
    """Construct the full upstream URL.

    ``target_url`` is stripped of trailing slashes; ``path`` is appended with
    a leading slash so the result is always well-formed.

    Examples:
        _build_upstream_url("https://svc.io", "users/1", "page=2")
        → "https://svc.io/users/1?page=2"

        _build_upstream_url("https://svc.io/v2", "", "")
        → "https://svc.io/v2"
    """
    base = target_url.rstrip("/")
    path_part = f"/{path.lstrip('/')}" if path else ""
    url = f"{base}{path_part}"
    if query_string:
        url = f"{url}?{query_string}"
    return url


def _filter_headers(headers: dict) -> dict:
    """Remove hop-by-hop headers; returns a plain dict with lowercase keys."""
    return {k: v for k, v in headers.items() if k.lower() not in _HOP_BY_HOP_HEADERS}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def proxy_request(
    request: Request,
    target_url: str,
    path: str,
    api_id: int,
    extra_headers: Optional[dict] = None,
) -> Response:
    """Forward *request* to *target_url/path* and return the upstream response.

    Downstream (gateway → upstream) changes:
    - Hop-by-hop headers stripped
    - ``X-Forwarded-For``, ``X-Forwarded-Host``, ``X-Gateway-API-ID`` injected
    - *extra_headers* merged in last (connector / secret-injected headers)

    Upstream (upstream → client) changes:
    - Hop-by-hop headers stripped
    - ``X-Gateway-Upstream`` and ``X-Gateway-API-ID`` appended

    Error mapping:
    - ``httpx.ConnectError``    → 502 Bad Gateway
    - ``httpx.TimeoutException``→ 504 Gateway Timeout
    - Other httpx errors       → 502 Bad Gateway
    """
    client = _get_client()

    # Build the target URL
    upstream_url = _build_upstream_url(target_url, path, request.url.query)

    # Build forwarded headers
    fwd_headers = _filter_headers(dict(request.headers))
    fwd_headers["x-forwarded-for"] = (
        request.client.host if request.client else "unknown"
    )
    fwd_headers["x-forwarded-host"] = request.headers.get("host", "")
    fwd_headers["x-gateway-api-id"] = str(api_id)
    request_id = request.headers.get("x-request-id")
    if request_id:
        fwd_headers["x-request-id"] = request_id

    # Merge connector / secret-injected headers last so they can
    # override or supplement client-provided headers.
    if extra_headers:
        fwd_headers.update({k.lower(): v for k, v in extra_headers.items()})

    # Read body once (Starlette caches it so this is safe)
    body = await request.body()

    logger.debug(
        "Proxying %s %s → %s (api_id=%s)",
        request.method,
        request.url.path,
        upstream_url,
        api_id,
    )

    try:
        upstream_resp = await client.request(
            method=request.method,
            url=upstream_url,
            headers=fwd_headers,
            content=body,
        )
    except httpx.ConnectError as exc:
        logger.error("Gateway connect error → %s: %s", upstream_url, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to connect to upstream: {target_url}",
        )
    except httpx.TimeoutException as exc:
        logger.error("Gateway timeout → %s: %s", upstream_url, exc)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Upstream request timed out",
        )
    except httpx.HTTPError as exc:
        logger.error("Gateway HTTP error → %s: %s", upstream_url, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Gateway proxy error",
        )

    # Build the response, stripping upstream hop-by-hop headers
    resp_headers = _filter_headers(dict(upstream_resp.headers))
    resp_headers["x-gateway-upstream"] = target_url
    resp_headers["x-gateway-api-id"] = str(api_id)

    return Response(
        content=upstream_resp.content,
        status_code=upstream_resp.status_code,
        headers=resp_headers,
        media_type=upstream_resp.headers.get("content-type"),
    )
