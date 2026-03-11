"""Backend pool management routes.

Mounted on the APIs router at:
    POST   /apis/{api_id}/backend-pools
    GET    /apis/{api_id}/backend-pools
    GET    /apis/{api_id}/backend-pools/{pool_id}
    PUT    /apis/{api_id}/backend-pools/{pool_id}
    DELETE /apis/{api_id}/backend-pools/{pool_id}

    PATCH  /apis/{api_id}/backend-pools/{pool_id}/backends/{url:path}/health
           — mark a backend within a pool healthy/unhealthy

The gateway proxy uses the **first** pool (by id) attached to an API for
backend selection.  Static ``target_url`` is used only when no pool is
attached or all backends in the pool are unhealthy.

Pool algorithms
---------------
- ``round_robin``        — requests cycled evenly across healthy backends
- ``least_connections``  — backend with fewest active connections is chosen
- ``weighted``           — random selection weighted by each backend's weight

Backends format (JSON array in the ``backends`` field)
------------------------------------------------------
[
    {"url": "http://host1:8080", "weight": 1},
    {"url": "http://host2:8080", "weight": 2}
]
"""

from typing import Any, Dict, List, Literal, Optional
from urllib.parse import unquote

from fastapi import APIRouter, Depends, HTTPException, Path, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorizers.rbac import require_permission
from app.db.connector import get_db
from app.db.models import API, BackendPool
from app.logging_config import get_logger

logger = get_logger("api.lb_router")

router = APIRouter(tags=["backend-pools"])

_ALGORITHMS = Literal["round_robin", "least_connections", "weighted"]


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class BackendEntry(BaseModel):
    url: str = Field(...,
                     description="Backend upstream URL, e.g. http://host:8080")
    weight: int = Field(
        1, ge=1, description="Relative weight (weighted algorithm only)")
    healthy: bool = Field(True, description="Initial health state")


class BackendPoolCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    algorithm: _ALGORITHMS = Field(
        "round_robin", description="Load balancing algorithm")
    backends: List[BackendEntry] = Field(..., min_length=1,
                                         description="List of upstream backends")
    health_check_url: Optional[str] = Field(
        None,
        description="Path or full URL used for periodic health checks (e.g. /health)",
    )
    health_check_interval: int = Field(
        30,
        ge=5,
        description="Seconds between health checks",
    )


class BackendPoolUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    algorithm: Optional[_ALGORITHMS] = None
    backends: Optional[List[BackendEntry]] = None
    health_check_url: Optional[str] = None
    health_check_interval: Optional[int] = Field(None, ge=5)


class BackendPoolOut(BaseModel):
    id: int
    api_id: Optional[int] = None
    name: str
    algorithm: str
    backends: List[Dict[str, Any]]
    health_check_url: Optional[str] = None
    health_check_interval: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_obj(cls, p: BackendPool) -> "BackendPoolOut":
        return cls(
            id=p.id,
            api_id=p.api_id,
            name=p.name,
            algorithm=p.algorithm,
            backends=p.backends or [],
            health_check_url=p.health_check_url,
            health_check_interval=p.health_check_interval or 30,
            created_at=p.created_at.isoformat() if p.created_at else None,
            updated_at=p.updated_at.isoformat() if p.updated_at else None,
        )


class BackendHealthPatch(BaseModel):
    healthy: bool = Field(...,
                          description="Set backend healthy (true) or unhealthy (false)")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_api_or_404(api_id: int, db: AsyncSession) -> API:
    result = await db.execute(select(API).where(API.id == api_id))
    api = result.scalar_one_or_none()
    if not api:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API {api_id} not found",
        )
    return api


async def _get_pool_or_404(api_id: int, pool_id: int, db: AsyncSession) -> BackendPool:
    result = await db.execute(
        select(BackendPool).where(
            BackendPool.id == pool_id,
            BackendPool.api_id == api_id,
        )
    )
    pool = result.scalar_one_or_none()
    if not pool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backend pool {pool_id} not found for API {api_id}",
        )
    return pool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/{api_id}/backend-pools",
    response_model=BackendPoolOut,
    status_code=status.HTTP_201_CREATED,
    summary="Attach a backend pool to an API",
)
async def create_pool(
    api_id: int,
    payload: BackendPoolCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:update")),
) -> BackendPoolOut:
    """Create a backend pool and attach it to an API.

    The gateway will use the **first** pool (lowest id) for load balancing.
    Once a pool is attached, the gateway uses it instead of the static
    ``config.target_url``.  Requests are routed to healthy backends only.
    """
    await _get_api_or_404(api_id, db)

    pool = BackendPool(
        api_id=api_id,
        name=payload.name,
        algorithm=payload.algorithm,
        backends=[b.model_dump() for b in payload.backends],
        health_check_url=payload.health_check_url,
        health_check_interval=payload.health_check_interval,
    )
    db.add(pool)
    await db.commit()
    await db.refresh(pool)
    logger.info("Created backend pool id=%s for api_id=%s", pool.id, api_id)
    return BackendPoolOut.from_orm_obj(pool)


