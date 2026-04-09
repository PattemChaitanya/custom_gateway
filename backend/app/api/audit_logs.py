"""Audit log query endpoints."""

import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, delete, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.auth_dependency import get_current_user
from app.authorizers.rbac import RBACManager
from app.db.connector import get_db
from app.db.models import AuditLog, User
from app.logging.cleanup import get_log_statistics
from app.logging_config import get_logger

logger = get_logger("audit_logs")

router = APIRouter(prefix="/api/audit-logs", tags=["Audit Logs"])

# ---------------------------------------------------------------------------
# Retention configuration
# ---------------------------------------------------------------------------
# Set AUDIT_LOG_RETENTION_DAYS=0 to disable automatic purging.
_RETENTION_DAYS = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "90"))
_PURGE_INTERVAL_HOURS = float(os.getenv("AUDIT_LOG_PURGE_INTERVAL_HOURS", "24"))


async def purge_old_audit_logs(db: AsyncSession, retention_days: int) -> int:
    """Delete audit logs older than *retention_days*.  Returns the row count deleted."""
    if retention_days <= 0:
        return 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    result = await db.execute(
        delete(AuditLog).where(AuditLog.timestamp < cutoff)
    )
    await db.commit()
    deleted = result.rowcount
    if deleted:
        logger.info("Audit log retention: purged %d rows older than %d days", deleted, retention_days)
    return deleted


async def run_audit_log_retention_loop(get_db_fn, stop_event: asyncio.Event) -> None:
    """Background loop that periodically purges old audit logs."""
    if _RETENTION_DAYS <= 0:
        logger.info("Audit log retention disabled (AUDIT_LOG_RETENTION_DAYS=0)")
        return
    interval_seconds = _PURGE_INTERVAL_HOURS * 3600
    logger.info(
        "Audit log retention loop started: %d-day TTL, purge every %.1fh",
        _RETENTION_DAYS, _PURGE_INTERVAL_HOURS,
    )
    while not stop_event.is_set():
        try:
            async for db in get_db_fn():
                await purge_old_audit_logs(db, _RETENTION_DAYS)
                break
        except Exception as exc:
            logger.warning("Audit log retention purge failed: %s", exc)
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except asyncio.TimeoutError:
            pass  # Normal — interval elapsed, loop again


