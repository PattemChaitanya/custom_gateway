"""Secrets management router."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from app.db.connector import get_db
from app.security.secrets import SecretsManager
from app.authorizers.rbac import require_permission

router = APIRouter(prefix="/api/secrets", tags=["Secrets"])


# Helper function to safely convert datetime or string to ISO format
def to_isoformat(dt) -> Optional[str]:
    """Convert datetime or string to ISO format string."""
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


def parse_tags(tags) -> Optional[List[str]]:
    """Convert tags from various formats to a list of strings."""
    if tags is None:
        return []
    if isinstance(tags, list):
        return tags
    if isinstance(tags, str) and tags:
        return [t.strip() for t in tags.split(",")]
    return []


# Pydantic schemas
class SecretCreate(BaseModel):
    """Schema for creating a secret."""
    name: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Secret name")
    key: Optional[str] = Field(
        None, min_length=1, max_length=255, description="Alias for name")
    value: str = Field(..., min_length=1,
                       description="Secret value (will be encrypted)")
    description: Optional[str] = Field(None, description="Secret description")
    tags: Optional[List[str]] = Field(
        None, description="Tags for categorization")


class SecretUpdate(BaseModel):
    """Schema for updating a secret."""
    value: str = Field(..., min_length=1, description="New secret value")
    description: Optional[str] = None


class SecretRotate(BaseModel):
    """Schema for rotating a secret."""
    value: str = Field(..., min_length=1, description="New secret value")


class SecretResponse(BaseModel):
    """Schema for secret response (no decrypted value)."""
    id: int
    name: str
    key: str
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    encrypted_value: Optional[str] = None

    model_config = {"from_attributes": True}


class SecretDetailResponse(SecretResponse):
    """Schema for secret detail response (includes decrypted value)."""
    value: Optional[str] = None


@router.post("", response_model=SecretResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=SecretResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_secret(
    secret_data: SecretCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("secret:create")),
):
    """
    Create a new secret.

    The value will be encrypted at rest using Fernet encryption.
    Accepts either 'name' or 'key' as the secret identifier.
    """
    name = secret_data.name or secret_data.key
    if not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'name' or 'key' must be provided",
        )

    manager = SecretsManager(db)

    try:
        result = await manager.store_secret(
            name=name,
            value=secret_data.value,
            description=secret_data.description,
            tags=secret_data.tags,
        )

        await db.commit()

        return SecretResponse(
            id=result.id,
            name=result.name,
            key=result.key,
            description=result.description,
            tags=parse_tags(result.tags),
            created_at=to_isoformat(result.created_at),
            updated_at=to_isoformat(result.updated_at),
            encrypted_value=result.encrypted_value,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create secret: {str(e)}",
        )


@router.get("", response_model=List[SecretResponse])
@router.get("/", response_model=List[SecretResponse], include_in_schema=False)
async def list_secrets(
    tags: Optional[str] = Query(None, description="Filter by tag"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("secret:list")),
):
    """
    List all secrets.

    Returns secret metadata without decrypted values.
    Optionally filter by tags.
    """
    manager = SecretsManager(db)

    try:
        secrets = await manager.list_secrets(tags=tags)

        return [
            SecretResponse(
                id=s.id,
                name=s.name,
                key=s.key,
                description=s.description,
                tags=parse_tags(s.tags),
                created_at=to_isoformat(s.created_at),
                updated_at=to_isoformat(s.updated_at),
            )
            for s in secrets
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list secrets: {str(e)}",
        )


@router.get("/{name}", response_model=SecretDetailResponse)
async def get_secret(
    name: str,
    decrypt: bool = Query(False, description="Whether to decrypt the value"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("secret:read")),
):
    """
    Get a specific secret by name.

    Set decrypt=true to include the decrypted value in the response.
    """
    manager = SecretsManager(db)

    result = await manager.get_secret(name, decrypt=decrypt)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Secret '{name}' not found",
        )

    return SecretDetailResponse(
        id=result.id,
        name=result.name,
        key=result.key,
        description=result.description,
        tags=parse_tags(result.tags),
        created_at=to_isoformat(result.created_at),
        updated_at=to_isoformat(result.updated_at),
        encrypted_value=result.encrypted_value,
        value=result.value,
    )


@router.put("/{name}", response_model=SecretResponse)
async def update_secret(
    name: str,
    secret_data: SecretUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("secret:update")),
):
    """
    Update a secret's value and/or description.
    """
    manager = SecretsManager(db)

    # Verify the secret exists
    existing = await manager.get_secret(name, decrypt=False)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Secret '{name}' not found",
        )

    # Preserve existing description if not provided in update
    description = secret_data.description if secret_data.description is not None else existing.description
    # Preserve existing tags
    tags = existing.tags

    try:
        result = await manager.store_secret(
            name=name,
            value=secret_data.value,
            description=description,
            tags=tags,
        )

        await db.commit()

        return SecretResponse(
            id=result.id,
            name=result.name,
            key=result.key,
            description=result.description,
            tags=parse_tags(result.tags),
            created_at=to_isoformat(result.created_at),
            updated_at=to_isoformat(result.updated_at),
            encrypted_value=result.encrypted_value,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update secret: {str(e)}",
        )


@router.delete("/{name}", status_code=status.HTTP_200_OK)
async def delete_secret(
    name: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("secret:delete")),
):
    """Delete a secret permanently."""
    manager = SecretsManager(db)

    success = await manager.delete_secret(name)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Secret '{name}' not found",
        )

    await db.commit()

    return {"message": f"Secret '{name}' deleted successfully"}


@router.post("/{name}/rotate", response_model=SecretResponse)
async def rotate_secret(
    name: str,
    rotate_data: SecretRotate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("secret:update")),
):
    """
    Rotate a secret with a new value.

    Preserves existing description and tags while updating the encrypted value.
    """
    manager = SecretsManager(db)

    # Verify the secret exists and get current metadata
    existing = await manager.get_secret(name, decrypt=False)
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Secret '{name}' not found",
        )

    try:
        # Use store_secret directly to preserve description and tags
        result = await manager.store_secret(
            name=name,
            value=rotate_data.value,
            description=existing.description,
            tags=existing.tags,
        )

        await db.commit()

        return SecretResponse(
            id=result.id,
            name=result.name,
            key=result.key,
            description=result.description,
            tags=parse_tags(result.tags),
            created_at=to_isoformat(result.created_at),
            updated_at=to_isoformat(result.updated_at),
            encrypted_value=result.encrypted_value,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rotate secret: {str(e)}",
        )