@router.get(
    "/{api_id}/backend-pools",
    response_model=List[BackendPoolOut],
    summary="List backend pools for an API",
)
async def list_pools(
    api_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:read")),
) -> List[BackendPoolOut]:
    """Return all backend pools attached to the given API, ordered by id."""
    await _get_api_or_404(api_id, db)
    result = await db.execute(
        select(BackendPool)
        .where(BackendPool.api_id == api_id)
        .order_by(BackendPool.id)
    )
    pools = result.scalars().all()
    return [BackendPoolOut.from_orm_obj(p) for p in pools]


@router.get(
    "/{api_id}/backend-pools/{pool_id}",
    response_model=BackendPoolOut,
    summary="Get a single backend pool",
)
async def get_pool(
    api_id: int,
    pool_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:read")),
) -> BackendPoolOut:
    """Retrieve a single backend pool by id."""
    pool = await _get_pool_or_404(api_id, pool_id, db)
    return BackendPoolOut.from_orm_obj(pool)


@router.put(
    "/{api_id}/backend-pools/{pool_id}",
    response_model=BackendPoolOut,
    summary="Update a backend pool",
)
async def update_pool(
    api_id: int,
    pool_id: int,
    payload: BackendPoolUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:update")),
) -> BackendPoolOut:
    """Update a pool's algorithm, backends list, or health check configuration.

    Only fields present in the payload are updated (partial update).
    Replacing ``backends`` atomically swaps the entire backends list.
    """
    pool = await _get_pool_or_404(api_id, pool_id, db)
    if payload.name is not None:
        pool.name = payload.name
    if payload.algorithm is not None:
        pool.algorithm = payload.algorithm
    if payload.backends is not None:
        pool.backends = [b.model_dump() for b in payload.backends]
    if payload.health_check_url is not None:
        pool.health_check_url = payload.health_check_url
    if payload.health_check_interval is not None:
        pool.health_check_interval = payload.health_check_interval
    await db.commit()
    await db.refresh(pool)
    logger.info("Updated backend pool id=%s for api_id=%s", pool_id, api_id)
    return BackendPoolOut.from_orm_obj(pool)


@router.delete(
    "/{api_id}/backend-pools/{pool_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a backend pool",
)
async def delete_pool(
    api_id: int,
    pool_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:update")),
) -> None:
    """Permanently delete a backend pool.

    Once deleted the gateway falls back to the API's static ``config.target_url``.
    """
    pool = await _get_pool_or_404(api_id, pool_id, db)
    await db.delete(pool)
    await db.commit()
    logger.info("Deleted backend pool id=%s for api_id=%s", pool_id, api_id)


@router.patch(
    "/{api_id}/backend-pools/{pool_id}/backends/{url:path}/health",
    response_model=BackendPoolOut,
    summary="Mark a backend healthy or unhealthy",
)
async def patch_backend_health(
    api_id: int,
    pool_id: int,
    url: str = Path(..., description="URL-encoded backend url"),
    payload: BackendHealthPatch = ...,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:update")),
) -> BackendPoolOut:
    """Toggle the ``healthy`` flag on a single backend within a pool.

    Use this to manually take a backend out of rotation (``healthy: false``)
    without removing it, or to reinstate it (``healthy: true``).

    **url** must be URL-encoded in the path, e.g.:
    ``PATCH /apis/1/backend-pools/2/backends/http%3A%2F%2Fhost%3A8080/health``
    """
    pool = await _get_pool_or_404(api_id, pool_id, db)
    decoded_url = unquote(url)

    backends: List[Dict[str, Any]] = list(pool.backends or [])
    matched = False
    for backend in backends:
        if backend.get("url") == decoded_url:
            backend["healthy"] = payload.healthy
            matched = True
            break

    if not matched:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Backend '{decoded_url}' not found in pool {pool_id}",
        )

    pool.backends = backends
    await db.commit()
    await db.refresh(pool)
    logger.info(
        "Backend '%s' in pool id=%s marked %s",
        decoded_url,
        pool_id,
        "healthy" if payload.healthy else "unhealthy",
    )
    return BackendPoolOut.from_orm_obj(pool)
