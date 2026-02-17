"""Role-Based Access Control (RBAC) implementation."""

from typing import List, Optional, Set
from sqlalchemy import select, or_
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
        self._resolved_session = None

    async def _sess(self):
        from app.db.session_utils import resolve_session
        if self._resolved_session is None:
            self._resolved_session = await resolve_session(self.session)
        return self._resolved_session

    async def create_role(
        self,
        name: str,
        description: Optional[str] = None,
        permissions: Optional[List[str]] = None,
        id: Optional[int] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
    ) -> Role:
        """Create a new role."""
        from datetime import datetime

        role_data = {
            "name": name,
            "description": description,
            "permissions": [],
        }

        # Add optional fields if provided
        if id is not None:
            role_data["id"] = id
        if created_at is not None:
            role_data["created_at"] = datetime.fromisoformat(
                created_at.replace('Z', '+00:00'))
        if updated_at is not None:
            role_data["updated_at"] = datetime.fromisoformat(
                updated_at.replace('Z', '+00:00'))

        role = Role(**role_data)
        print(f"Creating role: {name} with permissions: {permissions}, {role}")

        # Normalize incoming permissions to list of names/ids
        perm_list = []
        for p in (permissions or []):
            if isinstance(p, str):
                perm_list.append(p)
            elif isinstance(p, dict):
                if 'name' in p:
                    perm_list.append(str(p['name']))
                elif 'id' in p:
                    perm_list.append(str(p['id']))
            elif hasattr(p, 'name'):
                perm_list.append(str(getattr(p, 'name')))
            elif hasattr(p, 'id'):
                perm_list.append(str(getattr(p, 'id')))
            else:
                perm_list.append(str(p))

        role.permissions = perm_list

        session = await self._sess()
        session.add(role)
        await session.flush()  # Flush to assign ID
        await session.commit()
        await session.refresh(role)
        print(f"Created role: {role} with ID: {role.id}")

        logger.info(f"Created role: {name}")
        return role

    async def get_role(self, role_id: int) -> Optional[Role]:
        """Get a role by ID."""
        session = await self._sess()
        result = await session.execute(
            select(Role).where(Role.id == role_id)
        )
        return result.scalars().first()

    async def list_roles(self) -> List[Role]:
        """List all roles."""
        session = await self._sess()
        result = await session.execute(select(Role))
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

        session = await self._sess()
        await session.commit()
        await session.refresh(role)

        logger.info(f"Updated role: {role_id}")
        return role

    async def delete_role(self, role_id: int) -> bool:
        """Delete a role."""
        role = await self.get_role(role_id)

        if not role:
            return False

        session = await self._sess()
        await session.delete(role)
        await session.commit()

        logger.info(f"Deleted role: {role_id}")
        return True

    async def create_permission(
        self,
        name: str,
        resource: Optional[str] = None,
        action: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Permission:
        """Create a new permission.

        Backwards-compatible: callers may pass only `name` and `description`
        where `name` follows the pattern "resource:action" (e.g. "api:read").
        """
        # If resource/action not provided try to infer from name
        if (not resource or not action) and isinstance(name, str) and ":" in name:
            parts = name.split(":", 1)
            if not resource:
                resource = parts[0]
            if not action:
                action = parts[1]

        # Fallback defaults if still missing
        resource = resource or "*"
        action = action or "*"

        permission = Permission(
            name=name,
            resource=resource,
            action=action,
            description=description,
        )

        session = await self._sess()
        session.add(permission)
        await session.commit()
        await session.refresh(permission)

        logger.info(f"Created permission: {name}")
        return permission

    async def list_permissions(self) -> List[Permission]:
        """List all permissions."""
        session = await self._sess()
        result = await session.execute(select(Permission))
        return result.scalars().all()

    async def get_permission(self, permission_id: int) -> Optional[Permission]:
        """Get a permission by ID."""
        session = await self._sess()
        result = await session.execute(
            select(Permission).where(Permission.id == permission_id)
        )
        return result.scalars().first()

    async def delete_permission(self, permission_id: int) -> bool:
        """Delete a permission."""
        permission = await self.get_permission(permission_id)

        if not permission:
            return False

        session = await self._sess()
        await session.delete(permission)
        await session.commit()

        logger.info(f"Deleted permission: {permission_id}")
        return True

    async def assign_permission_to_role(self, role_id: int, permission_identifier) -> bool:
        """Assign a permission (by id or name) to a role.

        The role stores a list of permission *names* in the JSON `permissions` column
        so we normalize to permission.name when adding.
        """
        role = await self.get_role(role_id)
        if not role:
            return False

        # Resolve permission by id, name, Permission instance, or by dict/object containing id/name
        perm = None
        # If caller passed a Permission instance already, use it directly
        if hasattr(permission_identifier, 'id') and hasattr(permission_identifier, 'name'):
            perm = permission_identifier
        try:
            # If caller passed a dict-like object extract id/name
            if isinstance(permission_identifier, dict):
                if 'id' in permission_identifier:
                    pid = int(permission_identifier['id'])
                    perm = await self.get_permission(pid)
                elif 'name' in permission_identifier:
                    pname = permission_identifier['name']
                    session = await self._sess()
                    res = await session.execute(select(Permission).where(Permission.name == pname))
                    perm = res.scalars().first()
            elif hasattr(permission_identifier, 'get'):
                # other mapping-like
                pid = permission_identifier.get('id')
                pname = permission_identifier.get('name')
                if pid is not None:
                    perm = await self.get_permission(int(pid))
                elif pname is not None:
                    session = await self._sess()
                    res = await session.execute(select(Permission).where(Permission.name == pname))
                    perm = res.scalars().first()
            else:
                # numeric id
                if isinstance(permission_identifier, int) or (isinstance(permission_identifier, str) and permission_identifier.isdigit()):
                    pid = int(permission_identifier)
                    perm = await self.get_permission(pid)
                else:
                    # lookup by name (string or object with 'name')
                    pname = permission_identifier
                    if not isinstance(pname, str) and hasattr(pname, 'name'):
                        pname = getattr(pname, 'name')
                    session = await self._sess()
                    res = await session.execute(select(Permission).where(Permission.name == pname))
                    perm = res.scalars().first()
        except Exception:
            perm = None

        if not perm:
            return False

        current = list(role.permissions or [])
        # ensure names are stored so permission checks (which expect strings) work
        if perm.name in current:
            return True

        # assign a new list so SQLAlchemy change tracking picks up the update
        role.permissions = current + [perm.name]

        session = await self._sess()
        await session.commit()
        await session.refresh(role)

        logger.info(
            f"Assigned permission {perm.id} ({perm.name}) to role {role_id}")
        return True

    async def get_role_permissions(self, role_id: int) -> List[Permission]:
        """Return list of Permission objects assigned to a role.

        The role may store permission names or ids; attempt to resolve both.
        """
        role = await self.get_role(role_id)
        if not role or not role.permissions:
            return []

        # Resolve all permission ids and names in a single query for reliability
        id_list = []
        name_list = []
        for entry in role.permissions:
            # Accept ints, numeric strings, dicts like {'id':..} or {'name':..}, or Permission-like objects
            if isinstance(entry, int) or (isinstance(entry, str) and str(entry).isdigit()):
                id_list.append(int(entry))
            elif isinstance(entry, dict):
                if 'id' in entry:
                    id_list.append(int(entry['id']))
                elif 'name' in entry:
                    name_list.append(str(entry['name']))
            elif hasattr(entry, 'id') and getattr(entry, 'id', None) is not None:
                id_list.append(int(getattr(entry, 'id')))
            elif hasattr(entry, 'name') and getattr(entry, 'name', None) is not None:
                name_list.append(str(getattr(entry, 'name')))
            else:
                name_list.append(str(entry))

        clauses = []
        if id_list:
            clauses.append(Permission.id.in_(id_list))
        if name_list:
            clauses.append(Permission.name.in_(name_list))

        if not clauses:
            return []

        query = select(Permission).where(
            or_(*clauses)) if len(clauses) > 1 else select(Permission).where(clauses[0])
        session = await self._sess()
        res = await session.execute(query)
        return res.scalars().all()

    async def remove_permission_from_role(self, role_id: int, permission_identifier) -> bool:
        """Remove a permission (by id or name) from a role."""
        role = await self.get_role(role_id)
        if not role or not role.permissions:
            return False

        # build set of permission names to remove
        to_remove_name = None
        if isinstance(permission_identifier, int) or (isinstance(permission_identifier, str) and permission_identifier.isdigit()):
            perm = await self.get_permission(int(permission_identifier))
            if not perm:
                return False
            to_remove_name = perm.name
        else:
            to_remove_name = permission_identifier

        current = [p for p in (role.permissions or []) if p != to_remove_name]
        if len(current) == len(role.permissions or []):
            return False

        role.permissions = current
        session = await self._sess()
        await session.commit()
        await session.refresh(role)

        logger.info(f"Removed permission {to_remove_name} from role {role_id}")
        return True

    async def assign_role_to_user(self, user_id: int, role_id: int) -> UserRole:
        """Assign a role to a user."""
        # Check if assignment already exists
        session = await self._sess()
        result = await session.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id
            )
        )
        existing = result.scalars().first()

        if existing:
            return existing

        user_role = UserRole(user_id=user_id, role_id=role_id)
        session = await self._sess()
        session.add(user_role)
        await session.commit()
        await session.refresh(user_role)

        logger.info(f"Assigned role {role_id} to user {user_id}")
        return user_role

    async def remove_role_from_user(self, user_id: int, role_id: int) -> bool:
        """Remove a role from a user."""
        session = await self._sess()
        result = await session.execute(
            select(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id
            )
        )
        user_role = result.scalars().first()

        if not user_role:
            return False

        session = await self._sess()
        await session.delete(user_role)
        await session.commit()

        logger.info(f"Removed role {role_id} from user {user_id}")
        return True

    async def get_user_roles(self, user_id: int) -> List[Role]:
        """Get all roles assigned to a user."""
        # SQLite fallback uses a custom session implementation that doesn't
        # fully support SQLAlchemy joins. Detect and handle that case by
        # querying `user_roles` first and then loading roles by id.
        session = await self._sess()
        try:
            # Detect SQLiteDB by presence of `_db` attribute
            if hasattr(session, '_db'):
                # Get user_roles rows
                ur = await session.execute(select(UserRole).where(UserRole.user_id == user_id))
                user_roles = ur.scalars().all()
                role_ids = [int(getattr(r, 'role_id')) for r in user_roles if getattr(
                    r, 'role_id', None) is not None]
                roles = []
                for rid in role_ids:
                    rres = await session.execute(select(Role).where(Role.id == rid))
                    r = rres.scalars().first()
                    if r:
                        roles.append(r)
                return roles
            else:
                result = await session.execute(
                    select(Role).join(UserRole).where(
                        UserRole.user_id == user_id)
                )
                return result.scalars().all()
        except Exception:
            # Fallback to attempted join path if custom handling fails
            result = await session.execute(
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
        session = await self._sess()
        result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalars().first()

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
