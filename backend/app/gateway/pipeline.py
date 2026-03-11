"""Gateway enforcement pipeline.

Runs the ordered chain of checks before proxying an inbound request.
Each function raises ``HTTPException`` on failure; returning normally means
the check passed.

Pipeline order (called by the router):
    1.  enforce_auth()              — validates auth policy (apiKey / jwt / oauth2 / open)
    2.  enforce_rate_limit()        — per-API rate limit (ip / key / global)
    3.  enforce_schema_validation() — JSON Schema validation of request body

Auth policy types
-----------------
none / open
    Pass-through.  No credentials required.

apiKey
    Validates ``X-API-Key`` (or custom header from policy.config.header_name).
    When ``policy.config.scope_to_environment`` is true, only keys assigned to
    the API's deployed environment are accepted.

jwt / bearer
    Validates ``Authorization: Bearer <token>``.
    Uses ``policy.config.secret`` (or ``${secret:<name>}`` reference) when set,
    otherwise falls back to the global ``JWT_SECRET`` env var.
    Optionally checks ``policy.config.issuer`` and ``policy.config.audience``.

oauth2
    Calls an external token introspection endpoint (RFC 7662).
    Requires ``policy.config.token_introspection_url``.
    Uses HTTP Basic auth with ``policy.config.client_id`` /
    ``policy.config.client_secret`` (both support ``${secret:<name>}`` refs).
"""

import hashlib
import hmac
import os
import re

import httpx
from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import API
from app.logging_config import get_logger
from app.rate_limiter.algorithms import (
    FixedWindowRateLimiter,
    SlidingWindowRateLimiter,
    TokenBucketRateLimiter,
)

logger = get_logger("gateway.pipeline")

# Shared rate-limiter instances (module-level singletons)
_fixed_limiter = FixedWindowRateLimiter()
_sliding_limiter = SlidingWindowRateLimiter()
_token_limiter = TokenBucketRateLimiter()

# Placeholder pattern shared with secret_injector
_SECRET_REF_RE = re.compile(r"^\$\{secret:([a-zA-Z0-9_\-]+)\}$", re.IGNORECASE)


async def _resolve_secret_ref(value: str, db: AsyncSession) -> str:
    """If *value* is a ``${secret:<name>}`` reference, return the decrypted secret.
    Otherwise return *value* unchanged."""
    m = _SECRET_REF_RE.match(value or "")
    if not m:
        return value
    name = m.group(1)
    try:
        from app.security.secrets import SecretsManager
        mgr = SecretsManager(db)
        secret = await mgr.get_secret(name, decrypt=True)
        if secret:
            plaintext = getattr(secret, "value", None)
            if plaintext and plaintext != "***ENCRYPTED***":
                return plaintext
    except Exception as exc:
        logger.error("Failed to resolve secret ref '%s': %s", name, exc)
    return value  # Fall back to raw value / unresolved ref


# ---------------------------------------------------------------------------
# Auth enforcement (public entry point)
# ---------------------------------------------------------------------------

async def enforce_auth(api: API, request: Request, db: AsyncSession) -> None:
    """Enforce the API's configured auth policy.

    Policy resolution order:
    - No ``auth_policies`` attached   → open/public (pass through)
    - policy.type == "none"/"open"    → pass through explicitly
    - policy.type == "apiKey"         → validate key header
    - policy.type == "jwt"/"bearer"   → validate Bearer token
    - policy.type == "oauth2"         → introspect token externally
    """
    if not api.auth_policies:
        return  # No policy → open API

    policy = api.auth_policies[0]
    policy_type = (policy.type or "none").lower().replace(
        "-", "").replace("_", "")
    config: dict = policy.config or {}

    if policy_type in ("none", "open", ""):
        return

    if policy_type == "apikey":
        await _check_api_key(request, db, config, api)

    elif policy_type in ("jwt", "bearer"):
        await _check_jwt(request, db, config)

    elif policy_type == "oauth2":
        await _check_oauth2(request, db, config)

    else:
        logger.warning(
            "Unknown auth policy type '%s' for API %s — passing through",
            policy.type,
            api.id,
        )


# ---------------------------------------------------------------------------
# apiKey enforcement
# ---------------------------------------------------------------------------

