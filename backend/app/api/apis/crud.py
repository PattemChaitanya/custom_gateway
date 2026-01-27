from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...db import models


async def create_api(db: AsyncSession, payload: Dict[str, Any]) -> models.API:
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


async def list_apis(db: AsyncSession) -> List[models.API]:
    result = await db.execute(select(models.API))
    return result.scalars().all()


async def get_api(db: AsyncSession, api_id: int) -> Optional[models.API]:
    result = await db.execute(select(models.API).where(models.API.id == api_id))
    return result.scalar_one_or_none()


async def update_api(db: AsyncSession, api: models.API, patch: Dict[str, Any]) -> models.API:
    for k, v in patch.items():
        if v is not None and hasattr(api, k):
            setattr(api, k, v)
    db.add(api)
    await db.commit()
    await db.refresh(api)
    return api


async def delete_api(db: AsyncSession, api: models.API) -> None:
    await db.delete(api)
    await db.commit()

