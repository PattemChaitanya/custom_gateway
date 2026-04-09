"""
L2 — SQLite store (T4.2).

Uses aiosqlite with a single `kv_store` table:
  entity_type TEXT, entity_id TEXT, data TEXT (JSON), updated_at TEXT
  PRIMARY KEY (entity_type, entity_id)

Availability is detected on first use: if the DB file can't be opened,
is_available() returns False and no further reads/writes are attempted.

This tier is the durable fallback when PostgreSQL is down.  The sync job
(T4.6) drains it back into PostgreSQL once the primary comes back.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import aiosqlite

from .backend import EntityId, EntityType

logger = logging.getLogger(__name__)

SQLITE_PATH = os.getenv("TIERED_SQLITE_PATH", "tiered_store.db")


class SQLiteStore:
    """L2 aiosqlite-backed store."""

    tier_name = "L2-sqlite"

    def __init__(self, db_path: str = SQLITE_PATH) -> None:
        self._path = db_path
        self._db: Optional[aiosqlite.Connection] = None
        self._available = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def open(self) -> None:
        """Connect and create schema if needed. Sets _available."""
        try:
            self._db = await aiosqlite.connect(self._path)
            await self._db.execute("PRAGMA journal_mode=WAL")
            await self._db.execute("""
                CREATE TABLE IF NOT EXISTS kv_store (
                    entity_type TEXT NOT NULL,
                    entity_id   TEXT NOT NULL,
                    data        TEXT NOT NULL,
                    updated_at  TEXT NOT NULL,
                    PRIMARY KEY (entity_type, entity_id)
                )
            """)
            await self._db.execute(
                "CREATE INDEX IF NOT EXISTS idx_kv_entity_type ON kv_store(entity_type)"
            )
            await self._db.commit()
            self._available = True
            logger.info("SQLiteStore opened at %s", self._path)
        except Exception as exc:
            logger.warning("SQLiteStore unavailable: %s", exc)
            self._available = False

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None
        self._available = False

    # ── Protocol ──────────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        return self._available and self._db is not None

    async def get(
        self, entity_type: EntityType, entity_id: EntityId
    ) -> Optional[dict[str, Any]]:
        if not self.is_available():
            return None
        try:
            async with self._db.execute(  # type: ignore[union-attr]
                "SELECT data FROM kv_store WHERE entity_type=? AND entity_id=?",
                (entity_type, entity_id),
            ) as cursor:
                row = await cursor.fetchone()
                return json.loads(row[0]) if row else None
        except Exception as exc:
            logger.warning("SQLiteStore.get error: %s", exc)
            return None

    async def list(
        self, entity_type: EntityType, filters: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        if not self.is_available():
            return []
        try:
            async with self._db.execute(  # type: ignore[union-attr]
                "SELECT data FROM kv_store WHERE entity_type=?", (entity_type,)
            ) as cursor:
                rows = await cursor.fetchall()
            items = [json.loads(r[0]) for r in rows]
            if not filters:
                return items
            return [i for i in items if all(i.get(k) == v for k, v in filters.items())]
        except Exception as exc:
            logger.warning("SQLiteStore.list error: %s", exc)
            return []

    async def put(
        self, entity_type: EntityType, entity_id: EntityId, data: dict[str, Any]
    ) -> None:
        if not self.is_available():
            return
        try:
            now = datetime.now(timezone.utc).isoformat()
            await self._db.execute(  # type: ignore[union-attr]
                """
                INSERT INTO kv_store (entity_type, entity_id, data, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(entity_type, entity_id) DO UPDATE
                  SET data=excluded.data, updated_at=excluded.updated_at
                """,
                (entity_type, entity_id, json.dumps(data), now),
            )
            await self._db.commit()  # type: ignore[union-attr]
        except Exception as exc:
            logger.warning("SQLiteStore.put error: %s", exc)

    async def delete(
        self, entity_type: EntityType, entity_id: EntityId
    ) -> None:
        if not self.is_available():
            return
        try:
            await self._db.execute(  # type: ignore[union-attr]
                "DELETE FROM kv_store WHERE entity_type=? AND entity_id=?",
                (entity_type, entity_id),
            )
            await self._db.commit()  # type: ignore[union-attr]
        except Exception as exc:
            logger.warning("SQLiteStore.delete error: %s", exc)

    async def all_keys(self, entity_type: EntityType) -> list[EntityId]:
        if not self.is_available():
            return []
        try:
            async with self._db.execute(  # type: ignore[union-attr]
                "SELECT entity_id FROM kv_store WHERE entity_type=?", (entity_type,)
            ) as cursor:
                rows = await cursor.fetchall()
            return [r[0] for r in rows]
        except Exception as exc:
            logger.warning("SQLiteStore.all_keys error: %s", exc)
            return []

    async def drain(self) -> list[tuple[EntityType, EntityId, dict[str, Any]]]:
        """Return all rows — used by the sync job to flush L2 → L3."""
        if not self.is_available():
            return []
        try:
            async with self._db.execute(  # type: ignore[union-attr]
                "SELECT entity_type, entity_id, data FROM kv_store"
            ) as cursor:
                rows = await cursor.fetchall()
            return [(r[0], r[1], json.loads(r[2])) for r in rows]
        except Exception as exc:
            logger.warning("SQLiteStore.drain error: %s", exc)
            return []
