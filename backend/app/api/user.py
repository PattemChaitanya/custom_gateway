"""User management API endpoints."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, Field
from app.db.connector import get_db
from app.db.models import User
from app.authorizers.rbac import RBACManager, require_permission
from app.api.auth.auth_dependency import get_current_user
from app.logging_config import get_logger

router = APIRouter()
logger = get_logger("user_api")


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
    password: str = Field(..., min_length=8, max_length=72,
                          description="Plain text password (bcrypt max 72 bytes)")
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False


@router.get("/", response_model=List[UserResponse])
async def list_users(
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("user:list")),
):
    """
    List all users in the system.

    Requires authentication.
    """
    try:
        actor = current_user.id if getattr(
            current_user, "id", None) else "unknown"
        result = await session.execute(select(User))
        users = result.scalars().all()
        logger.info("users.list", actor_user_id=actor, count=len(users))

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
        logger.error("users.list.failed", error=str(e), exc_info=True)
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
        actor = current_user.id if getattr(
            current_user, "id", None) else "unknown"
        # Fetch full user object from DB for complete fields (created_at, etc.)
        result = await session.execute(select(User).where(User.id == current_user.id))
        user = result.scalars().first() or result.scalar_one_or_none()

        if not user:
            logger.warning("users.me.not_found", actor_user_id=actor)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Get roles and permissions
        manager = RBACManager(session)
        roles = await manager.get_user_roles(user.id)
        permissions = await manager.get_user_permissions(user.id)
        logger.info(
            "users.me.read",
            actor_user_id=actor,
            target_user_id=user.id,
            role_count=len(roles),
            permission_count=len(permissions),
        )

        return UserWithRolesResponse(
            id=user.id,
            email=user.email,
            is_active=getattr(user, 'is_active', True),
            is_superuser=getattr(user, 'is_superuser', False),
            legacy_roles=getattr(user, 'roles', ''),
            roles=[r.name for r in roles],
            permissions=list(permissions),
            created_at=to_isoformat(getattr(user, 'created_at', None)),
        )

    except Exception as e:
        logger.error("users.me.failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get current user: {str(e)}"
        )


@router.get("/{user_id}", response_model=UserWithRolesResponse)
async def get_user(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("user:read")),
):
    """
    Get detailed information about a specific user.

    Includes roles and permissions.
    """
    try:
        actor = current_user.id if getattr(
            current_user, "id", None) else "unknown"
        # Get user
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user:
            logger.warning("users.get.not_found",
                           actor_user_id=actor, target_user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        # Get roles and permissions
        manager = RBACManager(session)
        roles = await manager.get_user_roles(user_id)
        permissions = await manager.get_user_permissions(user_id)
        logger.info(
            "users.get",
            actor_user_id=actor,
            target_user_id=user_id,
            role_count=len(roles),
            permission_count=len(permissions),
        )

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
        logger.error("users.get.failed", target_user_id=user_id,
                     error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user: {str(e)}"
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("user:update")),
):
    """
    Update user information.

    Requires authentication.
    """
    try:
        actor = current_user.id if getattr(
            current_user, "id", None) else "unknown"
        # Get user
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user:
            logger.warning("users.update.not_found",
                           actor_user_id=actor, target_user_id=user_id)
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

        # Mark the object as modified so both SQLAlchemy (PostgreSQL) and
        # the custom SQLiteDB session persist the changes on commit.
        session.add(user)
        await session.commit()
        await session.refresh(user)
        logger.info("users.update", actor_user_id=actor,
                    target_user_id=user_id)

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
        logger.error("users.update.failed", target_user_id=user_id,
                     error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(e)}"
        )


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: int,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("user:delete")),
):
    """
    Delete a user.

    Requires authentication. Cannot delete yourself.
    """
    actor = current_user.id if getattr(current_user, "id", None) else "unknown"
    if user_id == current_user.id:
        logger.warning("users.delete.self_blocked", actor_user_id=actor)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    try:
        # Get user
        result = await session.execute(select(User).where(User.id == user_id))
        user = result.scalars().first()

        if not user:
            logger.warning("users.delete.not_found",
                           actor_user_id=actor, target_user_id=user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User {user_id} not found"
            )

        await session.delete(user)
        await session.commit()
        logger.info("users.delete", actor_user_id=actor,
                    target_user_id=user_id)

        return {"message": f"User {user_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("users.delete.failed", target_user_id=user_id,
                     error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: CreateUserRequest,
    session: AsyncSession = Depends(get_db),
    current_user=Depends(require_permission("user:create")),
):
    """
    Create a new user.

    Requires authentication and proper permissions.
    """
    from app.api.auth.auth_service import pwd_context

    try:
        actor = current_user.id if getattr(
            current_user, "id", None) else "unknown"
        # Check for existing email first (works for both PostgreSQL and SQLite)
        existing = await session.execute(select(User).where(User.email == user_data.email))
        if existing.scalars().first() is not None:
            logger.warning("users.create.conflict",
                           actor_user_id=actor, email=user_data.email)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A user with email '{user_data.email}' already exists",
            )

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
        logger.info("users.create", actor_user_id=actor,
                    target_user_id=user.id)

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
        await session.rollback()
        logger.error("users.create.failed", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )
