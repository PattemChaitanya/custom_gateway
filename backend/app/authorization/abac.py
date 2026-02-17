"""Minimal ABAC compatibility layer used by tests.

Provides a small `Policy` class with an `evaluate` helper and an
`ABACManager` that can create `Policy` objects. The implementation is
intentionally lightweight and matches the API used by the test suite.
"""
from typing import Any, Dict, Optional


class Policy:
    """Simple policy object used in tests.

    The policy expects a dict with a `condition` key containing a Python
    expression that can be evaluated against a context dict.
    """

    def __init__(self, name: str, rules: Dict[str, Any]):
        self.name = name
        self.rules = rules or {}

    def evaluate(self, context: Dict[str, Any]) -> bool:
        cond = self.rules.get("condition")
        if not cond:
            return False

        # Evaluate the condition string with the provided context as locals.
        # This is intentionally small and used only in tests.
        try:
            return bool(eval(cond, {}, context))
        except Exception:
            return False


class ABACManager:
    """Very small manager that creates Policy objects."""

    def __init__(self, session: Optional[Any] = None):
        self.session = session

    async def create_policy(self, name: str, resource_type: str, rules: Dict[str, Any]):
        # Return a Policy-like object containing the data the tests expect.
        p = Policy(name=name, rules=rules)
        # attach resource_type for compatibility with tests
        p.resource_type = resource_type
        return p


__all__ = ["Policy", "ABACManager"]
