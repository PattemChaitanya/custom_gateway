"""
L3 — PostgreSQL store (T4.3).

Wraps the existing DatabaseManager/AsyncSession. Availability is determined
by whether db_manager.is_using_primary is True.

Reads and writes go through the normal SQLAlchemy ORM for the three
hot-path entity types: instance, route, api_key.
For other entity types it falls back gracefully (returns None / []).
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from .backend import EntityId, EntityType

logger = logging.getLogger(__name__)


class PostgresStore:
    """L3 PostgreSQL store — delegates to the existing db_manager session."""

    tier_name = "L3-postgres"

    def __init__(self) -> None:
        # Lazily imported to avoid circular imports at module load time
        self._manager = None

    def _get_manager(self):
        if self._manager is None:
            from app.db.db_manager import get_db_manager
            self._manager = get_db_manager()
        return self._manager

    def is_available(self) -> bool:
        try:
            return self._get_manager().is_using_primary
        except Exception:
            return False

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _get_session(self):
        """Yield one AsyncSession from the manager."""
        manager = self._get_manager()
        if not manager.is_using_primary or not manager.session_factory:
            return None
        return manager.session_factory()

    async def get(
        self, entity_type: EntityType, entity_id: EntityId
    ) -> Optional[dict[str, Any]]:
        if not self.is_available():
            return None
        session = await self._get_session()
        if not session:
            return None
        try:
            async with session:
                return await _pg_get(session, entity_type, entity_id)
        except Exception as exc:
            logger.warning("PostgresStore.get error (%s/%s): %s", entity_type, entity_id, exc)
            return None

    async def list(
        self, entity_type: EntityType, filters: Optional[dict[str, Any]] = None
    ) -> list[dict[str, Any]]:
        if not self.is_available():
            return []
        session = await self._get_session()
        if not session:
            return []
        try:
            async with session:
                return await _pg_list(session, entity_type, filters)
        except Exception as exc:
            logger.warning("PostgresStore.list error (%s): %s", entity_type, exc)
            return []

    async def put(
        self, entity_type: EntityType, entity_id: EntityId, data: dict[str, Any]
    ) -> None:
        if not self.is_available():
            return
        session = await self._get_session()
        if not session:
            return
        try:
            async with session:
                await _pg_put(session, entity_type, entity_id, data)
                await session.commit()
        except Exception as exc:
            logger.warning("PostgresStore.put error (%s/%s): %s", entity_type, entity_id, exc)

    async def delete(
        self, entity_type: EntityType, entity_id: EntityId
    ) -> None:
        if not self.is_available():
            return
        session = await self._get_session()
        if not session:
            return
        try:
            async with session:
                await _pg_delete(session, entity_type, entity_id)
                await session.commit()
        except Exception as exc:
            logger.warning("PostgresStore.delete error (%s/%s): %s", entity_type, entity_id, exc)

    async def all_keys(self, entity_type: EntityType) -> list[EntityId]:
        rows = await self.list(entity_type)
        return [str(r.get("id", "")) for r in rows if r.get("id")]


# ── ORM helpers (one per hot-path entity type) ────────────────────────────────

async def _pg_get(session, entity_type: str, entity_id: str) -> Optional[dict]:
    from sqlalchemy import select
    model = _model_for(entity_type)
    if model is None:
        return None
    obj = await session.get(model, int(entity_id))
    return _to_dict(obj) if obj else None


async def _pg_list(session, entity_type: str, filters: Optional[dict]) -> list[dict]:
    from sqlalchemy import select
    model = _model_for(entity_type)
    if model is None:
        return []
    stmt = select(model)
    if filters:
        for k, v in filters.items():
            if hasattr(model, k):
                stmt = stmt.where(getattr(model, k) == v)
    result = await session.execute(stmt)
    return [_to_dict(r) for r in result.scalars().all()]


async def _pg_put(session, entity_type: str, entity_id: str, data: dict) -> None:
    model = _model_for(entity_type)
    if model is None:
        return
    obj = await session.get(model, int(entity_id))
    if obj is None:
        obj = model()
        session.add(obj)
    for k, v in data.items():
        if hasattr(obj, k):
            try:
                setattr(obj, k, v)
            except Exception:
                pass


async def _pg_delete(session, entity_type: str, entity_id: str) -> None:
    model = _model_for(entity_type)
    if model is None:
        return
    obj = await session.get(model, int(entity_id))
    if obj:
        await session.delete(obj)


def _model_for(entity_type: str):
    """Return the SQLAlchemy model class for a given entity type, or None."""
    try:
        from app.db.models import Instance, APIKey
        _map = {
            "instance": Instance,
            "api_key": APIKey,
        }
        # GatewayRoute added after migration 0010
        try:
            from app.db.models import GatewayRoute
            _map["route"] = GatewayRoute
        except ImportError:
            pass
        return _map.get(entity_type)
    except Exception:
        return None


def _to_dict(obj) -> dict:
    """Shallow dict from a SQLAlchemy model instance (non-private attrs only)."""
    result = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name, None)
        # Convert datetime to ISO string for JSON safety
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        result[col.name] = val
    return result
