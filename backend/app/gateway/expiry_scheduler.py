"""
expiry_scheduler.py — Background job that reaps expired gateway instances.

Runs every 5 minutes via APScheduler. For each Instance where:
  - expires_at <= now  AND  status IN ('running', 'provisioning')

It will:
  1. Stop + remove the Docker container
  2. Set status = 'expired' in the DB

Also exposes `get_instance_status()` used by the /api/instances/{account_id}
endpoint so the frontend can poll instance state + time remaining.
"""

import asyncio
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Instance
from app.gateway.instance_manager import deprovision_instance

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


# ── Scheduler lifecycle ───────────────────────────────────────────────────────

def start_expiry_scheduler(get_db_session) -> None:
    """
    Start the APScheduler job. Call once from the FastAPI lifespan handler.

    `get_db_session` must be an async generator / callable that yields an
    AsyncSession — i.e. the same `get_db` dependency used elsewhere.
    """
    global _scheduler
    if _scheduler and _scheduler.running:
        return

    _scheduler = AsyncIOScheduler(timezone="UTC")
    _scheduler.add_job(
        _reap_expired_instances,
        trigger="interval",
        minutes=5,
        id="reap_expired_instances",
        replace_existing=True,
        args=[get_db_session],
    )
    _scheduler.start()
    logger.info("Instance expiry scheduler started (interval=5min)")


def stop_expiry_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Instance expiry scheduler stopped")


# ── Core reap job (T3.2) ──────────────────────────────────────────────────────

async def _reap_expired_instances(get_db_session) -> None:
    """Find all expired instances and deprovision them."""
    now = datetime.now(timezone.utc)
    logger.debug("Checking for expired instances (now=%s)", now.isoformat())

    async for db in get_db_session():
        try:
            result = await db.execute(
                select(Instance).where(
                    Instance.expires_at <= now,
                    Instance.status.in_(["running", "provisioning"]),
                )
            )
            expired = result.scalars().all()

            if not expired:
                logger.debug("No expired instances found")
                return

            logger.info("Reaping %d expired instance(s)", len(expired))
            for instance in expired:
                try:
                    await deprovision_instance(instance, db, new_status="expired")
                    logger.info(
                        "Expired instance id=%d account=%d container=%s",
                        instance.id, instance.account_id, instance.container_id,
                    )
                except Exception as exc:
                    logger.error(
                        "Failed to reap instance id=%d: %s",
                        instance.id, exc,
                    )
        except Exception as exc:
            logger.error("Expiry reap job failed: %s", exc)
        break  # only consume one session from the generator
