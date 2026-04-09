"""
Instance status endpoint — used by the frontend Dashboard to display:
  - Instance status badge (provisioning / running / stopped / expired)
  - Gateway URL (copyable)
  - Time remaining until 48h expiry

GET /api/instances/{account_id}
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.auth_dependency import get_current_user
from app.db.connector import get_db
from app.db.models import Instance
from app.storage.tiered_store import get_store

router = APIRouter(prefix="/api/instances", tags=["Instances"])


class InstanceResponse(BaseModel):
    id: int
    account_id: int
    container_id: Optional[str]
    port: int
    status: str
    gateway_url: str
    created_at: Optional[str]
    expires_at: str
    # Seconds remaining until expiry. Negative means already expired.
    expires_in_seconds: int

    model_config = {"from_attributes": True}


def _to_response(instance: Instance) -> InstanceResponse:
    now = datetime.now(timezone.utc)
    expires_at = instance.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    expires_in = int((expires_at - now).total_seconds())

    return InstanceResponse(
        id=instance.id,
        account_id=instance.account_id,
        container_id=instance.container_id,
        port=instance.port,
        status=instance.status,
        gateway_url=instance.gateway_url,
        created_at=instance.created_at.isoformat() if instance.created_at else None,
        expires_at=expires_at.isoformat(),
        expires_in_seconds=expires_in,
    )


def _assert_access(current_user: dict, account_id: int) -> None:
    if current_user.get("is_superuser"):
        return
    if current_user.get("account_id") == account_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


@router.get(
    "/{account_id}",
    response_model=InstanceResponse,
    summary="Get gateway instance status and TTL for an account",
)
async def get_instance_status(
    account_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _assert_access(current_user, account_id)

    # L1/L2 fast path — avoids a DB round-trip on every Dashboard poll
    cached = await get_store().get("instance", str(account_id))
    if cached:
        now = datetime.now(timezone.utc)
        expires_at_str = cached.get("expires_at", "")
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            expires_in = int((expires_at - now).total_seconds())
        except Exception:
            expires_in = 0
        return InstanceResponse(
            id=cached["id"],
            account_id=cached["account_id"],
            container_id=cached.get("container_id"),
            port=cached["port"],
            status=cached["status"],
            gateway_url=cached["gateway_url"],
            created_at=None,
            expires_at=expires_at_str,
            expires_in_seconds=expires_in,
        )

    # L3 fallback — read from DB and warm the store
    result = await db.execute(
        select(Instance).where(Instance.account_id == account_id)
    )
    instance = result.scalar_one_or_none()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No instance found for this account")

    response = _to_response(instance)

    # Warm store for next call
    await get_store().put("instance", str(account_id), {
        "id": instance.id,
        "account_id": instance.account_id,
        "container_id": instance.container_id,
        "port": instance.port,
        "status": instance.status,
        "gateway_url": instance.gateway_url,
        "expires_at": response.expires_at,
    })

    return response
