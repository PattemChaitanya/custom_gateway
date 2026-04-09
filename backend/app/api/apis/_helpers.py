"""Shared helpers for APIs sub-routers."""

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import API


async def get_api_or_404(
    db: AsyncSession,
    api_id: int,
    account_id: Optional[int] = None,
) -> API:
    """Load an API by id, optionally scoped to *account_id*.

    Raises HTTP 404 when:
    - the API does not exist, OR
    - ``account_id`` is provided and the API belongs to a different account.

    Superusers pass ``account_id=None`` to skip the tenant check.
    """
    stmt = select(API).where(API.id == api_id)
    if account_id is not None:
        stmt = stmt.where(API.account_id == account_id)
    result = await db.execute(stmt)
    api = result.scalar_one_or_none()
    if not api:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API {api_id} not found",
        )
    return api