async def _check_api_key(
    request: Request,
    db: AsyncSession,
    config: dict,
    api: API,
) -> None:
    """Validate the API key from the configured header.

    config keys:
    - ``header_name``          — header to read (default: ``X-API-Key``)
    - ``scope_to_environment`` — bool; when true only accept keys whose
                                 ``environment_id`` matches the API's active
                                 deployment environment (default: false)
    """
    header_name: str = config.get("header_name", "X-API-Key")
    raw_key = request.headers.get(header_name)
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{header_name} header is required",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    from sqlalchemy.future import select as sa_select
    from app.db.models import APIKey, APIDeployment
    from datetime import datetime, timezone

    scope_to_env: bool = bool(config.get("scope_to_environment", False))

    # Determine the environment_id from the active deployment when scoping
    allowed_env_id: int | None = None
    if scope_to_env:
        dep_result = await db.execute(
            sa_select(APIDeployment).where(
                APIDeployment.api_id == api.id,
                APIDeployment.status == "deployed",
            )
        )
        dep = dep_result.scalars().first()
        if dep:
            allowed_env_id = dep.environment_id

    # Fetch candidate keys
    key_query = sa_select(APIKey).where(APIKey.revoked == False)  # noqa: E712
    if scope_to_env and allowed_env_id is not None:
        key_query = key_query.where(APIKey.environment_id == allowed_env_id)

    result = await db.execute(key_query)
    keys = result.scalars().all()

    now = datetime.now(timezone.utc)
    for stored_key in keys:
        if stored_key.expires_at:
            expires = stored_key.expires_at
            # Ensure offset-aware comparison
            if expires.tzinfo is None:
                from datetime import timezone as tz
                expires = expires.replace(tzinfo=tz.utc)
            if expires < now:
                continue
        if _verify_api_key(raw_key, stored_key.key):
            return  # Valid key found

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )


def _verify_api_key(raw_key: str, stored_hash: str) -> bool:
    """Constant-time comparison (supports salted ``salt:hash`` and plain SHA-256)."""
    try:
        if ":" in stored_hash:
            salt, expected = stored_hash.split(":", 1)
            actual = hashlib.sha256(f"{raw_key}{salt}".encode()).hexdigest()
            return hmac.compare_digest(actual, expected)
        actual = hashlib.sha256(raw_key.encode()).hexdigest()
        return hmac.compare_digest(actual, stored_hash)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT / Bearer enforcement
# ---------------------------------------------------------------------------

