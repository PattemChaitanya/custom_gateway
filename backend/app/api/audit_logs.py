"""Audit log query endpoints."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.auth_dependency import get_current_user
from app.authorizers.rbac import RBACManager
from app.db.connector import get_db
from app.db.models import AuditLog, User
from app.logging.cleanup import get_log_statistics

router = APIRouter(prefix="/api/audit-logs", tags=["Audit Logs"])


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

    stmt = (
        select(AuditLog)
        .where(and_(AuditLog.user_id == target_user_id, AuditLog.timestamp >= since))
        .order_by(desc(AuditLog.timestamp))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [_serialize_audit_log(row) for row in rows]


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

    stmt = (
        select(AuditLog)
        .where(and_(AuditLog.timestamp >= since, failed_predicate))
        .order_by(desc(AuditLog.timestamp))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [_serialize_audit_log(row) for row in rows]
