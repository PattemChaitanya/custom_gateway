"""
Internal endpoints — called by gateway runtime containers, not by end users.

Authentication: X-Account-Secret header (must match the secret stored per-instance).
These endpoints are NOT exposed through the regular auth middleware.

GET  /internal/config/{account_id}  — called on runtime boot & /internal/reload
POST /internal/logs                 — batch request log ingestion from gateways
"""

import hashlib
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.connector import get_db
from app.db.models import API, APIKey, Instance

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["Internal"])


# ── Auth helper ───────────────────────────────────────────────────────────────

async def _verify_account_secret(
    account_id: int,
    db: AsyncSession,
    x_account_secret: Optional[str],
) -> Instance:
    """Raise 403 if secret header is missing or doesn't match the stored secret."""
    if not x_account_secret:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing X-Account-Secret")

    result = await db.execute(
        select(Instance).where(Instance.account_id == account_id)
    )
    instance = result.scalar_one_or_none()
    if not instance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Instance not found")

    # Secret is stored in a metadata field we'll add; for now we compare via hash
    # stored in instance.account_secret_hash
    if not _check_secret(x_account_secret, instance):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid account secret")

    return instance


def _check_secret(provided: str, instance: Instance) -> bool:
    """Compare the provided secret against the stored hash."""
    stored = getattr(instance, "account_secret_hash", None)
    if not stored:
        # No secret stored yet — allow during initial provisioning window
        return True
    provided_hash = hashlib.sha256(provided.encode()).hexdigest()
    return provided_hash == stored


# ── Schemas ───────────────────────────────────────────────────────────────────

class ApiKeyConfig(BaseModel):
    id: int
    account_id: Optional[int]
    key_hash: str
    name: str
    rate_limit_rpm: int

    model_config = {"from_attributes": True}


class RouteConfig(BaseModel):
    id: int
    account_id: Optional[int]
    path: str
    method: str
    target_url: str
    auth_required: bool
    validation_schema: Optional[dict]
    active: bool

    model_config = {"from_attributes": True}


class AccountConfigResponse(BaseModel):
    account_id: int
    routes: List[RouteConfig]
    api_keys: List[ApiKeyConfig]


class LogEntry(BaseModel):
    id: str
    account_id: int
    route_id: Optional[str]
    method: str
    path: str
    status_code: int
    latency_ms: int
    api_key_id: Optional[str]
    timestamp: str


class LogBatch(BaseModel):
    logs: List[LogEntry]


# ── GET /internal/config/{account_id} ────────────────────────────────────────

@router.get(
    "/config/{account_id}",
    response_model=AccountConfigResponse,
    summary="Fetch routes and API keys for a gateway runtime (called on boot/reload)",
)
async def get_account_config(
    account_id: int,
    x_account_secret: Optional[str] = Header(None, alias="X-Account-Secret"),
    db: AsyncSession = Depends(get_db),
):
    await _verify_account_secret(account_id, db, x_account_secret)

    # Load active gateway routes for this account
    # Routes are stored in the GatewayRoute table (created in migration 0010).
    # If that table doesn't exist yet, fall back gracefully.
    routes: list[RouteConfig] = []
    try:
        from app.db.models import GatewayRoute  # noqa: PLC0415
        result = await db.execute(
            select(GatewayRoute).where(
                GatewayRoute.account_id == account_id,
                GatewayRoute.active == True,  # noqa: E712
            )
        )
        for r in result.scalars().all():
            routes.append(RouteConfig(
                id=r.id,
                account_id=r.account_id,
                path=r.path,
                method=r.method,
                target_url=r.target_url,
                auth_required=r.auth_required,
                validation_schema=r.validation_schema,
                active=r.active,
            ))
    except Exception:
        pass  # GatewayRoute table not yet migrated — return empty routes

    # Load API keys for this account
    api_keys: list[ApiKeyConfig] = []
    result = await db.execute(
        select(APIKey).where(
            APIKey.account_id == account_id,
            APIKey.revoked == False,  # noqa: E712
        )
    )
    for k in result.scalars().all():
        # Extract rate_limit_rpm from metadata if stored there
        rpm = 100
        if k.metadata_json and isinstance(k.metadata_json, dict):
            rpm = int(k.metadata_json.get("rate_limit_rpm", 100))
        api_keys.append(ApiKeyConfig(
            id=k.id,
            account_id=k.account_id,
            key_hash=k.key,  # already stored as SHA256 hash
            name=k.label or "",
            rate_limit_rpm=rpm,
        ))

    return AccountConfigResponse(
        account_id=account_id,
        routes=routes,
        api_keys=api_keys,
    )


# ── POST /internal/logs ───────────────────────────────────────────────────────

@router.post(
    "/logs",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Receive batched request logs from a gateway runtime",
)
async def ingest_logs(
    body: LogBatch,
    x_account_secret: Optional[str] = Header(None, alias="X-Account-Secret"),
    x_account_id: Optional[str] = Header(None, alias="X-Account-Id"),
    db: AsyncSession = Depends(get_db),
):
    if not x_account_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing X-Account-Id")

    account_id = int(x_account_id)
    await _verify_account_secret(account_id, db, x_account_secret)

    if not body.logs:
        return

    # Bulk INSERT into request_logs (T6.2).
    # Uses SQLAlchemy Core insert() for a single round-trip instead of
    # individual ORM flushes.  Gracefully skips if table doesn't exist yet.
    try:
        from datetime import datetime
        from sqlalchemy import insert
        from app.db.models import RequestLog  # noqa: PLC0415

        rows = [
            {
                "account_id": account_id,
                "route_id": int(entry.route_id) if entry.route_id else None,
                "method": entry.method,
                "path": entry.path,
                "status_code": entry.status_code,
                "latency_ms": entry.latency_ms,
                "timestamp": datetime.fromisoformat(entry.timestamp),
            }
            for entry in body.logs
        ]

        await db.execute(insert(RequestLog), rows)
        await db.commit()
        logger.debug("Bulk-inserted %d logs for account %d", len(rows), account_id)
    except Exception as exc:
        logger.warning("Log ingestion skipped (table may not exist yet): %s", exc)
