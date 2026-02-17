"""Authorizers management router (RBAC)."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from app.db.connector import get_db
from app.authorizers.rbac import RBACManager
from app.api.auth.auth_dependency import get_current_user
from app.db.models import User

router = APIRouter(prefix="/api/authorizers", tags=["Authorizers"])


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


def _normalize_permissions(perms):
    """Ensure permissions is a list of strings for JSON responses."""
    if not perms:
        return []
    out = []
    for p in perms:
        try:
            if isinstance(p, str):
                out.append(p)
            elif isinstance(p, dict):
                if 'name' in p:
                    out.append(str(p['name']))
                elif 'id' in p:
                    out.append(str(p['id']))
                else:
                    out.append(str(p))
            elif hasattr(p, 'name'):
                out.append(str(getattr(p, 'name')))
            elif hasattr(p, 'id'):
                out.append(str(getattr(p, 'id')))
            else:
                out.append(str(p))
        except Exception:
            out.append(str(p))
    return out


# Pydantic schemas
class RoleCreate(BaseModel):
    """Schema for creating a role."""
    name: str = Field(..., min_length=1, max_length=255,
                      description="Role name")
    description: Optional[str] = Field(None, description="Role description")
    permissions: Optional[List[str]] = Field(
        default_factory=list, description="List of permission names")
    id: Optional[int] = Field(None, description="Optional ID for the role")
    created_at: Optional[str] = Field(
        None, description="Optional creation timestamp")
    updated_at: Optional[str] = Field(
        None, description="Optional update timestamp")


class RoleUpdate(BaseModel):
    """Schema for updating a role."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    permissions: Optional[List[str]] = None


class RoleResponse(BaseModel):
    """Schema for role response."""
    id: int
    name: str
    description: Optional[str]
    permissions: List[str]
    created_at: str
    updated_at: Optional[str]

    model_config = {"from_attributes": True}


class PermissionCreate(BaseModel):
    """Schema for creating a permission."""
    name: str = Field(..., min_length=1, max_length=255,
                      description="Permission name")
    resource: str = Field(...,
                          description="Resource type (e.g., 'api', 'user', 'key')")
    action: str = Field(...,
                        description="Action (e.g., 'create', 'read', 'update', 'delete')")
    description: Optional[str] = Field(
        None, description="Permission description")


class PermissionUpdate(BaseModel):
    """Schema for updating a permission."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    resource: Optional[str] = None
    action: Optional[str] = None
    description: Optional[str] = None


class PermissionResponse(BaseModel):
    """Schema for permission response."""
    id: int
    name: str
    resource: str
    action: str
    description: Optional[str]
    created_at: str

    model_config = {"from_attributes": True}


class UserRoleAssignment(BaseModel):
    """Schema for assigning role to user."""
    user_id: int = Field(..., description="User ID")
    role_id: int = Field(..., description="Role ID")


# Roles endpoints
@router.post("/roles", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new role.

    Requires authentication. Creates a role with specified permissions.
    """
    manager = RBACManager(db)
    print(role_data, db, current_user, manager,
          flush=True)  # Debugging statement

    try:
        role = await manager.create_role(
            name=role_data.name,
            description=role_data.description,
            permissions=role_data.permissions,
            id=role_data.id,
            created_at=role_data.created_at,
            updated_at=role_data.updated_at,
        )

        print(f"Created route role: {role}", flush=True)  # Debugging statement

        return RoleResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            permissions=_normalize_permissions(role.permissions),
            created_at=to_isoformat(role.created_at) or "",
            updated_at=to_isoformat(role.updated_at),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create role: {str(e)}"
        )


@router.get("/roles", response_model=List[RoleResponse])
async def list_roles(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all roles."""
    manager = RBACManager(db)

    try:
        roles = await manager.list_roles()

        return [
            RoleResponse(
                id=r.id,
                name=r.name,
                description=r.description,
                permissions=_normalize_permissions(r.permissions),
                created_at=to_isoformat(r.created_at) or "",
                updated_at=to_isoformat(r.updated_at),
            )
            for r in roles
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list roles: {str(e)}"
        )


@router.get("/roles/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific role by ID."""
    manager = RBACManager(db)

    role = await manager.get_role(role_id)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id} not found"
        )

    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        permissions=_normalize_permissions(role.permissions),
        created_at=to_isoformat(role.created_at) or "",
        updated_at=to_isoformat(role.updated_at),
    )


