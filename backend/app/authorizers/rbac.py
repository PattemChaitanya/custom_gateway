"""Role-Based Access Control (RBAC) implementation."""

from typing import List, Optional, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends, HTTPException, status
from app.db.models import Role, Permission, UserRole, User
from app.db.connector import get_db
from app.api.auth.auth_dependency import get_current_user
from app.logging_config import get_logger
import functools

logger = get_logger("rbac")


class RBACManager:
    """Manager for Role-Based Access Control."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_role(
        self,
        name: str,
        description: Optional[str] = None,
        permissions: Optional[List[str]] = None,
    ) -> Role:
        """Create a new role."""
        role = Role(
            name=name,
            description=description,
            permissions=permissions or [],
        )
        
        self.session.add(role)
        await self.session.commit()
        await self.session.refresh(role)
        
        logger.info(f"Created role: {name}")
        return role
    
    async def get_role(self, role_id: int) -> Optional[Role]:
        """Get a role by ID."""
        result = await self.session.execute(
            select(Role).where(Role.id == role_id)
        )
        return result.scalar_one_or_none()
    
    async def get_role_by_name(self, name: str) -> Optional[Role]:
        """Get a role by name."""
        result = await self.session.execute(
            select(Role).where(Role.name == name)
        )
        return result.scalar_one_or_none()
    
    async def list_roles(self) -> List[Role]:
        """List all roles."""
        result = await self.session.execute(select(Role))
        return result.scalars().all()
    
    async def update_role(
        self,
        role_id: int,
        **kwargs
    ) -> Optional[Role]:
        """Update a role."""
        role = await self.get_role(role_id)
        
        if not role:
            return None
        
        for key, value in kwargs.items():
            if hasattr(role, key) and value is not None:
                setattr(role, key, value)
        
        await self.session.commit()
        await self.session.refresh(role)
        
        logger.info(f"Updated role: {role_id}")
        return role
    
    async def delete_role(self, role_id: int) -> bool:
        """Delete a role."""
        role = await self.get_role(role_id)
        
        if not role:
            return False
        
        await self.session.delete(role)
        await self.session.commit()
        
        logger.info(f"Deleted role: {role_id}")
        return True
    
    async def create_permission(
        self,
        name: str,
        resource: str,
        action: str,
        description: Optional[str] = None,
    ) -> Permission:
        """Create a new permission."""
        permission = Permission(
            name=name,
            resource=resource,
            action=action,
            description=description,
        )
        
        self.session.add(permission)
        await self.session.commit()
        await self.session.refresh(permission)
        
        logger.info(f"Created permission: {name}")
        return permission
    
    async def list_permissions(self) -> List[Permission]:
        """List all permissions."""
        result = await self.session.execute(select(Permission))
        return result.scalars().all()
    
    async def get_permission(self, permission_id: int) -> Optional[Permission]:
        """Get a permission by ID."""
        result = await self.session.execute(
            select(Permission).where(Permission.id == permission_id)
        )
        return result.scalar_one_or_none()
    
    async def delete_permission(self, permission_id: int) -> bool:
        """Delete a permission."""
        permission = await self.get_permission(permission_id)
        
        if not permission:
            return False
        
        await self.session.delete(permission)
        await self.session.commit()
        
        logger.info(f"Deleted permission: {permission_id}")
        return True
    
    async def assign_role_to_user(self, user_id: int, role_id: int) -> UserRole:
        """Assign a role to a user."""
        # Check if assignment already exists
        result = await self.session.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            return existing
        
        user_role = UserRole(user_id=user_id, role_id=role_id)
        self.session.add(user_role)
        await self.session.commit()
        await self.session.refresh(user_role)
        
        logger.info(f"Assigned role {role_id} to user {user_id}")
        return user_role
    
    async def remove_role_from_user(self, user_id: int, role_id: int) -> bool:
        """Remove a role from a user."""
        result = await self.session.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id
            )
        )
        user_role = result.scalar_one_or_none()
        
        if not user_role:
            return False
        
        await self.session.delete(user_role)
        await self.session.commit()
        
        logger.info(f"Removed role {role_id} from user {user_id}")
        return True
    
    async def get_user_roles(self, user_id: int) -> List[Role]:
        """Get all roles assigned to a user."""
        result = await self.session.execute(
            select(Role).join(UserRole).where(UserRole.user_id == user_id)
        )
        return result.scalars().all()
    
    async def get_user_permissions(self, user_id: int) -> Set[str]:
        """Get all permissions for a user (from all their roles)."""
        roles = await self.get_user_roles(user_id)
        permissions = set()
        
        for role in roles:
            if role.permissions:
                permissions.update(role.permissions)
        
        # Also check legacy roles column on User model
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user and user.roles:
            # Add legacy roles as permissions
            legacy_roles = user.roles.split(',')
            permissions.update(legacy_roles)
        
        return permissions
    
    async def user_has_permission(self, user_id: int, permission: str) -> bool:
        """Check if a user has a specific permission."""
        permissions = await self.get_user_permissions(user_id)
        return permission in permissions
    
    async def user_has_role(self, user_id: int, role_name: str) -> bool:
        """Check if a user has a specific role."""
        roles = await self.get_user_roles(user_id)
        return any(role.name == role_name for role in roles)


# Dependency functions for FastAPI routes
async def has_permission(
    permission: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> bool:
    """Check if current user has a permission."""
    manager = RBACManager(db)
    return await manager.user_has_permission(user.id, permission)


def require_permission(permission: str):
    """Decorator to require a specific permission."""
    async def permission_checker(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        manager = RBACManager(db)
        if not await manager.user_has_permission(user.id, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission} required"
            )
        return user
    return permission_checker


def require_role(role_name: str):
    """Decorator to require a specific role."""
    async def role_checker(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        manager = RBACManager(db)
        if not await manager.user_has_role(user.id, role_name):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role_name}"
            )
        return user
    return role_checker