async def require_audit_visibility(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Allow users with `audit:read` or legacy `api:list` visibility."""
    if getattr(current_user, "is_superuser", False):
        return current_user

    user_id = getattr(current_user, "id", None)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not resolve authenticated user",
        )

    manager = RBACManager(db)
    if await manager.user_has_permission(user_id, "audit:read"):
        return current_user
    if await manager.user_has_permission(user_id, "api:list"):
        return current_user

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Forbidden: 'audit:read' permission required",
    )


def _parse_optional_datetime(value: Optional[str], field_name: str) -> Optional[datetime]:
    if value is None:
        return None

    raw = value.strip()
    if not raw:
        return None

    try:
        normalized = raw.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid '{field_name}' format. Use ISO 8601 datetime.",
        ) from exc


def _serialize_audit_log(row: AuditLog) -> dict:
    timestamp = row.timestamp
    if isinstance(timestamp, str):
        ts_value = timestamp
    else:
        ts_value = timestamp.isoformat() if timestamp else None

    return {
        "id": row.id,
        "timestamp": ts_value,
        "user_id": row.user_id,
        "action": row.action,
        "resource_type": row.resource_type,
        "resource_id": row.resource_id,
        "ip_address": row.ip_address,
        "user_agent": row.user_agent,
        "metadata_json": row.metadata_json,
        "status": row.status,
        "error_message": row.error_message,
    }


@router.get("")
async def list_audit_logs(
    user_id: Optional[int] = Query(default=None),
    action: Optional[str] = Query(default=None),
    status_filter: Optional[str] = Query(default=None, alias="status"),
    start_date: Optional[str] = Query(default=None),
    end_date: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_audit_visibility),
):
    """List audit logs with optional filters."""
    if hasattr(db, "list_audit_logs"):
        rows = await db.list_audit_logs(
            user_id=user_id,
            action=action,
            status=status_filter,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        return [_serialize_audit_log(row) for row in rows]

    start_dt = _parse_optional_datetime(start_date, "start_date")
    end_dt = _parse_optional_datetime(end_date, "end_date")

    clauses = []
    # Non-superusers only see their own account's logs
    account_id = getattr(_current_user, "account_id", None)
    is_super = getattr(_current_user, "is_superuser", False)
    if account_id is not None and not is_super:
        clauses.append(AuditLog.account_id == account_id)
    if user_id is not None:
        clauses.append(AuditLog.user_id == user_id)
    if action and action.strip():
        clauses.append(func.lower(AuditLog.action) == action.strip().lower())
    if status_filter and status_filter.strip():
        clauses.append(func.lower(AuditLog.status) ==
                       status_filter.strip().lower())
    if start_dt is not None:
        clauses.append(AuditLog.timestamp >= start_dt)
    if end_dt is not None:
        clauses.append(AuditLog.timestamp <= end_dt)

    stmt = select(AuditLog)
    if clauses:
        stmt = stmt.where(and_(*clauses))

    stmt = stmt.order_by(desc(AuditLog.timestamp)).limit(limit)
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [_serialize_audit_log(row) for row in rows]


@router.get("/statistics")
async def audit_log_statistics(
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_audit_visibility),
):
    """Get aggregate statistics for audit logs."""
    if hasattr(db, "get_audit_log_statistics"):
        stats = await db.get_audit_log_statistics()
    else:
        stats = await get_log_statistics(db)
    return {
        "total_logs": stats.get("total_logs", 0),
        "logs_by_type": stats.get("logs_by_type", {}),
        "logs_by_user": stats.get("logs_by_user", {}),
    }


@router.get("/user/{target_user_id}")
async def user_activity(
    target_user_id: int,
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=500, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_audit_visibility),
):
    """Get activity for a specific user over the last `days` days."""
    if hasattr(db, "list_user_audit_activity"):
        rows = await db.list_user_audit_activity(
            target_user_id=target_user_id,
            days=days,
            limit=limit,
        )
        return [_serialize_audit_log(row) for row in rows]

    since = datetime.now(timezone.utc) - timedelta(days=days)

    account_id = getattr(_current_user, "account_id", None)
    is_super = getattr(_current_user, "is_superuser", False)
    clauses = [AuditLog.user_id == target_user_id, AuditLog.timestamp >= since]
    if account_id is not None and not is_super:
        clauses.append(AuditLog.account_id == account_id)

    stmt = (
        select(AuditLog)
        .where(and_(*clauses))
        .order_by(desc(AuditLog.timestamp))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [_serialize_audit_log(row) for row in rows]


@router.delete("/purge", summary="Purge audit logs older than N days (superusers only)")
async def purge_audit_logs(
    retention_days: int = Query(
        default=None,
        ge=1,
        description=(
            "Delete logs older than this many days. "
            f"Defaults to AUDIT_LOG_RETENTION_DAYS env var ({_RETENTION_DAYS})."
        ),
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually trigger audit log retention purge.  Superusers only."""
    if not getattr(current_user, "is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: superuser required to purge audit logs",
        )
    days = retention_days if retention_days is not None else _RETENTION_DAYS
    if days <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="retention_days must be >= 1",
        )
    deleted = await purge_old_audit_logs(db, days)
    return {"deleted_rows": deleted, "retention_days": days}


@router.get("/failed")
async def failed_attempts(
    hours: int = Query(default=24, ge=1, le=24 * 30),
    limit: int = Query(default=500, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _current_user: User = Depends(require_audit_visibility),
):
    """Get failed/error audit events over the last `hours` hours."""
    if hasattr(db, "list_failed_audit_attempts"):
        rows = await db.list_failed_audit_attempts(hours=hours, limit=limit)
        return [_serialize_audit_log(row) for row in rows]

    since = datetime.now(timezone.utc) - timedelta(hours=hours)

    failed_predicate = or_(
        func.lower(AuditLog.status).in_(["failure", "error"]),
        func.lower(AuditLog.action).like("%failure%"),
    )

    account_id = getattr(_current_user, "account_id", None)
    is_super = getattr(_current_user, "is_superuser", False)
    time_and_error = and_(AuditLog.timestamp >= since, failed_predicate)
    if account_id is not None and not is_super:
        where_clause = and_(time_and_error, AuditLog.account_id == account_id)
    else:
        where_clause = time_and_error

    stmt = (
        select(AuditLog)
        .where(where_clause)
        .order_by(desc(AuditLog.timestamp))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [_serialize_audit_log(row) for row in rows]