@router.put("/roles/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: int,
    role_data: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a role."""
    manager = RBACManager(db)

    # Build update dict
    update_data = {}
    if role_data.name is not None:
        update_data["name"] = role_data.name
    if role_data.description is not None:
        update_data["description"] = role_data.description
    if role_data.permissions is not None:
        update_data["permissions"] = role_data.permissions

    role = await manager.update_role(role_id, **update_data)

    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id} not found"
        )

    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        permissions=_normalize_permissions(role.permissions),
        created_at=to_isoformat(role.created_at) or "",
        updated_at=to_isoformat(role.updated_at),
    )


@router.delete("/roles/{role_id}", status_code=status.HTTP_200_OK)
async def delete_role(
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a role."""
    manager = RBACManager(db)

    success = await manager.delete_role(role_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id} not found"
        )

    return {"message": f"Role {role_id} deleted successfully"}


# Permissions endpoints
@router.post("/permissions", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
async def create_permission(
    permission_data: PermissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new permission."""
    manager = RBACManager(db)

    try:
        permission = await manager.create_permission(
            name=permission_data.name,
            resource=permission_data.resource,
            action=permission_data.action,
            description=permission_data.description,
        )

        return PermissionResponse(
            id=permission.id,
            name=permission.name,
            resource=permission.resource,
            action=permission.action,
            description=permission.description,
            created_at=to_isoformat(permission.created_at) or "",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create permission: {str(e)}"
        )


@router.get("/permissions", response_model=List[PermissionResponse])
async def list_permissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all permissions."""
    manager = RBACManager(db)

    try:
        permissions = await manager.list_permissions()

        return [
            PermissionResponse(
                id=p.id,
                name=p.name,
                resource=p.resource,
                action=p.action,
                description=p.description,
                created_at=to_isoformat(p.created_at) or "",
            )
            for p in permissions
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list permissions: {str(e)}"
        )


@router.get("/permissions/{permission_id}", response_model=PermissionResponse)
async def get_permission(
    permission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific permission by ID."""
    manager = RBACManager(db)

    permission = await manager.get_permission(permission_id)

    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permission {permission_id} not found"
        )

    return PermissionResponse(
        id=permission.id,
        name=permission.name,
        resource=permission.resource,
        action=permission.action,
        description=permission.description,
        created_at=to_isoformat(permission.created_at) or "",
    )


@router.delete("/permissions/{permission_id}", status_code=status.HTTP_200_OK)
async def delete_permission(
    permission_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a permission."""
    manager = RBACManager(db)

    success = await manager.delete_permission(permission_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permission {permission_id} not found"
        )

    return {"message": f"Permission {permission_id} deleted successfully"}


# User-Role assignment endpoints
@router.post("/users/assign-role", status_code=status.HTTP_200_OK)
async def assign_role_to_user(
    assignment: UserRoleAssignment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assign a role to a user."""
    manager = RBACManager(db)

    try:
        await manager.assign_role_to_user(assignment.user_id, assignment.role_id)
        return {"message": f"Role {assignment.role_id} assigned to user {assignment.user_id}"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to assign role: {str(e)}"
        )


@router.delete("/users/{user_id}/roles/{role_id}", status_code=status.HTTP_200_OK)
async def remove_role_from_user(
    user_id: int,
    role_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a role from a user."""
    manager = RBACManager(db)

    try:
        await manager.remove_role_from_user(user_id, role_id)
        return {"message": f"Role {role_id} removed from user {user_id}"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to remove role: {str(e)}"
        )


@router.get("/users/{user_id}/roles", response_model=List[RoleResponse])
async def get_user_roles(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all roles assigned to a user."""
    manager = RBACManager(db)

    try:
        roles = await manager.get_user_roles(user_id)

        return [
            RoleResponse(
                id=r.id,
                name=r.name,
                description=r.description,
                permissions=_normalize_permissions(r.permissions),
                created_at=to_isoformat(r.created_at) or "",
                updated_at=to_isoformat(r.updated_at),
            )
            for r in roles
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user roles: {str(e)}"
        )
