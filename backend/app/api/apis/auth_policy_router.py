"""Auth policy management routes.

Mounted on the APIs router at:
    POST   /apis/{api_id}/auth-policies
    GET    /apis/{api_id}/auth-policies
    GET    /apis/{api_id}/auth-policies/{policy_id}
    PUT    /apis/{api_id}/auth-policies/{policy_id}
    DELETE /apis/{api_id}/auth-policies/{policy_id}

Policy types and their ``config`` schemas
-----------------------------------------
**none / open**
    No config required.  The gateway passes all requests through.

**apiKey**
    ``config`` (all optional):
    {
        "header_name":          "X-API-Key",   # default
        "scope_to_environment": true            # only accept keys assigned to
                                                # the API's deployed env
    }

**jwt / bearer**
    ``config`` (all optional):
    {
        "issuer":   "https://auth.example.com",
        "audience": "my-api",
        "secret":   "${secret:jwt_signing_secret}"  # or plain value
    }
    When ``secret`` is set the gateway uses *that* secret instead of the
    global JWT_SECRET env var.  Use a ``${secret:<name>}`` ref to keep it
    out of the DB in plain text.

**oauth2**
    ``config`` (required: token_introspection_url):
    {
        "token_introspection_url": "https://auth.server/introspect",
        "client_id":               "${secret:oauth_client_id}",
        "client_secret":           "${secret:oauth_client_secret}"
    }
    The gateway POSTs {token, token_type_hint=access_token} with HTTP Basic
    auth using client_id:client_secret and expects
    ``{ "active": true, ... }``.
"""

from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.authorizers.rbac import require_permission
from app.db.connector import get_db
from app.db.models import API, AuthPolicy
from app.logging_config import get_logger

logger = get_logger("gateway.auth_policy_router")

router = APIRouter(tags=["auth-policies"])

_POLICY_TYPES = Literal["none", "open", "apiKey", "jwt", "bearer", "oauth2"]


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AuthPolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: _POLICY_TYPES = Field(..., description="Auth mechanism type")
    config: Optional[dict] = Field(
        None,
        description=(
            "Type-specific configuration. "
            "See module docstring for per-type schema."
        ),
    )


class AuthPolicyUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[_POLICY_TYPES] = None
    config: Optional[dict] = None


class AuthPolicyOut(BaseModel):
    id: int
    api_id: int
    name: str
    type: str
    config: Optional[dict] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_obj(cls, p: AuthPolicy) -> "AuthPolicyOut":
        return cls(
            id=p.id,
            api_id=p.api_id,
            name=p.name,
            type=p.type,
            config=p.config,
            created_at=p.created_at.isoformat() if p.created_at else None,
            updated_at=p.updated_at.isoformat() if p.updated_at else None,
        )


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


async def _get_policy_or_404(api_id: int, policy_id: int, db: AsyncSession) -> AuthPolicy:
    result = await db.execute(
        select(AuthPolicy).where(
            AuthPolicy.id == policy_id,
            AuthPolicy.api_id == api_id,
        )
    )
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Auth policy {policy_id} not found for API {api_id}",
        )
    return policy


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.post(
    "/{api_id}/auth-policies",
    response_model=AuthPolicyOut,
    status_code=status.HTTP_201_CREATED,
    summary="Attach an auth policy to an API",
)
async def create_auth_policy(
    api_id: int,
    payload: AuthPolicyCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:update")),
) -> AuthPolicyOut:
    """Create and attach an authentication policy to an API.

    The gateway enforces the **first** policy (lowest id) on every inbound
    proxy request.  Multiple policies may exist; only the primary is enforced.

    Supported types: ``none``, ``open``, ``apiKey``, ``jwt``/``bearer``, ``oauth2``.
    """
    await _get_api_or_404(api_id, db)
    policy = AuthPolicy(
        api_id=api_id,
        name=payload.name,
        type=payload.type,
        config=payload.config or {},
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    logger.info("Auth policy %s (%s) created for API %s",
                policy.id, policy.type, api_id)
    return AuthPolicyOut.from_orm_obj(policy)


@router.get(
    "/{api_id}/auth-policies",
    response_model=List[AuthPolicyOut],
    summary="List auth policies for an API",
)
async def list_auth_policies(
    api_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:read")),
) -> List[AuthPolicyOut]:
    await _get_api_or_404(api_id, db)
    result = await db.execute(
        select(AuthPolicy)
        .where(AuthPolicy.api_id == api_id)
        .order_by(AuthPolicy.id)
    )
    policies = result.scalars().all()
    return [AuthPolicyOut.from_orm_obj(p) for p in policies]


@router.get(
    "/{api_id}/auth-policies/{policy_id}",
    response_model=AuthPolicyOut,
    summary="Get a single auth policy",
)
async def get_auth_policy(
    api_id: int,
    policy_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:read")),
) -> AuthPolicyOut:
    policy = await _get_policy_or_404(api_id, policy_id, db)
    return AuthPolicyOut.from_orm_obj(policy)


@router.put(
    "/{api_id}/auth-policies/{policy_id}",
    response_model=AuthPolicyOut,
    summary="Update an auth policy",
)
async def update_auth_policy(
    api_id: int,
    policy_id: int,
    payload: AuthPolicyUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:update")),
) -> AuthPolicyOut:
    policy = await _get_policy_or_404(api_id, policy_id, db)
    if payload.name is not None:
        policy.name = payload.name
    if payload.type is not None:
        policy.type = payload.type
    if payload.config is not None:
        policy.config = payload.config
    await db.commit()
    await db.refresh(policy)
    logger.info("Auth policy %s updated for API %s", policy_id, api_id)
    return AuthPolicyOut.from_orm_obj(policy)


@router.delete(
    "/{api_id}/auth-policies/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove an auth policy from an API",
)
async def delete_auth_policy(
    api_id: int,
    policy_id: int,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("api:update")),
) -> None:
    policy = await _get_policy_or_404(api_id, policy_id, db)
    await db.delete(policy)
    await db.commit()
    logger.info("Auth policy %s deleted from API %s", policy_id, api_id)
