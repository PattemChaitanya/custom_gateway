"""Account (tenant) management router.

Provides CRUD for the top-level Account entity.  Only superusers can create
or delete accounts; account members can read and update their own account.

Endpoints
---------
POST   /api/accounts          — create a new account  [superuser]
GET    /api/accounts          — list all accounts      [superuser]
GET    /api/accounts/{id}     — get account by id      [superuser | own account]
PUT    /api/accounts/{id}     — update account         [superuser | own account]
DELETE /api/accounts/{id}     — delete account         [superuser]
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.auth_dependency import get_current_user
from app.authorizers.rbac import require_permission
from app.db.connector import get_db
from app.db.models import Account
from app.gateway.metering import PLAN_QUOTAS, get_daily_count, next_midnight_utc
from app.gateway.instance_manager import provision_instance, ProvisionResult
from app.rate_limiter.dependencies import management_rate_limit
from app.security.api_keys import APIKeyManager


def _assert_account_access(current_user: dict, account_id: int) -> None:
    """Raise 403 unless caller is superuser or owns this account."""
    if current_user.get("is_superuser"):
        return
    if current_user.get("account_id") == account_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

router = APIRouter(
    prefix="/api/accounts",
    tags=["Accounts"],
    dependencies=[Depends(management_rate_limit)],
)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class AccountCreate(BaseModel):
    # Must start with a letter so numeric-only slugs (e.g. "123") are rejected.
    # This keeps gateway routing unambiguous: /gw/{account_slug}/{api_id}/...
    # where account_slug always starts with a-z and api_id is always an integer.
    slug: str = Field(..., min_length=1, max_length=63, pattern=r'^[a-z][a-z0-9\-]*$')
    name: str = Field(..., min_length=1, max_length=255)
    plan: str = Field(default="free", pattern=r'^(free|pro|enterprise)$')


class AccountUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    plan: Optional[str] = Field(None, pattern=r'^(free|pro|enterprise)$')
    status: Optional[str] = Field(None, pattern=r'^(active|suspended|deleted)$')


class AccountResponse(BaseModel):
    id: int
    slug: str
    name: str
    plan: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    model_config = {"from_attributes": True}


class AccountProvisionResponse(BaseModel):
    """Returned only on account creation — includes the one-time gateway credentials."""
    id: int
    slug: str
    name: str
    plan: str
    status: str
    gateway_url: str
    api_key: str           # plain-text key — only shown once
    expires_at: str        # ISO8601 — instance 48h TTL
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class UsageResponse(BaseModel):
    account_id: int
    slug: str
    plan: str
    # None for unlimited (enterprise)
    daily_quota: Optional[int]
    used_today: int
    # None for unlimited plans
    remaining: Optional[int]
    quota_resets_at: str


def _to_response(account: Account) -> AccountResponse:
    return AccountResponse(
        id=account.id,
        slug=account.slug,
        name=account.name,
        plan=account.plan,
        status=account.status,
        created_at=account.created_at.isoformat() if account.created_at else None,
        updated_at=account.updated_at.isoformat() if account.updated_at else None,
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=AccountProvisionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account (tenant) and provision its gateway instance",
)
async def create_account(
    body: AccountCreate,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("account:create")),
):
    # Reject duplicate slugs
    existing = await db.execute(select(Account).where(Account.slug == body.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Account with slug '{body.slug}' already exists.",
        )

    # Create account row
    account = Account(slug=body.slug, name=body.name, plan=body.plan)
    db.add(account)
    await db.commit()
    await db.refresh(account)

    # Generate the first API key for this account
    key_manager = APIKeyManager(db, account_id=account.id)
    key_data = await key_manager.create_api_key(
        label="default",
        scopes="gateway:request",
        metadata={"rate_limit_rpm": 100},
    )
    await db.commit()

    # Provision per-account Docker gateway instance
    try:
        result: ProvisionResult = await provision_instance(account.id, db)
    except Exception as exc:
        # Provisioning failed — account row stays but we surface the error
        # (admin can retry provisioning; account data is not lost)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Account created but gateway provisioning failed: {exc}",
        )

    return AccountProvisionResponse(
        id=account.id,
        slug=account.slug,
        name=account.name,
        plan=account.plan,
        status=account.status,
        gateway_url=result.gateway_url,
        api_key=key_data["key"],  # plain-text, only shown once
        expires_at=result.expires_at.isoformat(),
        created_at=account.created_at.isoformat() if account.created_at else None,
    )


@router.get(
    "",
    response_model=List[AccountResponse],
    summary="List all accounts",
)
async def list_accounts(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("account:read")),
):
    result = await db.execute(select(Account).order_by(Account.id))
    return [_to_response(a) for a in result.scalars().all()]


@router.get(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Get account by id",
)
async def get_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _assert_account_access(current_user, account_id)
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return _to_response(account)


@router.put(
    "/{account_id}",
    response_model=AccountResponse,
    summary="Update account name, plan, or status",
)
async def update_account(
    account_id: int,
    body: AccountUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _assert_account_access(current_user, account_id)
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    if body.name is not None:
        account.name = body.name
    # Only superusers can change plan/status
    if current_user.get("is_superuser"):
        if body.plan is not None:
            account.plan = body.plan
        if body.status is not None:
            account.status = body.status
    await db.commit()
    await db.refresh(account)
    return _to_response(account)


@router.get(
    "/{account_id}/usage",
    response_model=UsageResponse,
    summary="Get today's gateway request usage for an account",
)
async def get_account_usage(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _assert_account_access(current_user, account_id)
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    quota = PLAN_QUOTAS.get(account.plan, PLAN_QUOTAS["free"])
    count = await get_daily_count(db, account_id)
    remaining = max(0, quota - count) if quota > 0 else None

    return UsageResponse(
        account_id=account.id,
        slug=account.slug,
        plan=account.plan,
        daily_quota=quota if quota > 0 else None,
        used_today=count,
        remaining=remaining,
        quota_resets_at=next_midnight_utc().isoformat(),
    )


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an account and all its resources (CASCADE)",
)
async def delete_account(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("account:delete")),
):
    account = await db.get(Account, account_id)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    await db.delete(account)
    await db.commit()
