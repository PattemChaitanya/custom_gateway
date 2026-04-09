"""
StorageBackend Protocol — T4 abstraction layer.

Every storage tier (L1 memory, L2 SQLite, L3 PostgreSQL) implements this
protocol so the TieredStore can treat them uniformly.

Entity keys are (entity_type, id) pairs, e.g. ("instance", 42) or
("route", "abc-123").  Values are plain dicts (JSON-serialisable).

Typed helpers for the three hot-path entity types are defined at the bottom.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable


EntityType = str   # "instance" | "route" | "api_key"
EntityId   = str   # str(int) or UUID string — always stored as str


@runtime_checkable
class StorageBackend(Protocol):
    """Read / write / delete interface that all tiers must satisfy."""

    # Name used in log messages
    tier_name: str

    def is_available(self) -> bool:
        """Return True if this tier can accept reads and writes right now."""
        ...

    async def get(
        self, entity_type: EntityType, entity_id: EntityId
    ) -> Optional[dict[str, Any]]:
        """Return the stored dict, or None if not found."""
        ...

    async def list(
        self, entity_type: EntityType, filters: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        """Return all entities of the given type, optionally filtered."""
        ...

    async def put(
        self, entity_type: EntityType, entity_id: EntityId, data: dict[str, Any]
    ) -> None:
        """Upsert the dict at (entity_type, entity_id)."""
        ...

    async def delete(
        self, entity_type: EntityType, entity_id: EntityId
    ) -> None:
        """Remove the entity; no-op if it doesn't exist."""
        ...

    async def all_keys(
        self, entity_type: EntityType
    ) -> list[EntityId]:
        """Return all stored IDs for the given entity type."""
        ...
