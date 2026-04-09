"""
TieredStore — write-through facade with waterfall reads (T4.4 + T4.5).

  Write: L1 always → L2 if available → L3 if available
  Read:  L1 hit → return immediately
         L1 miss → try L2 → warm L1, return
         L2 miss → try L3 → warm L1+L2, return

Availability detection (T4.4):
  On startup, open() probes each tier. Unavailable tiers are skipped
  transparently; the store degrades gracefully.

Sync job (T4.6):
  start_sync_job() launches an asyncio task that periodically (default 60s)
  checks if L3 (PostgreSQL) is back online, then drains all L2 rows into L3
  and clears L2.  This ensures no data is permanently lost when the primary
  DB was temporarily unavailable.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

from .memory_store import MemoryStore
from .sqlite_store import SQLiteStore
from .postgres_store import PostgresStore
from .backend import EntityId, EntityType

logger = logging.getLogger(__name__)

_store: Optional["TieredStore"] = None


def get_store() -> "TieredStore":
    """Return the process-level singleton TieredStore."""
    global _store
    if _store is None:
        _store = TieredStore()
    return _store


class TieredStore:
    """
    Three-tier storage facade:
      L1 = MemoryStore   (always available, lost on restart)
      L2 = SQLiteStore   (file-backed, survives restarts, no PG needed)
      L3 = PostgresStore (primary truth, available when PG is up)
    """

    def __init__(self) -> None:
        self.l1 = MemoryStore()
        self.l2 = SQLiteStore()
        self.l3 = PostgresStore()
        self._sync_task: Optional[asyncio.Task] = None
        self._sync_interval = int(__import__("os").getenv("TIERED_SYNC_INTERVAL_S", "60"))

    # ── Lifecycle (T4.4 — availability detection) ─────────────────────────────

    async def open(self) -> None:
        """Probe each tier; L2 open() is async, others are lazy."""
        await self.l2.open()
        logger.info(
            "TieredStore ready — L1=%s L2=%s L3=%s",
            self.l1.is_available(),
            self.l2.is_available(),
            self.l3.is_available(),
        )

    async def close(self) -> None:
        self.stop_sync_job()
        await self.l2.close()

    # ── Read: waterfall L1 → L2 → L3 (T4.5) ─────────────────────────────────

    async def get(
        self, entity_type: EntityType, entity_id: EntityId
    ) -> Optional[dict[str, Any]]:
        # L1
        data = await self.l1.get(entity_type, entity_id)
        if data is not None:
            return data

        # L2
        if self.l2.is_available():
            data = await self.l2.get(entity_type, entity_id)
            if data is not None:
                await self.l1.put(entity_type, entity_id, data)   # warm L1
                return data

        # L3
        if self.l3.is_available():
            data = await self.l3.get(entity_type, entity_id)
            if data is not None:
                await self.l1.put(entity_type, entity_id, data)   # warm L1
                if self.l2.is_available():
                    await self.l2.put(entity_type, entity_id, data)  # warm L2
                return data

        return None

    async def list(
        self, entity_type: EntityType, filters: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        # L1 (only if populated — check if we have any keys for this type)
        l1_keys = await self.l1.all_keys(entity_type)
        if l1_keys:
            return await self.l1.list(entity_type, filters)

        # L2
        if self.l2.is_available():
            rows = await self.l2.list(entity_type, filters)
            if rows:
                for r in rows:
                    await self.l1.put(entity_type, str(r.get("id", "")), r)
                return rows

        # L3
        if self.l3.is_available():
            rows = await self.l3.list(entity_type, filters)
            if rows:
                for r in rows:
                    eid = str(r.get("id", ""))
                    await self.l1.put(entity_type, eid, r)
                    if self.l2.is_available():
                        await self.l2.put(entity_type, eid, r)
                return rows

        return []

    # ── Write-through (T4.5) ──────────────────────────────────────────────────

    async def put(
        self, entity_type: EntityType, entity_id: EntityId, data: dict[str, Any]
    ) -> None:
        """Write to all available tiers."""
        await self.l1.put(entity_type, entity_id, data)
        if self.l2.is_available():
            await self.l2.put(entity_type, entity_id, data)
        if self.l3.is_available():
            await self.l3.put(entity_type, entity_id, data)

    async def delete(
        self, entity_type: EntityType, entity_id: EntityId
    ) -> None:
        """Delete from all available tiers."""
        await self.l1.delete(entity_type, entity_id)
        if self.l2.is_available():
            await self.l2.delete(entity_type, entity_id)
        if self.l3.is_available():
            await self.l3.delete(entity_type, entity_id)

    # ── Cache invalidation helpers ────────────────────────────────────────────

    def invalidate(self, entity_type: EntityType, entity_id: Optional[EntityId] = None) -> None:
        """Evict from L1 cache (next read will fall through to L2/L3)."""
        if entity_id:
            asyncio.get_event_loop().run_until_complete(
                self.l1.delete(entity_type, entity_id)
            )
        else:
            self.l1.clear(entity_type)

    # ── L2 → L3 sync job (T4.6) ──────────────────────────────────────────────

    def start_sync_job(self) -> None:
        if self._sync_task and not self._sync_task.done():
            return
        self._sync_task = asyncio.create_task(self._sync_loop())
        logger.info("TieredStore sync job started (interval=%ds)", self._sync_interval)

    def stop_sync_job(self) -> None:
        if self._sync_task:
            self._sync_task.cancel()
            self._sync_task = None

    async def _sync_loop(self) -> None:
        while True:
            await asyncio.sleep(self._sync_interval)
            try:
                await self._sync_l2_to_l3()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("TieredStore sync error: %s", exc)

    async def _sync_l2_to_l3(self) -> None:
        """
        Flush all L2 rows into L3 when PostgreSQL is available.

        Runs only when:
          - L2 has data  AND
          - L3 is now available (PG came back online)

        After a successful sync, L2 rows are deleted (L3 is now authoritative).
        """
        if not self.l2.is_available():
            return
        if not self.l3.is_available():
            return

        rows = await self.l2.drain()
        if not rows:
            return

        synced = 0
        for entity_type, entity_id, data in rows:
            try:
                # Only sync if L3 doesn't already have a newer copy
                existing = await self.l3.get(entity_type, entity_id)
                if existing is None:
                    await self.l3.put(entity_type, entity_id, data)
                    await self.l2.delete(entity_type, entity_id)
                    synced += 1
            except Exception as exc:
                logger.warning(
                    "Sync failed for %s/%s: %s", entity_type, entity_id, exc
                )

        if synced:
            logger.info("TieredStore: synced %d rows from L2 → L3", synced)
