"""Metrics storage in database for historical data."""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Metric
from app.logging_config import get_logger

logger = get_logger("metrics_storage")


class MetricsStorage:
    """Storage manager for metrics in database."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def store_request_metric(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        latency_ms: int,
        api_id: Optional[int] = None,
        user_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Metric:
        """Store a request metric.

        Uses flush instead of commit so the caller (or the session
        context manager) can batch multiple writes in a single
        transaction, avoiding one DB round-trip per metric.
        """
        metric = Metric(
            timestamp=datetime.now(timezone.utc),
            metric_type="request",
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            latency_ms=latency_ms,
            api_id=api_id,
            user_id=user_id,
            metadata_json=metadata,
        )

        self.session.add(metric)
        await self.session.flush()
        return metric

    async def store_error_metric(
        self,
        endpoint: str,
        method: str,
        status_code: int,
        api_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Metric:
        """Store an error metric.

        Uses flush instead of commit so multiple metrics can be
        batched in a single transaction.
        """
        metric = Metric(
            timestamp=datetime.now(timezone.utc),
            metric_type="error",
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            api_id=api_id,
            metadata_json=metadata,
        )

        self.session.add(metric)
        await self.session.flush()
        return metric

    async def get_metrics_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        api_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get aggregated metrics summary."""
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=7)
        if not end_date:
            end_date = datetime.now(timezone.utc)

        # Build base query
        conditions = [
            Metric.timestamp >= start_date,
            Metric.timestamp <= end_date,
        ]
        if api_id:
            conditions.append(Metric.api_id == api_id)

        # Total requests
        total_requests = await self.session.execute(
            select(func.count(Metric.id)).where(
                and_(*conditions),
                Metric.metric_type == "request"
            )
        )

        # Average latency
        avg_latency = await self.session.execute(
            select(func.avg(Metric.latency_ms)).where(
                and_(*conditions),
                Metric.metric_type == "request",
                Metric.latency_ms.isnot(None)
            )
        )

        # Error count
        error_count = await self.session.execute(
            select(func.count(Metric.id)).where(
                and_(*conditions),
                Metric.status_code >= 400
            )
        )

        # Requests by status code
        status_distribution = await self.session.execute(
            select(
                Metric.status_code,
                func.count(Metric.id).label('count')
            ).where(
                and_(*conditions),
                Metric.metric_type == "request"
            ).group_by(Metric.status_code)
        )

        # Extract scalar values once to avoid consuming the result twice
        total_requests_count = total_requests.scalar() or 0
        avg_latency_value = avg_latency.scalar() or 0
        error_count_value = error_count.scalar() or 0

        return {
            "total_requests": total_requests_count,
            "average_latency_ms": round(avg_latency_value, 2),
            "error_count": error_count_value,
            "error_rate": round(error_count_value / max(total_requests_count, 1) * 100, 2),
            "status_distribution": {row[0]: row[1] for row in status_distribution.all()},
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

    async def get_endpoint_metrics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get metrics grouped by endpoint."""
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=7)
        if not end_date:
            end_date = datetime.now(timezone.utc)

        result = await self.session.execute(
            select(
                Metric.endpoint,
                Metric.method,
                func.count(Metric.id).label('request_count'),
                func.avg(Metric.latency_ms).label('avg_latency'),
                func.sum(
                    func.cast((Metric.status_code >= 400),
                              type_=func.INTEGER())
                ).label('error_count')
            ).where(
                and_(
                    Metric.timestamp >= start_date,
                    Metric.timestamp <= end_date,
                    Metric.metric_type == "request"
                )
            ).group_by(
                Metric.endpoint,
                Metric.method
            ).order_by(
                func.count(Metric.id).desc()
            ).limit(limit)
        )

        return [
            {
                "endpoint": row[0],
                "method": row[1],
                "request_count": row[2],
                "avg_latency_ms": round(row[3] or 0, 2),
                "error_count": row[4] or 0,
            }
            for row in result.all()
        ]

    async def get_latency_percentiles(
        self,
        endpoint: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, float]:
        """Calculate latency percentiles."""
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(hours=24)
        if not end_date:
            end_date = datetime.now(timezone.utc)

        conditions = [
            Metric.timestamp >= start_date,
            Metric.timestamp <= end_date,
            Metric.metric_type == "request",
            Metric.latency_ms.isnot(None)
        ]

        if endpoint:
            conditions.append(Metric.endpoint == endpoint)

        # Get total count first to calculate offsets
        count_result = await self.session.execute(
            select(func.count(Metric.id)).where(and_(*conditions))
        )
        total = count_result.scalar() or 0

        if total == 0:
            return {"p50": 0, "p90": 0, "p95": 0, "p99": 0}

        async def _percentile_at(p: float) -> float:
            """Fetch a single percentile value using SQL OFFSET/LIMIT.

            This avoids loading all rows into Python memory.
            """
            idx = int((total - 1) * p)
            row = await self.session.execute(
                select(Metric.latency_ms)
                .where(and_(*conditions))
                .order_by(Metric.latency_ms)
                .offset(idx)
                .limit(1)
            )
            val = row.scalar()
            return float(val) if val is not None else 0.0

        return {
            "p50": round(await _percentile_at(0.50), 2),
            "p90": round(await _percentile_at(0.90), 2),
            "p95": round(await _percentile_at(0.95), 2),
            "p99": round(await _percentile_at(0.99), 2),
        }
