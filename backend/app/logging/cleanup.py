"""Cleanup script for old logs (30-day retention)."""

from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import AuditLog, Metric
from app.logging_config import get_logger

logger = get_logger("cleanup")


async def cleanup_old_logs(session: AsyncSession, retention_days: int = 30) -> int:
    """Clean up logs older than retention period.
    
    Args:
        session: Database session
        retention_days: Number of days to retain logs (default 30)
    
    Returns:
        int: Number of audit logs deleted
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=retention_days)
    
    # Clean up audit logs
    audit_count_query = await session.execute(
        select(func.count(AuditLog.id)).where(AuditLog.timestamp < cutoff_date)
    )
    audit_count = audit_count_query.scalar() or 0
    
    await session.execute(
        delete(AuditLog).where(AuditLog.timestamp < cutoff_date)
    )
    
    # Clean up metrics
    metrics_count_query = await session.execute(
        select(func.count(Metric.id)).where(Metric.timestamp < cutoff_date)
    )
    metrics_count = metrics_count_query.scalar() or 0
    
    await session.execute(
        delete(Metric).where(Metric.timestamp < cutoff_date)
    )
    
    await session.commit()
    
    logger.info(
        f"Cleaned up old logs: {audit_count} audit logs, {metrics_count} metrics",
        audit_logs_deleted=audit_count,
        metrics_deleted=metrics_count,
        retention_days=retention_days,
    )
    
    # Return just the audit count for test compatibility
    return audit_count


async def get_log_statistics(session: AsyncSession) -> dict:
    """Get statistics about stored logs."""
    # Audit logs count
    audit_total = await session.execute(select(func.count(AuditLog.id)))
    audit_count = audit_total.scalar() or 0
    
    # Metrics count
    metrics_total = await session.execute(select(func.count(Metric.id)))
    metrics_count = metrics_total.scalar() or 0
    
    # Get logs by action type
    logs_by_type_query = await session.execute(
        select(AuditLog.action, func.count(AuditLog.id)).group_by(AuditLog.action)
    )
    logs_by_type = {row[0]: row[1] for row in logs_by_type_query.all()}
    
    # Get logs by user
    logs_by_user_query = await session.execute(
        select(AuditLog.user_id, func.count(AuditLog.id))
        .where(AuditLog.user_id.isnot(None))
        .group_by(AuditLog.user_id)
    )
    logs_by_user = {row[0]: row[1] for row in logs_by_user_query.all()}
    
    # Oldest log dates
    oldest_audit = await session.execute(
        select(func.min(AuditLog.timestamp))
    )
    oldest_audit_date = oldest_audit.scalar()
    
    oldest_metric = await session.execute(
        select(func.min(Metric.timestamp))
    )
    oldest_metric_date = oldest_metric.scalar()
    
    return {
        "total_logs": audit_count,  # For test compatibility
        "audit_logs_count": audit_count,
        "metrics_count": metrics_count,
        "logs_by_type": logs_by_type,
        "logs_by_user": logs_by_user,
        "oldest_audit_log": oldest_audit_date.isoformat() if oldest_audit_date else None,
        "oldest_metric": oldest_metric_date.isoformat() if oldest_metric_date else None,
    }
