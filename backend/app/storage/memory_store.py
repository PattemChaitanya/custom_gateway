"""
L1 — In-memory store (T4.1).

Holds a flat dict-of-dicts: { entity_type: { entity_id: data_dict } }.
All operations are synchronous under the hood but wrapped in async so
the StorageBackend protocol is satisfied.

This store is always available (never raises, never returns None for is_available).
Data is lost on process restart — that's fine; L2/L3 are the truth stores.
"""

from __future__ import annotations

from typing import Any, Optional
from .backend import EntityId, EntityType


class MemoryStore:
    """L1 in-memory store — dict-backed, zero-latency reads."""

    tier_name = "L1-memory"

    def __init__(self) -> None:
        # { entity_type: { entity_id: data } }
        self._store: dict[str, dict[str, dict[str, Any]]] = {}

    def is_available(self) -> bool:
        return True

    def _ns(self, entity_type: EntityType) -> dict[str, dict[str, Any]]:
        if entity_type not in self._store:
            self._store[entity_type] = {}
        return self._store[entity_type]

    async def get(
        self, entity_type: EntityType, entity_id: EntityId
    ) -> Optional[dict[str, Any]]:
        return self._ns(entity_type).get(entity_id)

    async def list(
        self, entity_type: EntityType, filters: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        rows = list(self._ns(entity_type).values())
        if not filters:
            return rows
        return [
            r for r in rows
            if all(r.get(k) == v for k, v in filters.items())
        ]

    async def put(
        self, entity_type: EntityType, entity_id: EntityId, data: dict[str, Any]
    ) -> None:
        self._ns(entity_type)[entity_id] = dict(data)

    async def delete(
        self, entity_type: EntityType, entity_id: EntityId
    ) -> None:
        self._ns(entity_type).pop(entity_id, None)

    async def all_keys(self, entity_type: EntityType) -> list[EntityId]:
        return list(self._ns(entity_type).keys())

    def clear(self, entity_type: Optional[str] = None) -> None:
        """Evict all entries for one type (or entire store if None)."""
        if entity_type:
            self._store.pop(entity_type, None)
        else:
            self._store.clear()
