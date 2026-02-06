"""Seed default roles and permissions for RBAC system."""

from app.logging_config import get_logger
from app.authorizers.rbac import RBACManager
from app.db.connector import get_db_manager
from sqlalchemy.ext.asyncio import AsyncSession
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


logger = get_logger("seed_rbac")


# Default permissions structure
DEFAULT_PERMISSIONS = [
    # API Management
    {"name": "api:create", "resource": "api",
        "action": "create", "description": "Create new APIs"},
    {"name": "api:read", "resource": "api",
        "action": "read", "description": "View API details"},
    {"name": "api:update", "resource": "api", "action": "update",
        "description": "Update API configuration"},
    {"name": "api:delete", "resource": "api",
        "action": "delete", "description": "Delete APIs"},
    {"name": "api:list", "resource": "api",
        "action": "list", "description": "List all APIs"},

    # User Management
    {"name": "user:create", "resource": "user",
        "action": "create", "description": "Create new users"},
    {"name": "user:read", "resource": "user",
        "action": "read", "description": "View user details"},
    {"name": "user:update", "resource": "user", "action": "update",
        "description": "Update user information"},
    {"name": "user:delete", "resource": "user",
        "action": "delete", "description": "Delete users"},
    {"name": "user:list", "resource": "user",
        "action": "list", "description": "List all users"},

    # Key Management
    {"name": "key:create", "resource": "key",
        "action": "create", "description": "Create API keys"},
    {"name": "key:read", "resource": "key", "action": "read",
        "description": "View API key details"},
    {"name": "key:update", "resource": "key",
        "action": "update", "description": "Update API keys"},
    {"name": "key:delete", "resource": "key",
        "action": "delete", "description": "Delete API keys"},
    {"name": "key:list", "resource": "key",
        "action": "list", "description": "List API keys"},

    # Role Management
    {"name": "role:create", "resource": "role",
        "action": "create", "description": "Create roles"},
    {"name": "role:read", "resource": "role",
        "action": "read", "description": "View role details"},
    {"name": "role:update", "resource": "role",
        "action": "update", "description": "Update roles"},
    {"name": "role:delete", "resource": "role",
        "action": "delete", "description": "Delete roles"},
    {"name": "role:list", "resource": "role",
        "action": "list", "description": "List all roles"},
    {"name": "role:assign", "resource": "role", "action": "assign",
        "description": "Assign roles to users"},

    # Permission Management
    {"name": "permission:create", "resource": "permission",
        "action": "create", "description": "Create permissions"},
    {"name": "permission:read", "resource": "permission",
        "action": "read", "description": "View permission details"},
    {"name": "permission:delete", "resource": "permission",
        "action": "delete", "description": "Delete permissions"},
    {"name": "permission:list", "resource": "permission",
        "action": "list", "description": "List all permissions"},

    # Connector Management
    {"name": "connector:create", "resource": "connector",
        "action": "create", "description": "Create connectors"},
    {"name": "connector:read", "resource": "connector",
        "action": "read", "description": "View connector details"},
    {"name": "connector:update", "resource": "connector",
        "action": "update", "description": "Update connectors"},
    {"name": "connector:delete", "resource": "connector",
        "action": "delete", "description": "Delete connectors"},
    {"name": "connector:list", "resource": "connector",
        "action": "list", "description": "List all connectors"},

    # Audit & Monitoring
    {"name": "audit:read", "resource": "audit",
        "action": "read", "description": "View audit logs"},
    {"name": "metrics:read", "resource": "metrics",
        "action": "read", "description": "View metrics"},

    # Secrets Management
    {"name": "secret:create", "resource": "secret",
        "action": "create", "description": "Create secrets"},
    {"name": "secret:read", "resource": "secret",
        "action": "read", "description": "View secrets"},
    {"name": "secret:update", "resource": "secret",
        "action": "update", "description": "Update secrets"},
    {"name": "secret:delete", "resource": "secret",
        "action": "delete", "description": "Delete secrets"},
]


# Default roles with their permissions
DEFAULT_ROLES = [
    {
        "name": "admin",
        "description": "Full system access with all permissions",
        "permissions": [
            "api:create", "api:read", "api:update", "api:delete", "api:list",
            "user:create", "user:read", "user:update", "user:delete", "user:list",
            "key:create", "key:read", "key:update", "key:delete", "key:list",
            "role:create", "role:read", "role:update", "role:delete", "role:list", "role:assign",
            "permission:create", "permission:read", "permission:delete", "permission:list",
            "connector:create", "connector:read", "connector:update", "connector:delete", "connector:list",
            "audit:read", "metrics:read",
            "secret:create", "secret:read", "secret:update", "secret:delete",
        ]
    },
    {
        "name": "developer",
        "description": "API development and management access",
        "permissions": [
            "api:create", "api:read", "api:update", "api:list",
            "connector:create", "connector:read", "connector:update", "connector:list",
            "key:create", "key:read", "key:list",
            "metrics:read",
        ]
    },
    {
        "name": "editor",
        "description": "Can view and edit existing resources",
        "permissions": [
            "api:read", "api:update", "api:list",
            "connector:read", "connector:update", "connector:list",
            "key:read", "key:list",
            "metrics:read",
        ]
    },
    {
        "name": "viewer",
        "description": "Read-only access to resources",
        "permissions": [
            "api:read", "api:list",
            "connector:read", "connector:list",
            "key:read", "key:list",
            "metrics:read",
        ]
    },
]


async def seed_permissions(manager: RBACManager) -> dict:
    """Seed default permissions."""
    created = []
    skipped = []

    logger.info(f"Seeding {len(DEFAULT_PERMISSIONS)} permissions...")

    for perm_data in DEFAULT_PERMISSIONS:
        try:
            # Check if permission already exists
            existing_perms = await manager.list_permissions()
            if any(p.name == perm_data["name"] for p in existing_perms):
                logger.debug(
                    f"Permission '{perm_data['name']}' already exists, skipping")
                skipped.append(perm_data["name"])
                continue

            permission = await manager.create_permission(
                name=perm_data["name"],
                resource=perm_data["resource"],
                action=perm_data["action"],
                description=perm_data.get("description"),
            )
            created.append(permission.name)
            logger.debug(f"Created permission: {permission.name}")

        except Exception as e:
            logger.error(
                f"Failed to create permission '{perm_data['name']}': {e}")

    return {"created": created, "skipped": skipped}


async def seed_roles(manager: RBACManager) -> dict:
    """Seed default roles."""
    created = []
    skipped = []

    logger.info(f"Seeding {len(DEFAULT_ROLES)} roles...")

    for role_data in DEFAULT_ROLES:
        try:
            # Check if role already exists
            existing_role = await manager.get_role_by_name(role_data["name"])
            if existing_role:
                logger.debug(
                    f"Role '{role_data['name']}' already exists, skipping")
                skipped.append(role_data["name"])
                continue

            role = await manager.create_role(
                name=role_data["name"],
                description=role_data["description"],
                permissions=role_data["permissions"],
            )
            created.append(role.name)
            logger.debug(f"Created role: {role.name}")

        except Exception as e:
            logger.error(f"Failed to create role '{role_data['name']}': {e}")

    return {"created": created, "skipped": skipped}


async def seed_rbac():
    """Main function to seed RBAC data."""
    logger.info("Starting RBAC seeding...")

    # Initialize database
    db_manager = get_db_manager()
    await db_manager.initialize()

    try:
        # Get database session
        async for session in db_manager.get_session():
            manager = RBACManager(session)

            # Seed permissions first
            perm_results = await seed_permissions(manager)
            logger.info(
                f"Permissions: {len(perm_results['created'])} created, "
                f"{len(perm_results['skipped'])} skipped"
            )

            # Seed roles
            role_results = await seed_roles(manager)
            logger.info(
                f"Roles: {len(role_results['created'])} created, "
                f"{len(role_results['skipped'])} skipped"
            )

            logger.info("RBAC seeding completed successfully!")

            # Print summary
            print("\n" + "="*60)
            print("RBAC SEEDING SUMMARY")
            print("="*60)
            print(f"\nPermissions Created: {len(perm_results['created'])}")
            if perm_results['created']:
                for p in perm_results['created'][:5]:
                    print(f"  - {p}")
                if len(perm_results['created']) > 5:
                    print(f"  ... and {len(perm_results['created']) - 5} more")

            print(f"\nRoles Created: {len(role_results['created'])}")
            if role_results['created']:
                for r in role_results['created']:
                    print(f"  - {r}")

            print(
                f"\nPermissions Skipped (already exist): {len(perm_results['skipped'])}")
            print(
                f"Roles Skipped (already exist): {len(role_results['skipped'])}")
            print("\n" + "="*60)

            break  # Exit after first session

    except Exception as e:
        logger.error(f"Failed to seed RBAC: {e}", exc_info=True)
        raise
    finally:
        await db_manager.shutdown()


if __name__ == "__main__":
    asyncio.run(seed_rbac())
