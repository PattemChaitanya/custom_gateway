"""Resolves inbound gateway requests to registered API records.

Given an api_id, loads the full API record from the database including its
related auth_policies, rate_limits, connectors and deployments so the pipeline
can make enforcement decisions without additional DB round-trips.
"""

from typing import Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.db.models import API, APIDeployment, Account, BackendPool, Environment
from app.logging_config import get_logger

logger = get_logger("gateway.resolver")


async def resolve_account_by_slug(db: AsyncSession, slug: str) -> Optional[Account]:
    """Look up an active Account by its URL-safe slug.

    Returns None when the account does not exist or is not active — callers
    should treat both cases as 404 to avoid leaking account existence.
    """
    result = await db.execute(
        select(Account).where(
            Account.slug == slug,
            Account.status == "active",
        )
    )
    return result.scalar_one_or_none()


async def resolve_api(
    db: AsyncSession,
    api_id: int,
    account_id: Optional[int] = None,
) -> Optional[API]:
    """Load an API record by primary key, eagerly loading all policy relationships.

    When *account_id* is provided the query is scoped to that account — an API
    that exists but belongs to a different account returns ``None`` (caller
    should raise 404, not 403, to avoid leaking cross-tenant information).

    Returns None if the API does not exist.
    """
    stmt = (
        select(API)
        .options(
            selectinload(API.schemas),
            selectinload(API.auth_policies),
            selectinload(API.rate_limits),
            selectinload(API.connectors),
            selectinload(API.deployments).selectinload(
                APIDeployment.environment),
            selectinload(API.backend_pools),
        )
        .where(API.id == api_id)
    )
    if account_id is not None:
        stmt = stmt.where(API.account_id == account_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def get_target_url(api: API, env_slug: Optional[str] = None) -> Optional[str]:
    """Resolve the upstream target URL for *api*, optionally scoped to *env_slug*.

    Resolution order (no env_slug):
    1. Return ``config["target_url"]`` (global static URL).

    Resolution order (env_slug provided):
    1. Find the ``deployed`` deployment for that environment.
    2. Return its ``target_url_override`` when set, otherwise fall back to
       ``config["target_url"]`` as a per-env base URL.

    Returns ``None`` when no URL can be resolved.
    Raises ``EnvironmentNotDeployedError`` when *env_slug* is given but the
    API has no ``deployed`` deployment for that environment — the caller should
    return HTTP 404 rather than silently routing to the wrong backend.
    """
    if env_slug:
        for dep in (api.deployments or []):
            if (
                dep.status == "deployed"
                and dep.environment
                and dep.environment.slug == env_slug
            ):
                if dep.target_url_override:
                    return dep.target_url_override
                # Deployment exists but has no override — fall back to global URL
                break
        else:
            # No deployed deployment found for the requested environment
            raise EnvironmentNotDeployedError(
                f"API '{api.name}' (id={api.id}) has no active deployment in "
                f"environment '{env_slug}'. Deploy the API to that environment "
                "first via POST /apis/{id}/deployments."
            )

    if api.config and isinstance(api.config, dict):
        return api.config.get("target_url")
    return None


class EnvironmentNotDeployedError(Exception):
    """Raised when the requested environment has no active deployment."""


def select_pool_backend(api: API) -> Optional[str]:
    """If the API has a ``BackendPool`` attached, select a backend URL from it
    using the pool's configured algorithm.  Returns ``None`` when no pool is
    configured or all backends are unhealthy.

    This is called in-process using the loaded pool record — no additional
    DB round-trips needed because ``resolve_api`` eagerly loads ``backend_pools``.
    """
    if not api.backend_pools:
        return None

    pool: BackendPool = api.backend_pools[0]
    backends_raw = pool.backends or []
    if not backends_raw:
        return None

    from app.load_balancer.algorithms import create_load_balancer
    lb = create_load_balancer(pool.algorithm or "round_robin", backends_raw)
    backend = lb.select_backend()
    if backend:
        return backend.url
    return None


def select_service_backend(api: API) -> Optional[str]:
    """If the API's ``config.service_name`` is set, look up a healthy instance
    from the in-process mini-cloud ``ServiceRegistry`` and return its URL.

    Resolution uses the routing strategy configured in
    ``config.routing_strategy`` (default: ``round_robin``).

    Returns ``None`` when:
    - ``config.service_name`` is not set
    - No instances are registered for that service
    - All known instances are unhealthy / expired
    """
    config = api.config or {}
    service_name: Optional[str] = config.get("service_name")
    if not service_name:
        return None

    strategy: str = config.get("routing_strategy", "round_robin")

    try:
        from app.control_plane.runtime import registry
        instance = registry.select_instance(service_name, strategy=strategy)
        if instance:
            logger.debug(
                "Mini-cloud routing: api=%s → service=%s → instance=%s (%s)",
                api.id,
                service_name,
                instance.instance_id,
                instance.url,
            )
            return instance.url
    except Exception as exc:
        logger.warning(
            "Mini-cloud registry lookup failed for api=%s service=%s: %s",
            api.id,
            service_name,
            exc,
        )
    return None


def check_api_lifecycle(api: API) -> Optional[Tuple[int, str]]:
    """Check whether the API's lifecycle status blocks proxying.

    Returns ``(http_status_code, message)`` when the API should NOT be proxied,
    or ``None`` when the request may proceed.

    - ``draft``       → 503 Service Unavailable (not yet deployed)
    - ``deprecated``  → 410 Gone
    - ``active``      → None (proceed)
    """
    api_status = (api.status or "draft").lower()
    if api_status == "draft":
        return (
            503,
            f"API '{api.name}' (id={api.id}) is in draft status and has not been deployed. "
            "Deploy it via POST /apis/{id}/deployments first.",
        )
    if api_status == "deprecated":
        return (
            410,
            f"API '{api.name}' (id={api.id}) has been deprecated and is no longer available.",
        )
    return None  # active — proceed
