"""Rate limit management routes.

Mounted on the APIs router at:
    POST   /apis/{api_id}/rate-limits
    GET    /apis/{api_id}/rate-limits
    GET    /apis/{api_id}/rate-limits/{rl_id}
    PUT    /apis/{api_id}/rate-limits/{rl_id}
    DELETE /apis/{api_id}/rate-limits/{rl_id}
"""

from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorizers.rbac import require_permission
from app.db.connector import get_db
from app.logging_config import get_logger
from app.rate_limiter.manager import RateLimitManager

logger = get_logger("gateway.rate_limit_router")

router = APIRouter(tags=["rate-limits"])

# Valid literals enforced at the API layer
_ALGORITHMS = Literal["fixed_window", "sliding_window", "token_bucket"]
_KEY_TYPES = Literal["global", "per-ip", "per-key"]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class RateLimitCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100,
                      description="Human-readable label")
    key_type: _KEY_TYPES = Field("global", description="Bucketing strategy")
    algorithm: _ALGORITHMS = Field(
        "fixed_window", description="Algorithm to use")
    limit: int = Field(..., ge=1, le=1_000_000,
                       description="Max requests per window")
    window_seconds: int = Field(..., ge=1, le=86_400,
                                description="Window size in seconds")


class RateLimitUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    key_type: Optional[_KEY_TYPES] = None
    algorithm: Optional[_ALGORITHMS] = None
    limit: Optional[int] = Field(None, ge=1, le=1_000_000)
    window_seconds: Optional[int] = Field(None, ge=1, le=86_400)


class RateLimitOut(BaseModel):
    id: int
    api_id: int
    name: str
    key_type: str
    algorithm: str
    limit: int
    window_seconds: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_obj(cls, rl) -> "RateLimitOut":
        return cls(
            id=rl.id,
            api_id=rl.api_id,
            name=rl.name,
            key_type=rl.key_type,
            algorithm=getattr(rl, "algorithm", "fixed_window"),
            limit=rl.limit,
            window_seconds=rl.window_seconds,
            created_at=rl.created_at.isoformat() if rl.created_at else None,
            updated_at=rl.updated_at.isoformat() if rl.updated_at else None,
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_api_or_404(api_id: int, db: AsyncSession):
    from sqlalchemy import select
    from app.db.models import API
    result = await db.execute(select(API).where(API.id == api_id))
    api = result.scalar_one_or_none()
    if not api:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API {api_id} not found",
        )
    return api


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/{api_id}/rate-limits",
    response_model=RateLimitOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a rate limit to an API",
)
async def create_rate_limit(
    api_id: int,
    payload: RateLimitCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:update")),
) -> RateLimitOut:
    """Attach a rate-limit policy to an API.

    Multiple rate-limits can exist per API. The gateway will enforce the
    **first** matching rule (ordered by insertion order, i.e. lowest id).
    Typical setup: one global rule + an optional per-ip burst rule.
    """
    await _get_api_or_404(api_id, db)
    mgr = RateLimitManager(db)
    rl = await mgr.create_rate_limit(
        api_id=api_id,
        name=payload.name,
        key_type=payload.key_type,
        limit=payload.limit,
        window_seconds=payload.window_seconds,
    )
    # Persist algorithm separately (manager predates the column)
    rl.algorithm = payload.algorithm
    await db.commit()
    await db.refresh(rl)
    logger.info("Rate limit %s created for API %s (algo=%s)",
                rl.id, api_id, rl.algorithm)
    return RateLimitOut.from_orm_obj(rl)


@router.get(
    "/{api_id}/rate-limits",
    response_model=List[RateLimitOut],
    summary="List rate limits for an API",
)
async def list_rate_limits(
    api_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:read")),
) -> List[RateLimitOut]:
    await _get_api_or_404(api_id, db)
    mgr = RateLimitManager(db)
    rls = await mgr.get_rate_limits_for_api(api_id)
    return [RateLimitOut.from_orm_obj(rl) for rl in rls]


@router.get(
    "/{api_id}/rate-limits/{rl_id}",
    response_model=RateLimitOut,
    summary="Get a single rate limit record",
)
async def get_rate_limit(
    api_id: int,
    rl_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:read")),
) -> RateLimitOut:
    await _get_api_or_404(api_id, db)
    mgr = RateLimitManager(db)
    rl = await mgr.get_rate_limit(rl_id)
    if not rl or rl.api_id != api_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rate limit {rl_id} not found for API {api_id}",
        )
    return RateLimitOut.from_orm_obj(rl)


@router.put(
    "/{api_id}/rate-limits/{rl_id}",
    response_model=RateLimitOut,
    summary="Update a rate limit",
)
async def update_rate_limit(
    api_id: int,
    rl_id: int,
    payload: RateLimitUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:update")),
) -> RateLimitOut:
    await _get_api_or_404(api_id, db)
    mgr = RateLimitManager(db)
    rl = await mgr.get_rate_limit(rl_id)
    if not rl or rl.api_id != api_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rate limit {rl_id} not found for API {api_id}",
        )

    update_kwargs = {}
    if payload.name is not None:
        update_kwargs["name"] = payload.name
    if payload.key_type is not None:
        update_kwargs["key_type"] = payload.key_type
    if payload.limit is not None:
        update_kwargs["limit"] = payload.limit
    if payload.window_seconds is not None:
        update_kwargs["window_seconds"] = payload.window_seconds
    if payload.algorithm is not None:
        update_kwargs["algorithm"] = payload.algorithm

    rl = await mgr.update_rate_limit(rl_id, **update_kwargs)
    logger.info("Rate limit %s updated for API %s", rl_id, api_id)
    return RateLimitOut.from_orm_obj(rl)


@router.delete(
    "/{api_id}/rate-limits/{rl_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a rate limit",
)
async def delete_rate_limit(
    api_id: int,
    rl_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:update")),
) -> None:
    await _get_api_or_404(api_id, db)
    mgr = RateLimitManager(db)
    rl = await mgr.get_rate_limit(rl_id)
    if not rl or rl.api_id != api_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Rate limit {rl_id} not found for API {api_id}",
        )
    await mgr.delete_rate_limit(rl_id)
    logger.info("Rate limit %s deleted from API %s", rl_id, api_id)
