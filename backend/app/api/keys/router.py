"""API Keys router and endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel, Field
from app.db.connector import get_db
from app.security.api_keys import APIKeyManager
from app.authorizers.rbac import require_permission
from app.db.models import User, APIKey, Environment
from app.security.api_keys import get_api_key_dependency

router = APIRouter(prefix="/api/keys", tags=["api-keys"])


class CreateAPIKeyRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=100)
    scopes: Optional[str] = Field(default="", max_length=500)
    environment_id: Optional[int] = None
    expires_in_days: Optional[int] = Field(default=None, ge=1, le=3650)


class APIKeyResponse(BaseModel):
    id: int
    key: Optional[str] = None  # Only returned on creation
    label: str
    scopes: str
    environment_id: Optional[int]
    revoked: bool
    created_at: str
    expires_at: Optional[str]
    last_used_at: Optional[str] = None
    usage_count: int = 0
    key_preview: Optional[str] = None


@router.post("/", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    payload: CreateAPIKeyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("key:create")),
):
    """Create a new API key. The actual key is only shown once!"""
    manager = APIKeyManager(db)
    result = await manager.create_api_key(
        label=payload.label,
        scopes=payload.scopes,
        environment_id=payload.environment_id,
        expires_in_days=payload.expires_in_days,
    )
    return result


@router.get("/", response_model=List[APIKeyResponse])
async def list_keys(
    environment_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("key:list")),
):
    """List all API keys (without showing actual key values)."""
    manager = APIKeyManager(db)
    keys = await manager.list_keys(environment_id=environment_id)
    return keys


@router.post("/{key_id}/revoke", status_code=status.HTTP_200_OK)
async def revoke_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("key:update")),
):
    """Revoke an API key."""
    manager = APIKeyManager(db)
    success = await manager.revoke_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"message": "API key revoked successfully"}


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("key:delete")),
):
    """Delete an API key permanently."""
    manager = APIKeyManager(db)
    success = await manager.delete_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")


@router.get("/{key_id}/stats", status_code=status.HTTP_200_OK)
async def get_key_stats(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permission("key:read")),
):
    """Get usage statistics for an API key."""
    manager = APIKeyManager(db)
    stats = await manager.get_key_stats(key_id)
    if not stats:
        raise HTTPException(status_code=404, detail="API key not found")
    return stats


@router.get("/verify", status_code=status.HTTP_200_OK)
async def verify_key(api_key: APIKey = Depends(get_api_key_dependency)):
    """Verify an API key (use X-API-Key header)."""
    return {
        "valid": True,
        "label": api_key.label,
        "scopes": api_key.scopes,
        "environment_id": api_key.environment_id,
    }


@router.get("/environments", status_code=status.HTTP_200_OK)
async def list_environments(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("key:list")),
):
    """List all available environments for API key assignment."""
    from sqlalchemy import select
    result = await db.execute(select(Environment).order_by(Environment.name))
    envs = result.scalars().all()
    return [
        {
            "id": env.id,
            "name": env.name,
            "slug": getattr(env, 'slug', ''),
            "description": getattr(env, 'description', None),
        }
        for env in envs
    ]


@router.post("/environments", status_code=status.HTTP_201_CREATED)
async def create_environment(
    payload: dict,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("key:create")),
):
    """Create a new environment."""
    from sqlalchemy import select
    import re

    name = (payload.get("name") or "").strip()
    if not name or len(name) > 100:
        raise HTTPException(
            status_code=422, detail="Name is required (max 100 chars)")

    slug = payload.get("slug") or re.sub(
        r'[^a-z0-9]+', '-', name.lower()).strip('-')
    description = payload.get("description", "")

    # Check uniqueness
    existing = await db.execute(select(Environment).where(
        (Environment.name == name) | (Environment.slug == slug)
    ))
    if existing.scalars().first():
        raise HTTPException(
            status_code=409, detail="Environment with this name or slug already exists")

    env = Environment(name=name, slug=slug, description=description)
    db.add(env)
    await db.flush()
    await db.commit()

    return {"id": env.id, "name": env.name, "slug": env.slug, "description": getattr(env, 'description', None)}


@router.delete("/environments/{env_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_environment(
    env_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("key:delete")),
):
    """Delete an environment."""
    from sqlalchemy import select
    result = await db.execute(select(Environment).where(Environment.id == env_id))
    env = result.scalars().first()
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    await db.delete(env)
    await db.commit()
