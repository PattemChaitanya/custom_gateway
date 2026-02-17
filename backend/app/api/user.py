"""User management API endpoints."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, Field
from app.db.connector import get_db
from app.db.models import User
from app.authorizers.rbac import RBACManager
from app.api.auth.auth_dependency import get_current_user

router = APIRouter()


# Helper function to safely convert datetime or string to ISO format
def to_isoformat(dt) -> str:
    """Convert datetime or string to ISO format string."""
    if dt is None:
        return None
    if isinstance(dt, str):
        return dt
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


# Pydantic schemas
class UserResponse(BaseModel):
    """User response schema."""
    id: int
    email: str
    is_active: bool = True
    is_superuser: bool = False
    roles: Optional[str] = None
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class UserWithRolesResponse(BaseModel):
    """User response with detailed role information."""
    id: int
    email: str
    is_active: bool
    is_superuser: bool
    legacy_roles: Optional[str] = None  # Legacy roles column
    roles: List[str] = []  # List of role names from user_roles table
    permissions: List[str] = []  # List of all permissions
    created_at: Optional[str] = None

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """Schema for updating user."""
    email: Optional[EmailStr] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class CreateUserRequest(BaseModel):
    """Schema for creating a new user."""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., min_length=8, description="Plain text password")
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False


@router.get("/", response_model=List[UserResponse])
async def list_users(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all users in the system.

    Requires authentication.
    """
    try:
        result = await session.execute(select(User))
        users = result.scalars().all()

        return [
            UserResponse(
                id=u.id,
                email=u.email,
                is_active=u.is_active if u.is_active is not None else True,
                is_superuser=u.is_superuser if u.is_superuser is not None else False,
                roles=u.roles,
                created_at=to_isoformat(u.created_at),
            )
            for u in users
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list users: {str(e)}"
        )


@router.get("/me", response_model=UserWithRolesResponse)
async def get_current_user_info(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get information about the currently authenticated user.

    Includes roles and permissions.
    """
    try:
        # Get roles and permissions
        manager = RBACManager(session)
        roles = await manager.get_user_roles(current_user.id)
        permissions = await manager.get_user_permissions(current_user.id)

        return UserWithRolesResponse(
            id=current_user.id,
            email=current_user.email,
            is_active=current_user.is_active,
            is_superuser=current_user.is_superuser,
            legacy_roles=current_user.roles,
            roles=[r.name for r in roles],
            permissions=list(permissions),
            created_at=to_isoformat(current_user.created_at),
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get current user: {str(e)}"
        )


@router.get("/{user_id}", response_model=UserWithRolesResponse)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get detailed information about a specific user.

    Includes roles and permissions.
    """
    try:
        # Get user
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        # Get roles and permissions
        manager = RBACManager(session)
        roles = await manager.get_user_roles(user_id)
        permissions = await manager.get_user_permissions(user_id)

        return UserWithRolesResponse(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            legacy_roles=user.roles,
            roles=[r.name for r in roles],
            permissions=list(permissions),
            created_at=to_isoformat(user.created_at),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}"
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update user information.

    Requires authentication.
    """
    try:
        # Get user
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        # Update fields
        if user_data.email is not None:
            user.email = user_data.email
        if user_data.is_active is not None:
            user.is_active = user_data.is_active
        if user_data.is_superuser is not None:
            user.is_superuser = user_data.is_superuser

        await session.commit()
        await session.refresh(user)

        return UserResponse(
            id=user.id,
            email=user.email,
            is_active=user.is_active if user.is_active is not None else True,
            is_superuser=user.is_superuser if user.is_superuser is not None else False,
            roles=user.roles,
            created_at=to_isoformat(user.created_at),
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a user.

    Requires authentication. Cannot delete yourself.
    """
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    try:
        # Get user
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        await session.delete(user)
        await session.commit()

        return {"message": f"User {user_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: CreateUserRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new user.

    Requires authentication and proper permissions.
    """
    from passlib.context import CryptContext

    try:
        # simple password hashing using bcrypt
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed = pwd_context.hash(user_data.password)

        user = User(
            email=user_data.email,
            hashed_password=hashed,
            is_active=user_data.is_active if user_data.is_active is not None else True,
            is_superuser=user_data.is_superuser if user_data.is_superuser is not None else False,
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

        return UserResponse(
            id=user.id,
            email=user.email,
            is_active=user.is_active if user.is_active is not None else True,
            is_superuser=user.is_superuser if user.is_superuser is not None else False,
            roles=user.roles,
            created_at=to_isoformat(user.created_at),
        )

    except Exception as e:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )
