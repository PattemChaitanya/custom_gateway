"""
In-Memory Database Fallback

Provides a simple in-memory database implementation that mimics the SQLAlchemy
AsyncSession interface for seamless fallback when PostgreSQL is unavailable.
"""

"""
In-Memory Database Fallback

Provides a simple in-memory database implementation that mimics the SQLAlchemy
AsyncSession interface for seamless fallback when PostgreSQL is unavailable.
"""

from types import SimpleNamespace
from typing import Dict, Optional, List, Any
import logging

logger = logging.getLogger(__name__)


class QueryResult:
    """Wrapper for query results to mimic SQLAlchemy Result object."""

    def __init__(self, results: List[Any]):
        """Initialize query result with list of objects."""
        self._results = results

    def scalars(self):
        """Return scalar results accessor."""
        return ScalarResult(self._results)

    def first(self):
        """Return first result or None."""
        return self._results[0] if self._results else None

    def all(self):
        """Return all results."""
        return self._results


class ScalarResult:
    """Scalar result accessor to mimic SQLAlchemy ScalarResult."""

    def __init__(self, results: List[Any]):
        """Initialize with list of results."""
        self._results = results

    def first(self):
        """Return first result or None."""
        return self._results[0] if self._results else None

    def all(self):
        """Return all results."""
        return self._results

    def one(self):
        """Return single result, raise if multiple or none."""
        if len(self._results) == 0:
            raise Exception("No result found")
        if len(self._results) > 1:
            raise Exception("Multiple results found")
        return self._results[0]

    def one_or_none(self):
        """Return single result or None."""
        if len(self._results) == 0:
            return None
        if len(self._results) > 1:
            raise Exception("Multiple results found")
        return self._results[0]