async def _check_jwt(request: Request, db: AsyncSession, config: dict) -> None:
    """Validate a Bearer JWT.

    config keys:
    - ``secret``   — signing secret (plain string or ``${secret:<name>}`` ref).
                     Defaults to ``JWT_SECRET`` env var when absent.
    - ``issuer``   — expected ``iss`` claim (skipped when absent)
    - ``audience`` — expected ``aud`` claim (skipped when absent)
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization: Bearer <token> header is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_header[len("Bearer "):]

    # Resolve the signing secret
    raw_secret = config.get("secret") or os.getenv(
        "JWT_SECRET", "change-this-secret")
    signing_secret = await _resolve_secret_ref(str(raw_secret), db)

    try:
        from jose import JWTError, jwt as jose_jwt

        options: dict = {}
        decode_kwargs: dict = {
            "algorithms": ["HS256", "RS256"],
            "options": options,
        }

        issuer = config.get("issuer")
        audience = config.get("audience")
        if issuer:
            decode_kwargs["issuer"] = issuer
        if audience:
            decode_kwargs["audience"] = audience
        else:
            # Skip audience validation when not configured
            options["verify_aud"] = False

        payload = jose_jwt.decode(token, signing_secret, **decode_kwargs)
        if not payload.get("sub"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject claim",
            )
    except JWTError as exc:
        logger.debug("JWT validation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.debug("JWT validation error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# OAuth2 token introspection (RFC 7662)
# ---------------------------------------------------------------------------

async def _check_oauth2(request: Request, db: AsyncSession, config: dict) -> None:
    """Introspect a Bearer token against an external OAuth2 server (RFC 7662).

    config keys (required):
    - ``token_introspection_url`` — introspection endpoint URL

    config keys (optional):
    - ``client_id``     — OAuth2 client id (plain or ``${secret:<name>}`` ref)
    - ``client_secret`` — OAuth2 client secret (plain or ``${secret:<name>}`` ref)
    """
    introspect_url: str = config.get("token_introspection_url", "")
    if not introspect_url:
        logger.error("oauth2 policy config missing token_introspection_url")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Auth policy misconfigured: missing token_introspection_url",
        )

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization: Bearer <token> header is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = auth_header[len("Bearer "):]

    # Resolve client credentials (may be secret refs)
    client_id = await _resolve_secret_ref(str(config.get("client_id", "")), db)
    client_secret = await _resolve_secret_ref(str(config.get("client_secret", "")), db)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                introspect_url,
                data={"token": token, "token_type_hint": "access_token"},
                auth=(client_id, client_secret) if client_id else None,
            )
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token introspection failed",
                headers={"WWW-Authenticate": "Bearer"},
            )
        data = resp.json()
        if not data.get("active", False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is inactive or expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("OAuth2 introspection error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not verify token with authorization server",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ---------------------------------------------------------------------------
# Rate-limit enforcement
# ---------------------------------------------------------------------------

async def enforce_rate_limit(api: API, request: Request) -> None:
    """Enforce the API's per-API rate limit configuration.

    Uses ``api.rate_limits[0]`` (if present).  The Redis key is namespaced
    per API so it does not interfere with the global gateway rate limiter.

    key_type strategies:
    - ``per-ip``  → keyed by client IP
    - ``per-key`` → keyed by the first 16 chars of X-API-Key (hashed)
    - ``global``  → single counter shared across all callers of this API

    Raises HTTP 429 if the rate limit is exceeded.
    """
    if not api.rate_limits:
        return  # No rate limit configured for this API

    rl = api.rate_limits[0]
    limit: int = rl.limit
    window: int = rl.window_seconds
    key_type: str = (rl.key_type or "global").lower()
    algorithm: str = getattr(rl, "algorithm", "fixed_window") or "fixed_window"

    if key_type == "per-ip":
        client_ip = request.client.host if request.client else "unknown"
        rate_key = f"gw:api:{api.id}:ip:{client_ip}"
    elif key_type == "per-key":
        raw_key = request.headers.get("X-API-Key", "")
        # Use first 16 chars as a stable, non-secret discriminator
        rate_key = f"gw:api:{api.id}:key:{raw_key[:16]}"
    else:
        rate_key = f"gw:api:{api.id}:global"

    # Pick algorithm implementation
    if algorithm == "sliding_window":
        limiter = _sliding_limiter
    elif algorithm == "token_bucket":
        limiter = _token_limiter
    else:
        limiter = _fixed_limiter

    allowed, info = await limiter.is_allowed(rate_key, limit, window)
    if not allowed:
        retry_after = str(info.get("reset", window))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "rate_limit_exceeded",
                "api_id": api.id,
                "limit": info.get("limit", limit),
                "remaining": info.get("remaining", 0),
                "retry_after_seconds": retry_after,
            },
            headers={"Retry-After": retry_after},
        )


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

# HTTP methods that carry a request body and should be validated
_BODY_METHODS = frozenset({"POST", "PUT", "PATCH"})


async def enforce_schema_validation(api: API, request: Request) -> None:
    """Validate the request body against the API's first JSON Schema definition.

    - Only runs for body-carrying methods (POST, PUT, PATCH).
    - Skipped entirely when the API has no schemas, or the first schema has a
      null ``definition``.
    - Returns HTTP **422 Unprocessable Entity** with structured validation
      errors when validation fails.
    - Returns HTTP **400 Bad Request** when the body is not valid JSON.
    """
    if request.method.upper() not in _BODY_METHODS:
        return  # No body to validate for GET / DELETE / HEAD / OPTIONS

    if not api.schemas:
        return  # No schema attached to this API

    schema_def = api.schemas[0].definition
    if not schema_def:
        return  # Schema row exists but definition is null — skip

    # Read and parse the raw body
    try:
        body_bytes = await request.body()
        if not body_bytes:
            return  # Empty body — let upstream decide
        import json
        body = json.loads(body_bytes)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request body is not valid JSON: {exc}",
        )

    # Validate against JSON Schema
    try:
        import jsonschema
        validator = jsonschema.Draft7Validator(schema_def)
        errors = sorted(validator.iter_errors(
            body), key=lambda e: list(e.path))
        if errors:
            details = [
                {
                    "field": ".".join(str(p) for p in err.path) or "(root)",
                    "message": err.message,
                    "schema_path": ".".join(str(p) for p in err.schema_path),
                }
                for err in errors
            ]
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "error": "schema_validation_failed",
                    "api_id": api.id,
                    "violations": details,
                },
            )
    except HTTPException:
        raise
    except Exception as exc:
        # Misconfigured schema — log and pass through (fail open, don't block)
        logger.error(
            "Schema validation error for api_id=%s (schema might be invalid): %s",
            api.id,
            exc,
        )
