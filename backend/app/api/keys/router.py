"""API Keys router and endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from pydantic import BaseModel, Field
from app.db.connector import get_db
from app.security.api_keys import APIKeyManager, get_api_key_dependency
from app.api.auth.auth_dependency import get_current_user
from app.db.models import User, APIKey

router = APIRouter(prefix="/keys", tags=["api-keys"])


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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
):
    """List all API keys (without showing actual key values)."""
    manager = APIKeyManager(db)
    keys = await manager.list_keys(environment_id=environment_id)
    return keys


@router.post("/{key_id}/revoke", status_code=status.HTTP_200_OK)
async def revoke_key(
    key_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
):
    """Delete an API key permanently."""
    manager = APIKeyManager(db)
    success = await manager.delete_key(key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")


@router.get("/verify", status_code=status.HTTP_200_OK)
async def verify_key(api_key: APIKey = Depends(get_api_key_dependency)):
    """Verify an API key (use X-API-Key header)."""
    return {
        "valid": True,
        "label": api_key.label,
        "scopes": api_key.scopes,
        "environment_id": api_key.environment_id,
    }
