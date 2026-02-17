"""Re-export RBAC manager and decorators from app.authorizers.rbac

This small shim allows code that imports `app.authorization.rbac` to
continue working with the real implementation under `app.authorizers`.
"""
from app.authorizers.rbac import RBACManager, require_permission, require_role

__all__ = ["RBACManager", "require_permission", "require_role"]
