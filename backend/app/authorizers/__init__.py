"""Authorization module for RBAC and ABAC."""

from .rbac import (
    RBACManager,
    has_permission,
    require_permission,
    require_role,
)
from .policies import (
    PolicyEngine,
    Permission,
    ResourcePermission,
)
from .middleware import register_authorization_middleware

__all__ = [
    "RBACManager",
    "has_permission",
    "require_permission",
    "require_role",
    "PolicyEngine",
    "Permission",
    "ResourcePermission",
    "register_authorization_middleware",
]
