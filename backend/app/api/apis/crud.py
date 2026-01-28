from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...db import models


async def create_api(db: AsyncSession | object, payload: Dict[str, Any]) -> models.API | object:
    """Create an API either in the SQL DB or in the in-memory fallback.

    The `db` argument can be an AsyncSession or an InMemoryDB instance. We
    detect the latter by the presence of an attribute `in_memory` on the
    object.
    """
    # In-memory path
    if getattr(db, "in_memory", False):
        return await db.create_api(payload)

    # SQLAlchemy path
    # check for existing API with same name+version
    existing = await db.execute(
        select(models.API).where(models.API.name == payload.get("name"), models.API.version == payload.get("version"))
    )
    if existing.scalar_one_or_none() is not None:
        raise ValueError("API with same name and version already exists")

    api = models.API(
        name=payload.get("name"),
        version=payload.get("version"),
        description=payload.get("description"),
        owner_id=payload.get("owner_id"),
        config=payload.get("config"),
    )
    db.add(api)
    await db.commit()
    await db.refresh(api)
    return api


async def list_apis(db: AsyncSession | object) -> List[models.API] | List[object]:
    if getattr(db, "in_memory", False):
        return await db.list_apis()
    result = await db.execute(select(models.API))
    return result.scalars().all()


async def get_api(db: AsyncSession | object, api_id: int) -> Optional[models.API] | Optional[object]:
    if getattr(db, "in_memory", False):
        return await db.get_api(api_id)
    result = await db.execute(select(models.API).where(models.API.id == api_id))
    return result.scalar_one_or_none()


async def update_api(db: AsyncSession | object, api: models.API | object, patch: Dict[str, Any]) -> models.API | object:
    if getattr(db, "in_memory", False):
        return await db.update_api(api, patch)
    for k, v in patch.items():
        if v is not None and hasattr(api, k):
            setattr(api, k, v)
    db.add(api)
    await db.commit()
    await db.refresh(api)
    return api


async def delete_api(db: AsyncSession | object, api: models.API | object) -> None:
    if getattr(db, "in_memory", False):
        return await db.delete_api(api)
    await db.delete(api)
    await db.commit()

