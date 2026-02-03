"""Policy-based authorization engine (ABAC - Attribute-Based Access Control)."""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from app.logging_config import get_logger

logger = get_logger("policy_engine")


class Action(str, Enum):
    """Standard CRUD actions."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    LIST = "list"


@dataclass
class Permission:
    """Represents a permission with resource and action."""
    resource: str
    action: Action
    conditions: Optional[Dict[str, Any]] = None
    
    def matches(self, resource: str, action: str) -> bool:
        """Check if permission matches resource and action."""
        return self.resource == resource and self.action.value == action


@dataclass
class ResourcePermission:
    """Represents permissions for a specific resource instance."""
    resource_type: str
    resource_id: str
    owner_id: Optional[int] = None
    visibility: str = "private"  # private, team, public
    metadata: Optional[Dict[str, Any]] = None


class PolicyEngine:
    """Policy evaluation engine for attribute-based access control."""
    
    def __init__(self):
        self.policies = []
    
    def add_policy(self, policy: Dict[str, Any]):
        """Add a policy to the engine."""
        self.policies.append(policy)
    
    def evaluate(
        self,
        user: Dict[str, Any],
        resource: ResourcePermission,
        action: str,
    ) -> bool:
        """Evaluate if user can perform action on resource.
        
        Args:
            user: User object with id, roles, attributes
            resource: Resource being accessed
            action: Action being performed
        
        Returns:
            True if allowed, False otherwise
        """
        # 1. Check if user is owner
        if resource.owner_id == user.get("id"):
            logger.debug(f"Access granted: User {user['id']} is owner of resource")
            return True
        
        # 2. Check if user is superuser
        if user.get("is_superuser"):
            logger.debug(f"Access granted: User {user['id']} is superuser")
            return True
        
        # 3. Check visibility rules
        if resource.visibility == "public" and action == "read":
            logger.debug("Access granted: Public resource, read action")
            return True
        
        # 4. Check user roles
        user_roles = user.get("roles", [])
        if isinstance(user_roles, str):
            user_roles = user_roles.split(',')
        
        # Admin role has all permissions
        if "admin" in user_roles:
            logger.debug(f"Access granted: User {user['id']} has admin role")
            return True
        
        # Editor role can read and update
        if "editor" in user_roles and action in ["read", "update"]:
            logger.debug(f"Access granted: User {user['id']} has editor role")
            return True
        
        # Viewer role can only read
        if "viewer" in user_roles and action == "read":
            logger.debug(f"Access granted: User {user['id']} has viewer role")
            return True
        
        # 5. Check custom policies
        for policy in self.policies:
            if self._evaluate_policy(policy, user, resource, action):
                logger.debug(f"Access granted: Custom policy matched")
                return True
        
        logger.warning(
            f"Access denied: User {user.get('id')} cannot {action} {resource.resource_type}/{resource.resource_id}"
        )
        return False
    
    def _evaluate_policy(
        self,
        policy: Dict[str, Any],
        user: Dict[str, Any],
        resource: ResourcePermission,
        action: str,
    ) -> bool:
        """Evaluate a single policy."""
        # Check if policy applies to this resource type
        if policy.get("resource_type") and policy["resource_type"] != resource.resource_type:
            return False
        
        # Check if policy applies to this action
        if policy.get("actions") and action not in policy["actions"]:
            return False
        
        # Check conditions
        conditions = policy.get("conditions", {})
        
        for key, value in conditions.items():
            user_value = user.get(key)
            if user_value != value:
                return False
        
        return True
    
    def can_create(self, user: Dict[str, Any], resource_type: str) -> bool:
        """Check if user can create a resource of given type."""
        resource = ResourcePermission(
            resource_type=resource_type,
            resource_id="*",
        )
        return self.evaluate(user, resource, "create")
    
    def can_read(self, user: Dict[str, Any], resource: ResourcePermission) -> bool:
        """Check if user can read a resource."""
        return self.evaluate(user, resource, "read")
    
    def can_update(self, user: Dict[str, Any], resource: ResourcePermission) -> bool:
        """Check if user can update a resource."""
        return self.evaluate(user, resource, "update")
    
    def can_delete(self, user: Dict[str, Any], resource: ResourcePermission) -> bool:
        """Check if user can delete a resource."""
        return self.evaluate(user, resource, "delete")


# Global policy engine instance
policy_engine = PolicyEngine()


def check_permission(
    user: Dict[str, Any],
    resource_type: str,
    resource_id: str,
    action: str,
    owner_id: Optional[int] = None,
) -> bool:
    """Convenience function to check permissions."""
    resource = ResourcePermission(
        resource_type=resource_type,
        resource_id=resource_id,
        owner_id=owner_id,
    )
    return policy_engine.evaluate(user, resource, action)
