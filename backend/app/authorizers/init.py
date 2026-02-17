"""RBAC initialization helpers for app startup."""

from sqlalchemy.ext.asyncio import AsyncSession
from app.authorizers.rbac import RBACManager
from app.logging_config import get_logger

logger = get_logger("rbac_init")


async def init_rbac_system(session: AsyncSession, force: bool = False) -> dict:
    """Initialize RBAC system with default roles and permissions.

    This function is idempotent and can be called multiple times safely.
    It will only create roles and permissions that don't already exist.

    Args:
        session: AsyncSession for database operations
        force: If True, will recreate all roles and permissions (use with caution)

    Returns:
        dict: Summary of initialization results
    """
    manager = RBACManager(session)
    results = {
        "permissions_created": [],
        "permissions_skipped": [],
        "roles_created": [],
        "roles_skipped": [],
        "errors": []
    }

    try:
        # Default permissions
        default_permissions = [
            # API Management
            {"name": "api:create", "resource": "api", "action": "create"},
            {"name": "api:read", "resource": "api", "action": "read"},
            {"name": "api:update", "resource": "api", "action": "update"},
            {"name": "api:delete", "resource": "api", "action": "delete"},
            {"name": "api:list", "resource": "api", "action": "list"},

            # User Management
            {"name": "user:create", "resource": "user", "action": "create"},
            {"name": "user:read", "resource": "user", "action": "read"},
            {"name": "user:update", "resource": "user", "action": "update"},
            {"name": "user:delete", "resource": "user", "action": "delete"},
            {"name": "user:list", "resource": "user", "action": "list"},

            # Key Management
            {"name": "key:create", "resource": "key", "action": "create"},
            {"name": "key:read", "resource": "key", "action": "read"},
            {"name": "key:update", "resource": "key", "action": "update"},
            {"name": "key:delete", "resource": "key", "action": "delete"},
            {"name": "key:list", "resource": "key", "action": "list"},

            # Role Management
            {"name": "role:create", "resource": "role", "action": "create"},
            {"name": "role:read", "resource": "role", "action": "read"},
            {"name": "role:update", "resource": "role", "action": "update"},
            {"name": "role:delete", "resource": "role", "action": "delete"},
            {"name": "role:list", "resource": "role", "action": "list"},
            {"name": "role:assign", "resource": "role", "action": "assign"},
        ]

        # Create permissions
        for perm_data in default_permissions:
            try:
                existing_perms = await manager.list_permissions()
                if not force and any(p.name == perm_data["name"] for p in existing_perms):
                    results["permissions_skipped"].append(perm_data["name"])
                    continue

                await manager.create_permission(**perm_data)
                results["permissions_created"].append(perm_data["name"])

            except Exception as e:
                logger.error(
                    f"Failed to create permission {perm_data['name']}: {e}")
                results["errors"].append(
                    f"Permission {perm_data['name']}: {str(e)}")

        # Default roles
        default_roles = [
            {
                "name": "admin",
                "description": "Full system access",
                "permissions": [
                    "api:create", "api:read", "api:update", "api:delete", "api:list",
                    "user:create", "user:read", "user:update", "user:delete", "user:list",
                    "key:create", "key:read", "key:update", "key:delete", "key:list",
                    "role:create", "role:read", "role:update", "role:delete", "role:list", "role:assign",
                ]
            },
            {
                "name": "developer",
                "description": "API development access",
                "permissions": [
                    "api:create", "api:read", "api:update", "api:list",
                    "key:create", "key:read", "key:list",
                ]
            },
            {
                "name": "editor",
                "description": "Edit existing resources",
                "permissions": [
                    "api:read", "api:update", "api:list",
                    "key:read", "key:list",
                ]
            },
            {
                "name": "viewer",
                "description": "Read-only access",
                "permissions": [
                    "api:read", "api:list",
                    "key:read", "key:list",
                ]
            },
        ]

        # Create roles
        for role_data in default_roles:
            try:
                existing_role = await manager.get_role_by_name(role_data["name"])
                if not force and existing_role:
                    results["roles_skipped"].append(role_data["name"])
                    continue

                await manager.create_role(**role_data)
                results["roles_created"].append(role_data["name"])

            except Exception as e:
                logger.error(f"Failed to create role {role_data['name']}: {e}")
                results["errors"].append(f"Role {role_data['name']}: {str(e)}")

        logger.info(
            f"RBAC initialized: {len(results['permissions_created'])} permissions, "
            f"{len(results['roles_created'])} roles created"
        )

    except Exception as e:
        logger.error(f"RBAC initialization failed: {e}", exc_info=True)
        results["errors"].append(f"Fatal error: {str(e)}")

    return results


async def ensure_rbac_initialized(session: AsyncSession) -> bool:
    """Ensure RBAC system is initialized with minimum required roles.

    Returns:
        bool: True if RBAC is ready, False otherwise
    """
    try:
        manager = RBACManager(session)

        # Check if at least admin role exists
        admin_role = await manager.get_role_by_name("admin")

        if not admin_role:
            logger.info("RBAC not initialized, initializing now...")
            results = await init_rbac_system(session)

            if results["errors"]:
                logger.warning(
                    f"RBAC initialization had errors: {results['errors']}")
                return False

            return True

        return True

    except Exception as e:
        logger.error(f"Failed to check RBAC initialization: {e}")
        return False
