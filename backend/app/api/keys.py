"""API Keys management router."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from app.db import get_session
from app.security.api_keys import APIKeyManager
from app.logging.audit import AuditLogger
from app.api.auth.dependencies import get_current_user

router = APIRouter(prefix="/api/keys", tags=["API Keys"])


# Pydantic models
class CreateAPIKeyRequest(BaseModel):
    """Request model for creating an API key."""
    label: str = Field(..., min_length=1, max_length=100, description="Label for the API key")
    scopes: Optional[str] = Field(None, description="Comma-separated list of scopes")
    environment_id: Optional[int] = Field(None, description="Environment ID")
    expires_in_days: Optional[int] = Field(365, ge=0, description="Days until expiration (0 for never)")
    metadata: Optional[dict] = Field(None, description="Additional metadata")


class APIKeyResponse(BaseModel):
    """Response model for API key."""
    id: int
    label: str
    key_preview: str
    scopes: Optional[str]
    environment_id: Optional[int]
    revoked: bool
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    usage_count: int
    
    class Config:
        from_attributes = True


class APIKeyWithSecret(APIKeyResponse):
    """Response model with the actual key (only returned on creation)."""
    key: str


@router.post("", response_model=APIKeyWithSecret, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: CreateAPIKeyRequest,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """Generate a new API key."""
    try:
        api_key_manager = APIKeyManager(session)
        audit_logger = AuditLogger(session)
        
        # Calculate expiration
        expires_at = None
        if request.expires_in_days and request.expires_in_days > 0:
            expires_at = datetime.utcnow() + timedelta(days=request.expires_in_days)
        
        # Create API key
        api_key_obj = await api_key_manager.create_api_key(
            label=request.label,
            scopes=request.scopes,
            environment_id=request.environment_id,
            expires_at=expires_at,
            metadata=request.metadata,
        )
        
        # Log the action
        await audit_logger.log_event(
            action="KEY_GENERATE",
            user_id=current_user.get("id"),
            resource_type="api_key",
            resource_id=str(api_key_obj.id),
            metadata_json={"label": request.label, "scopes": request.scopes},
        )
        
        await session.commit()
        
        # Return with the actual key (only time it's shown)
        return {
            "id": api_key_obj.id,
            "key": api_key_obj.key,  # Plain text key (only shown once)
            "label": api_key_obj.label,
            "key_preview": api_key_obj.key_preview,
            "scopes": api_key_obj.scopes,
            "environment_id": api_key_obj.environment_id,
            "revoked": api_key_obj.revoked,
            "created_at": api_key_obj.created_at,
            "expires_at": api_key_obj.expires_at,
            "last_used_at": api_key_obj.last_used_at,
            "usage_count": api_key_obj.usage_count,
        }
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create API key: {str(e)}"
        )


@router.get("", response_model=List[APIKeyResponse])
async def list_api_keys(
    environment_id: Optional[int] = None,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """List all API keys."""
    try:
        api_key_manager = APIKeyManager(session)
        keys = await api_key_manager.list_api_keys(environment_id=environment_id)
        return keys
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list API keys: {str(e)}"
        )


@router.post("/{key_id}/revoke", status_code=status.HTTP_200_OK)
async def revoke_api_key(
    key_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """Revoke an API key."""
    try:
        api_key_manager = APIKeyManager(session)
        audit_logger = AuditLogger(session)
        
        success = await api_key_manager.revoke_api_key(key_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        # Log the action
        await audit_logger.log_event(
            action="KEY_REVOKE",
            user_id=current_user.get("id"),
            resource_type="api_key",
            resource_id=str(key_id),
        )
        
        await session.commit()
        return {"message": "API key revoked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to revoke API key: {str(e)}"
        )


@router.delete("/{key_id}", status_code=status.HTTP_200_OK)
async def delete_api_key(
    key_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """Delete an API key."""
    try:
        api_key_manager = APIKeyManager(session)
        audit_logger = AuditLogger(session)
        
        success = await api_key_manager.delete_api_key(key_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        # Log the action
        await audit_logger.log_event(
            action="KEY_DELETE",
            user_id=current_user.get("id"),
            resource_type="api_key",
            resource_id=str(key_id),
        )
        
        await session.commit()
        return {"message": "API key deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete API key: {str(e)}"
        )


@router.get("/{key_id}/stats")
async def get_api_key_stats(
    key_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: dict = Depends(get_current_user),
):
    """Get usage statistics for an API key."""
    try:
        api_key_manager = APIKeyManager(session)
        stats = await api_key_manager.get_key_stats(key_id)
        
        if not stats:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        return stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get API key stats: {str(e)}"
        )
