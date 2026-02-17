"""Compatibility package exposing authorization APIs.

This module provides a thin compatibility layer so older imports under
`app.authorization` continue to work while the implementation lives in
`app.authorizers`.
"""

__all__ = ["rbac", "abac", "decorators"]
