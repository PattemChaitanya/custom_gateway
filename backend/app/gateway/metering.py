"""Per-account usage metering and daily quota enforcement.

Plans and their daily request quotas
-------------------------------------
free       — 10 000 requests / day
pro        — 100 000 requests / day
enterprise — unlimited  (quota sentinel value: 0)

Usage is tracked via ``Metric`` rows with ``metric_type='gateway_request'``.
Quota is enforced by counting today's rows before the request is proxied.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Account, Metric
from app.logging_config import get_logger

logger = get_logger("gateway.metering")

# ---------------------------------------------------------------------------
# Plan quotas
# ---------------------------------------------------------------------------

# Daily request limits per plan.  0 = unlimited (enterprise).
PLAN_QUOTAS: dict[str, int] = {
    "free": 10_000,
    "pro": 100_000,
    "enterprise": 0,
}

_DEFAULT_QUOTA = PLAN_QUOTAS["free"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _today_utc() -> datetime:
    """UTC midnight of the current day (start of quota window)."""
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def next_midnight_utc() -> datetime:
    """UTC midnight of the next day (quota window reset time)."""
    return _today_utc() + timedelta(days=1)


async def get_daily_count(db: AsyncSession, account_id: int) -> int:
    """Return the number of gateway requests recorded for *account_id* since
    UTC midnight today."""
    result = await db.execute(
        select(func.count(Metric.id)).where(
            Metric.account_id == account_id,
            Metric.metric_type == "gateway_request",
            Metric.timestamp >= _today_utc(),
        )
    )
    return result.scalar_one() or 0


# ---------------------------------------------------------------------------
# Quota enforcement
# ---------------------------------------------------------------------------

async def check_quota(db: AsyncSession, account: Account) -> None:
    """Raise HTTP 429 if *account* has exhausted its daily request quota.

    Enterprise accounts (quota=0) are never blocked.
    Called as step 0 of the gateway pipeline, before any expensive checks.
    """
    quota = PLAN_QUOTAS.get(account.plan, _DEFAULT_QUOTA)
    if quota == 0:
        return  # unlimited plan

    count = await get_daily_count(db, account.id)
    if count >= quota:
        reset = next_midnight_utc()
        retry_after = int((reset - datetime.now(timezone.utc)).total_seconds())
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": "daily_quota_exceeded",
                "account": account.slug,
                "plan": account.plan,
                "daily_quota": quota,
                "used_today": count,
                "quota_resets_at": reset.isoformat(),
            },
            headers={"Retry-After": str(retry_after)},
        )


# ---------------------------------------------------------------------------
# Metric recording
# ---------------------------------------------------------------------------

async def record_request(
    db: AsyncSession,
    *,
    account_id: Optional[int],
    api_id: Optional[int],
    status_code: int,
    latency_ms: int,
    method: Optional[str] = None,
    endpoint: Optional[str] = None,
) -> None:
    """Write a ``gateway_request`` Metric row for usage metering.

    Errors are swallowed — metering must never block or fail the response
    that has already been assembled for the client.
    """
    try:
        db.add(Metric(
            account_id=account_id,
            api_id=api_id,
            metric_type="gateway_request",
            status_code=status_code,
            latency_ms=latency_ms,
            method=method,
            endpoint=endpoint,
        ))
        await db.commit()
    except Exception as exc:
        logger.warning("Metric write failed (non-fatal): %s", exc)
        await db.rollback()
