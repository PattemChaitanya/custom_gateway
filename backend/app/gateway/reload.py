"""
reload.py — Trigger a hot-reload on a live gateway runtime instance.

Called after every gateway_routes CRUD mutation so the Node.js runtime
re-fetches its route table without restarting.

POST {gateway_url}/internal/reload
  Headers: X-Account-Secret: <secret>

Failure is non-fatal (T5.2): we log a warning and return False so the
CRUD caller can complete its response regardless.
"""

import logging
import os

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Instance

logger = logging.getLogger(__name__)

RELOAD_TIMEOUT_S = float(os.getenv("GATEWAY_RELOAD_TIMEOUT_S", "5"))


async def trigger_reload(account_id: int, db: AsyncSession) -> bool:
    """
    Fire POST {gateway_url}/internal/reload for the given account's instance.

    Returns True on success, False on any failure (network error, non-200,
    instance not found, etc.).  Never raises.
    """
    # Look up the running instance
    try:
        result = await db.execute(
            select(Instance).where(
                Instance.account_id == account_id,
                Instance.status == "running",
            )
        )
        instance = result.scalar_one_or_none()
    except Exception as exc:
        logger.warning("reload: DB lookup failed for account %d: %s", account_id, exc)
        return False

    if instance is None:
        # No running instance — nothing to reload (provisioning / stopped / expired)
        logger.debug("reload: no running instance for account %d — skipping", account_id)
        return False

    url = f"{instance.gateway_url}/internal/reload"

    # Retrieve the account secret from instance metadata
    # (stored in a future account_secret_hash column; fall back to env default)
    account_secret = os.getenv("GATEWAY_DEFAULT_SECRET", "")

    try:
        async with httpx.AsyncClient(timeout=RELOAD_TIMEOUT_S) as client:
            resp = await client.post(
                url,
                headers={"X-Account-Secret": account_secret},
            )
        if resp.status_code == 200:
            logger.info(
                "reload: account %d gateway reloaded (status=%d)",
                account_id, resp.status_code,
            )
            return True
        else:
            logger.warning(
                "reload: account %d gateway returned %d",
                account_id, resp.status_code,
            )
            return False
    except Exception as exc:
        # T5.2 — non-fatal: network error, container unreachable, etc.
        logger.warning(
            "reload: account %d gateway unreachable (%s) — CRUD succeeded anyway",
            account_id, exc,
        )
        return False
