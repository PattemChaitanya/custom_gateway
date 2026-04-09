"""
Request logs query API — used by the frontend Metrics page (T8).

Endpoints
---------
GET /api/request-logs
    ?account_id=<int>   filter by account (superuser only without own context)
    ?hours=24           lookback window in hours (default 24, max 168)
    ?limit=500          max rows returned (default 500, max 5000)

GET /api/request-logs/summary
    Aggregated data for the Metrics page:
      - requests_over_time: [{bucket, count}]  (hourly buckets, last 24h)
      - status_breakdown:   {2xx, 4xx, 5xx, other}
      - slowest_routes:     [{path, avg_latency_ms, count}]  top-5
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth.auth_dependency import get_current_user
from app.db.connector import get_db
from app.db.models import RequestLog

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/request-logs", tags=["Request Logs"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class LogRow(BaseModel):
    id: int
    account_id: int
    route_id: Optional[int]
    method: str
    path: str
    status_code: int
    latency_ms: int
    timestamp: str

    model_config = {"from_attributes": True}


class HourlyBucket(BaseModel):
    bucket: str   # ISO hour string, e.g. "2026-04-03T14:00:00+00:00"
    count: int


class StatusBreakdown(BaseModel):
    s2xx: int
    s4xx: int
    s5xx: int
    other: int


class SlowestRoute(BaseModel):
    path: str
    method: str
    avg_latency_ms: float
    count: int


class LogsSummary(BaseModel):
    requests_over_time: List[HourlyBucket]
    status_breakdown: StatusBreakdown
    slowest_routes: List[SlowestRoute]
    total_requests: int
    avg_latency_ms: float
    error_rate: float   # % of 4xx+5xx


# ── Helpers ───────────────────────────────────────────────────────────────────

def _account_id_for_user(current_user: dict) -> Optional[int]:
    return current_user.get("account_id")


def _assert_access(current_user: dict, account_id: int) -> None:
    if current_user.get("is_superuser"):
        return
    if current_user.get("account_id") == account_id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _since(hours: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=hours)


# ── GET /api/request-logs ─────────────────────────────────────────────────────

@router.get("", response_model=List[LogRow])
async def list_logs(
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=500, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    account_id = _account_id_for_user(current_user)
    since = _since(hours)

    stmt = (
        select(RequestLog)
        .where(RequestLog.timestamp >= since)
        .order_by(RequestLog.timestamp.desc())
        .limit(limit)
    )
    if account_id and not current_user.get("is_superuser"):
        stmt = stmt.where(RequestLog.account_id == account_id)

    result = await db.execute(stmt)
    rows = result.scalars().all()
    return [
        LogRow(
            id=r.id,
            account_id=r.account_id,
            route_id=r.route_id,
            method=r.method,
            path=r.path,
            status_code=r.status_code,
            latency_ms=r.latency_ms,
            timestamp=r.timestamp.isoformat() if r.timestamp else "",
        )
        for r in rows
    ]


# ── GET /api/request-logs/summary ─────────────────────────────────────────────

@router.get("/summary", response_model=LogsSummary)
async def logs_summary(
    hours: int = Query(default=24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    account_id = _account_id_for_user(current_user)
    since = _since(hours)

    def _scope(stmt):
        s = stmt.where(RequestLog.timestamp >= since)
        if account_id and not current_user.get("is_superuser"):
            s = s.where(RequestLog.account_id == account_id)
        return s

    # ── Total requests + avg latency ──────────────────────────────────────────
    agg = await db.execute(
        _scope(
            select(
                func.count(RequestLog.id).label("total"),
                func.avg(RequestLog.latency_ms).label("avg_lat"),
            )
        )
    )
    agg_row = agg.one()
    total: int = agg_row.total or 0
    avg_lat: float = round(float(agg_row.avg_lat or 0), 1)

    # ── Hourly buckets ────────────────────────────────────────────────────────
    # Use date_trunc on PostgreSQL; fall back to strftime on SQLite
    dialect = db.bind.dialect.name if db.bind else "postgresql"  # type: ignore[union-attr]

    if dialect == "postgresql":
        bucket_expr = func.date_trunc("hour", RequestLog.timestamp)
    else:
        # SQLite: truncate to hour via strftime
        bucket_expr = func.strftime("%Y-%m-%dT%H:00:00", RequestLog.timestamp)

    hourly_result = await db.execute(
        _scope(
            select(
                bucket_expr.label("bucket"),
                func.count(RequestLog.id).label("count"),
            )
        )
        .group_by(bucket_expr)
        .order_by(bucket_expr)
    )
    requests_over_time = [
        HourlyBucket(
            bucket=row.bucket.isoformat() if hasattr(row.bucket, "isoformat") else str(row.bucket),
            count=row.count,
        )
        for row in hourly_result
    ]

    # ── Status breakdown ──────────────────────────────────────────────────────
    status_result = await db.execute(
        _scope(
            select(
                RequestLog.status_code,
                func.count(RequestLog.id).label("cnt"),
            )
        )
        .group_by(RequestLog.status_code)
    )
    s2xx = s4xx = s5xx = other = 0
    for row in status_result:
        code: int = row.status_code
        cnt: int = row.cnt
        if 200 <= code < 300:
            s2xx += cnt
        elif 400 <= code < 500:
            s4xx += cnt
        elif 500 <= code < 600:
            s5xx += cnt
        else:
            other += cnt

    error_rate = round((s4xx + s5xx) / max(total, 1) * 100, 1)

    # ── Top 5 slowest routes ──────────────────────────────────────────────────
    slowest_result = await db.execute(
        _scope(
            select(
                RequestLog.path,
                RequestLog.method,
                func.avg(RequestLog.latency_ms).label("avg_lat"),
                func.count(RequestLog.id).label("cnt"),
            )
        )
        .group_by(RequestLog.path, RequestLog.method)
        .order_by(func.avg(RequestLog.latency_ms).desc())
        .limit(5)
    )
    slowest_routes = [
        SlowestRoute(
            path=row.path,
            method=row.method,
            avg_latency_ms=round(float(row.avg_lat or 0), 1),
            count=row.cnt,
        )
        for row in slowest_result
    ]

    return LogsSummary(
        requests_over_time=requests_over_time,
        status_breakdown=StatusBreakdown(s2xx=s2xx, s4xx=s4xx, s5xx=s5xx, other=other),
        slowest_routes=slowest_routes,
        total_requests=total,
        avg_latency_ms=avg_lat,
        error_rate=error_rate,
    )