class InMemoryDB:
    """
    Simple in-memory database for fallback when PostgreSQL is unavailable.

    This class provides async methods that match the CRUD layer expectations,
    allowing seamless switching between PostgreSQL and in-memory storage.
    Objects returned are SimpleNamespace instances so Pydantic's `from_attributes`
    mode can read them like ORM objects.

    Note: This is a simple implementation for development/fallback purposes.
    Data is not persisted and will be lost when the application restarts.
    """

    def __init__(self) -> None:
        """Initialize in-memory database with empty storage."""
        self.in_memory = True  # Flag to identify this as in-memory DB

        # Storage dictionaries
        self._apis: Dict[int, SimpleNamespace] = {}
        self._users: Dict[int, SimpleNamespace] = {}
        self._refresh_tokens: Dict[int, SimpleNamespace] = {}
        self._otps: Dict[int, SimpleNamespace] = {}
        self._roles: Dict[int, SimpleNamespace] = {}
        self._permissions: Dict[int, SimpleNamespace] = {}
        self._user_roles: Dict[int, SimpleNamespace] = {}

        # ID counters
        self._next_api_id = 1
        self._next_user_id = 1
        self._next_token_id = 1
        self._next_otp_id = 1
        self._next_role_id = 1
        self._next_permission_id = 1
        self._next_user_role_id = 1

        logger.info("In-memory database initialized")

    # API Management Methods

    async def create_api(self, payload: Dict[str, Any]) -> SimpleNamespace:
        """
        Create a new API entry in memory.

        Args:
            payload: Dictionary containing API data

        Returns:
            SimpleNamespace: Created API object

        Raises:
            ValueError: If API with same name and version exists
        """
        # Check for existing API with same name+version
        for existing_api in self._apis.values():
            if (existing_api.name == payload.get("name") and
                    existing_api.version == payload.get("version")):
                raise ValueError(
                    "API with same name and version already exists")

        # Create new API object
        # Create new API object
        api = SimpleNamespace()
        api.id = self._next_api_id
        api.name = payload.get("name")
        api.version = payload.get("version")
        api.description = payload.get("description")
        api.owner_id = payload.get("owner_id")
        api.type = payload.get("type")
        api.resource = payload.get("resource")
        api.type = payload.get("type")
        api.resource = payload.get("resource")
        api.config = payload.get("config")
        api.created_at = payload.get("created_at")
        api.updated_at = payload.get("updated_at")
        api.created_at = payload.get("created_at")
        api.updated_at = payload.get("updated_at")

        self._apis[self._next_api_id] = api
        self._next_api_id += 1

        logger.debug(f"Created API: {api.name} v{api.version} (id={api.id})")
        return api

    async def list_apis(self) -> List[SimpleNamespace]:
        """
        List all APIs in memory.

        Returns:
            List[SimpleNamespace]: List of all API objects
        """
        return list(self._apis.values())

    async def get_api(self, api_id: int) -> Optional[SimpleNamespace]:
        """
        Get an API by ID.

        Args:
            api_id: API identifier

        Returns:
            SimpleNamespace | None: API object or None if not found
        """
        return self._apis.get(api_id)

    async def update_api(
        self,
        api: SimpleNamespace,
        patch: Dict[str, Any]
    ) -> SimpleNamespace:
        """
        Update an API with new data.

        Args:
            api: API object to update
            patch: Dictionary of fields to update

        Returns:
            SimpleNamespace: Updated API object
        """
        for key, value in patch.items():
            if value is not None and hasattr(api, key):
                setattr(api, key, value)

        # Ensure it's stored (in case it's a new reference)
        self._apis[api.id] = api

        logger.debug(f"Updated API: {api.name} (id={api.id})")
        return api

    async def delete_api(self, api: SimpleNamespace) -> None:
        """
        Delete an API from memory.

        Args:
            api: API object to delete
        """
        if api.id in self._apis:
            del self._apis[api.id]
            logger.debug(f"Deleted API: {api.name} (id={api.id})")

    # Session-like Methods (for compatibility with SQLAlchemy interface)

    async def commit(self) -> None:
        """
        No-op commit for compatibility with SQLAlchemy sessions.

        Since this is an in-memory database, changes are immediate and
        don't require committing.
        """
        pass

    async def rollback(self) -> None:
        """
        No-op rollback for compatibility with SQLAlchemy sessions.

        Since this is an in-memory database without transaction support,
        rollback doesn't have an effect.
        """
        logger.warning("Rollback called on in-memory database (no-op)")

    async def refresh(self, obj: SimpleNamespace) -> None:
        """        No-op refresh for compatibility with SQLAlchemy sessions.

        Args:
            obj: Object to refresh (no-op in memory)
        """
        pass

    async def flush(self) -> None:
        """
        No-op flush for compatibility with SQLAlchemy sessions.

        Since this is an in-memory database, changes are immediate and
        don't require flushing. IDs are assigned in add() method.
        """
        pass

    def add(self, obj: SimpleNamespace) -> None:
        """
        Add object to in-memory database.

        Args:
            obj: Object to add (User, OTP, RefreshToken, Role, Permission, UserRole, etc.)
        """
        # Determine object type and add to appropriate storage
        obj_type = getattr(obj, '__class__', None)
        if obj_type:
            type_name = obj_type.__name__ if hasattr(
                obj_type, '__name__') else str(obj_type)

            if 'User' in type_name:
                if not hasattr(obj, 'id') or obj.id is None:
                    obj.id = self._next_user_id
                    self._next_user_id += 1
                self._users[obj.id] = obj
            elif 'OTP' in type_name:
                if not hasattr(obj, 'id') or obj.id is None:
                    obj.id = self._next_otp_id
                    self._next_otp_id += 1
                self._otps[obj.id] = obj
            elif 'RefreshToken' in type_name:
                if not hasattr(obj, 'id') or obj.id is None:
                    obj.id = self._next_token_id
                    self._next_token_id += 1
                self._refresh_tokens[obj.id] = obj
            elif 'Role' in type_name:
                if not hasattr(obj, 'id') or obj.id is None:
                    obj.id = self._next_role_id
                    self._next_role_id += 1
                self._roles[obj.id] = obj
            elif 'Permission' in type_name:
                if not hasattr(obj, 'id') or obj.id is None:
                    obj.id = self._next_permission_id
                    self._next_permission_id += 1
                self._permissions[obj.id] = obj
            elif 'UserRole' in type_name:
                if not hasattr(obj, 'id') or obj.id is None:
                    obj.id = self._next_user_role_id
                    self._next_user_role_id += 1
                self._user_roles[obj.id] = obj

    async def delete(self, obj: SimpleNamespace) -> None:
        """
        Delete an object from memory.

        Args:
            obj: Object to delete
        """
        # Try to determine object type and delete appropriately
        if hasattr(obj, 'id'):
            if obj.id in self._apis:
                await self.delete_api(obj)
            elif obj.id in self._users:
                del self._users[obj.id]
            elif obj.id in self._refresh_tokens:
                del self._refresh_tokens[obj.id]
            elif obj.id in self._otps:
                del self._otps[obj.id]
            elif obj.id in self._roles:
                del self._roles[obj.id]
            elif obj.id in self._permissions:
                del self._permissions[obj.id]
            elif obj.id in self._user_roles:
                del self._user_roles[obj.id]

    async def execute(self, statement):
        """
        Execute a SQLAlchemy select statement on in-memory data.

        Args:
            statement: SQLAlchemy select statement

        Returns:
            QueryResult: Object with scalars() method for result access
        """
        # Simple implementation to handle basic select queries
        from app.db.models import User, OTP, RefreshToken, Role, Permission, UserRole

        # Determine which model is being queried
        if hasattr(statement, '_propagate_attrs') and hasattr(statement, 'column_descriptions'):
            # SQLAlchemy 2.0 style query
            try:
                # Get the entity being queried
                entities = statement.column_descriptions
                if entities:
                    entity_type = entities[0].get(
                        'entity', entities[0].get('type'))
                    entity_name = entity_type.__name__ if hasattr(
                        entity_type, '__name__') else str(entity_type)

                    # Query the appropriate storage
                    if entity_type == User or entity_name == 'User':
                        results = list(self._users.values())
                    elif entity_type == OTP or entity_name == 'OTP':
                        results = list(self._otps.values())
                    elif entity_type == RefreshToken or entity_name == 'RefreshToken':
                        results = list(self._refresh_tokens.values())
                    elif entity_type == Role or entity_name == 'Role':
                        results = list(self._roles.values())
                    elif entity_type == Permission or entity_name == 'Permission':
                        results = list(self._permissions.values())
                    elif entity_type == UserRole or entity_name == 'UserRole':
                        results = list(self._user_roles.values())
                    else:
                        results = []

                    # Apply where clause filtering
                    if hasattr(statement, '_where_criteria') and statement._where_criteria:
                        filtered_results = []
                        for obj in results:
                            match = True
                            for criterion in statement._where_criteria:
                                # Handle different criterion types
                                try:
                                    # Handle NOT operator (UnaryExpression)
                                    if hasattr(criterion, '__class__') and 'UnaryExpression' in criterion.__class__.__name__:
                                        if hasattr(criterion, 'element'):
                                            # This is a NOT expression
                                            inner = criterion.element
                                            if hasattr(inner, 'key'):
                                                attr_name = inner.key
                                                if hasattr(obj, attr_name):
                                                    # For NOT, we want the opposite of the attribute value
                                                    if getattr(obj, attr_name):
                                                        match = False
                                                        break
                                    # Handle regular comparison (BinaryExpression)
                                    elif hasattr(criterion, 'left') and hasattr(criterion, 'right'):
                                        left_val = criterion.left.key if hasattr(
                                            criterion.left, 'key') else str(criterion.left)
                                        right_val = criterion.right.value if hasattr(
                                            criterion.right, 'value') else criterion.right

                                        if hasattr(obj, left_val):
                                            obj_val = getattr(obj, left_val)
                                            if obj_val != right_val:
                                                match = False
                                                break
                                except Exception as ex:
                                    logger.debug(
                                        f"Error evaluating criterion: {ex}")
                                    pass
                            if match:
                                filtered_results.append(obj)
                        results = filtered_results

                    return QueryResult(results)
            except Exception as e:
                logger.warning(f"Query execution error: {e}")
                return QueryResult([])

        return QueryResult([])

    # Utility Methods

    def clear_all(self) -> None:
        """Clear all data from the in-memory database."""
        self._apis.clear()
        self._users.clear()
        self._refresh_tokens.clear()
        self._otps.clear()
        self._roles.clear()
        self._permissions.clear()
        self._user_roles.clear()

        self._next_api_id = 1
        self._next_user_id = 1
        self._next_token_id = 1
        self._next_otp_id = 1

        logger.info("In-memory database cleared")

    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about the in-memory database.

        Returns:
            dict: Dictionary with counts of stored objects
        """
        return {
            "apis": len(self._apis),
            "users": len(self._users),
            "refresh_tokens": len(self._refresh_tokens),
            "otps": len(self._otps),
        }

    def __repr__(self) -> str:
        """String representation of the in-memory database."""
        stats = self.get_stats()
        return (
            f"InMemoryDB(apis={stats['apis']}, users={stats['users']}, "
            f"tokens={stats['refresh_tokens']}, otps={stats['otps']})"
        )
