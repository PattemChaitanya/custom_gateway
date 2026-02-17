"""Decorator shims for permission/role requirement APIs.

Re-exports `require_permission` and `require_role` from the RBAC implementation
so tests can import them from `app.authorization.decorators`.
"""
from app.authorizers.rbac import require_permission, require_role

__all__ = ["require_permission", "require_role"]
