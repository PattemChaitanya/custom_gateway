"""Administrative endpoints for system initialization and management."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.connector import get_db
from app.authorizers.init import init_rbac_system, ensure_rbac_initialized
from app.api.auth.auth_dependency import get_current_user
from app.db.models import User
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin", tags=["Administration"])


class InitRBACResponse(BaseModel):
    """Response schema for RBAC initialization."""
    success: bool
    message: str
    permissions_created: int
    permissions_skipped: int
    roles_created: int
    roles_skipped: int
    errors: list


@router.post("/init-rbac", response_model=InitRBACResponse)
async def initialize_rbac(
    force: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Initialize RBAC system with default roles and permissions.

    This endpoint creates all default roles and permissions needed for the system.
    It's idempotent and safe to call multiple times.

    Args:
        force: If True, will recreate all roles and permissions (use with caution)

    Returns:
        Summary of initialization results
    """
    # Only superusers can initialize RBAC
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can initialize RBAC"
        )

    try:
        results = await init_rbac_system(db, force=force)

        success = len(results["errors"]) == 0
        total_created = len(
            results["permissions_created"]) + len(results["roles_created"])

        if success:
            message = f"RBAC initialized successfully: {total_created} items created"
        else:
            message = f"RBAC initialized with {len(results['errors'])} errors"

        return InitRBACResponse(
            success=success,
            message=message,
            permissions_created=len(results["permissions_created"]),
            permissions_skipped=len(results["permissions_skipped"]),
            roles_created=len(results["roles_created"]),
            roles_skipped=len(results["roles_skipped"]),
            errors=results["errors"]
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize RBAC: {str(e)}"
        )


@router.get("/rbac-status")
async def rbac_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Check if RBAC system is properly initialized.

    Returns:
        Status information about RBAC initialization
    """
    try:
        is_initialized = await ensure_rbac_initialized(db)

        from app.authorizers.rbac import RBACManager
        manager = RBACManager(db)

        roles = await manager.list_roles()
        permissions = await manager.list_permissions()

        return {
            "initialized": is_initialized,
            "total_roles": len(roles),
            "total_permissions": len(permissions),
            "roles": [r.name for r in roles],
            "message": "RBAC is initialized" if is_initialized else "RBAC needs initialization"
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check RBAC status: {str(e)}"
        )
