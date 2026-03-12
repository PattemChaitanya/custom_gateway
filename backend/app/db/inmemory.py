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

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Dict, Optional, List, Any
import logging

logger = logging.getLogger(__name__)


class QueryResult:
    """Wrapper for query results to mimic SQLAlchemy Result object."""

    def __init__(self, results: List[Any], rowcount: int = 0):
        """Initialize query result with list of objects."""
        self._results = results
        self.rowcount = rowcount

    def scalars(self):
        """Return scalar results accessor."""
        return ScalarResult(self._results)

    def scalar(self):
        """Return first column of first row, or None."""
        return self._results[0] if self._results else None

    def scalar_one_or_none(self):
        """Return first column of the only row, or None. Raise if multiple rows."""
        if len(self._results) == 0:
            return None
        if len(self._results) > 1:
            raise Exception("Multiple results found")
        return self._results[0]

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
        self._api_keys: Dict[int, SimpleNamespace] = {}
        self._environments: Dict[int, SimpleNamespace] = {}
        self._secrets: Dict[int, SimpleNamespace] = {}
        self._audit_logs: Dict[int, SimpleNamespace] = {}

        # Secondary indexes for O(1) lookups on common fields
        self._user_email_index: Dict[str, int] = {}  # email -> user_id

        # ID counters
        self._next_api_id = 1
        self._next_user_id = 1
        self._next_token_id = 1
        self._next_otp_id = 1
        self._next_role_id = 1
        self._next_permission_id = 1
        self._next_user_role_id = 1
        self._next_api_key_id = 1
        self._next_environment_id = 1
        self._next_secret_id = 1
        self._next_audit_log_id = 1

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
        api = SimpleNamespace()
        api.id = self._next_api_id
        api.name = payload.get("name")
        api.version = payload.get("version")
        api.description = payload.get("description")
        api.owner_id = payload.get("owner_id")
        api.type = payload.get("type")
        api.resource = payload.get("resource")
        api.config = payload.get("config")
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
                # Maintain secondary email index
                if hasattr(obj, 'email') and obj.email:
                    self._user_email_index[obj.email] = obj.id
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
            elif 'APIKey' in type_name:
                if not hasattr(obj, 'id') or obj.id is None:
                    obj.id = self._next_api_key_id
                    self._next_api_key_id += 1
                self._api_keys[obj.id] = obj
            elif 'Environment' in type_name:
                if not hasattr(obj, 'id') or obj.id is None:
                    obj.id = self._next_environment_id
                    self._next_environment_id += 1
                self._environments[obj.id] = obj
            elif 'Secret' in type_name:
                if not hasattr(obj, 'id') or obj.id is None:
                    obj.id = self._next_secret_id
                    self._next_secret_id += 1
                self._secrets[obj.id] = obj
            elif 'AuditLog' in type_name:
                if not hasattr(obj, 'id') or obj.id is None:
                    obj.id = self._next_audit_log_id
                    self._next_audit_log_id += 1
                self._audit_logs[obj.id] = obj

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
                user = self._users[obj.id]
                if hasattr(user, 'email') and user.email in self._user_email_index:
                    del self._user_email_index[user.email]
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
            elif obj.id in self._api_keys:
                del self._api_keys[obj.id]
            elif obj.id in self._environments:
                del self._environments[obj.id]
            elif obj.id in self._secrets:
                del self._secrets[obj.id]
            elif obj.id in self._audit_logs:
                del self._audit_logs[obj.id]

    async def execute(self, statement):
        """
        Execute a SQLAlchemy select statement on in-memory data.

        Args:
            statement: SQLAlchemy select statement

        Returns:
            QueryResult: Object with scalars() method for result access
        """
        # Simple implementation to handle basic select queries
        from app.db.models import User, OTP, RefreshToken, Role, Permission, UserRole, APIKey, Environment, Secret, AuditLog

        # Handle UPDATE statements (e.g. update(APIKey).where(...).values(...))
        if hasattr(statement, 'entity_description') and not hasattr(statement, 'column_descriptions'):
            try:
                entity_type = statement.entity_description.get('entity', None)
                storage_map = {
                    User: self._users,
                    OTP: self._otps,
                    RefreshToken: self._refresh_tokens,
                    Role: self._roles,
                    Permission: self._permissions,
                    UserRole: self._user_roles,
                    APIKey: self._api_keys,
                    Environment: self._environments,
                    Secret: self._secrets,
                    AuditLog: self._audit_logs,
                }
                storage = storage_map.get(entity_type)
                if not storage:
                    return QueryResult([], rowcount=0)

                # Get values to set
                update_vals = {}
                if hasattr(statement, '_values') and statement._values:
                    for col_clause, bind_param in statement._values.items():
                        col_name = col_clause.key if hasattr(
                            col_clause, 'key') else str(col_clause)
                        val = bind_param.value if hasattr(
                            bind_param, 'value') else bind_param
                        update_vals[col_name] = val

                if not update_vals:
                    return QueryResult([], rowcount=0)

                # Find matching objects via WHERE criteria
                targets = list(storage.values())
                if hasattr(statement, '_where_criteria') and statement._where_criteria:
                    for criterion in statement._where_criteria:
                        try:
                            if hasattr(criterion, 'left') and hasattr(criterion, 'right'):
                                left_val = criterion.left.key if hasattr(
                                    criterion.left, 'key') else str(criterion.left)
                                right_val = criterion.right.value if hasattr(
                                    criterion.right, 'value') else criterion.right
                                targets = [o for o in targets if getattr(
                                    o, left_val, None) == right_val]
                        except Exception:
                            pass

                # Apply updates
                for obj in targets:
                    for k, v in update_vals.items():
                        setattr(obj, k, v)

                return QueryResult([], rowcount=len(targets))
            except Exception as e:
                logger.warning(f"UPDATE execution error: {e}")
                return QueryResult([], rowcount=0)

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
                        # Fast-path: check for simple email equality filter
                        email_match = self._try_email_index_lookup(statement)
                        if email_match is not None:
                            return QueryResult(email_match)
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
                    elif entity_type == APIKey or entity_name == 'APIKey':
                        results = list(self._api_keys.values())
                    elif entity_type == Environment or entity_name == 'Environment':
                        results = list(self._environments.values())
                    elif entity_type == Secret or entity_name == 'Secret':
                        results = list(self._secrets.values())
                    elif entity_type == AuditLog or entity_name == 'AuditLog':
                        results = list(self._audit_logs.values())
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

    def _try_email_index_lookup(self, statement) -> Optional[List[SimpleNamespace]]:
        """Try to resolve a User query via the email index (O(1)).

        Returns a list of matching users if the query is a simple
        ``User.email == <value>`` filter, otherwise returns ``None`` to
        fall back to the generic linear scan.
        """
        if not (hasattr(statement, '_where_criteria') and statement._where_criteria):
            return None
        if len(statement._where_criteria) != 1:
            return None
        criterion = statement._where_criteria[0]
        try:
            if hasattr(criterion, 'left') and hasattr(criterion, 'right'):
                left_key = criterion.left.key if hasattr(
                    criterion.left, 'key') else None
                if left_key == 'email':
                    target = criterion.right.value if hasattr(
                        criterion.right, 'value') else None
                    if target is not None:
                        uid = self._user_email_index.get(target)
                        if uid is not None and uid in self._users:
                            return [self._users[uid]]
                        return []
        except Exception:
            pass
        return None

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
        self._api_keys.clear()
        self._environments.clear()
        self._secrets.clear()
        self._audit_logs.clear()
        self._user_email_index.clear()

        self._next_api_id = 1
        self._next_user_id = 1
        self._next_token_id = 1
        self._next_otp_id = 1
        self._next_api_key_id = 1
        self._next_environment_id = 1
        self._next_secret_id = 1
        self._next_audit_log_id = 1

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
            "api_keys": len(self._api_keys),
            "environments": len(self._environments),
            "secrets": len(self._secrets),
            "audit_logs": len(self._audit_logs),
        }

    def _normalize_dt(self, value: Any) -> Optional[datetime]:
        if value is None:
            return None
        if isinstance(value, datetime):
            dt = value
        elif isinstance(value, str):
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        else:
            return None

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    async def list_audit_logs(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
    ) -> List[SimpleNamespace]:
        start_dt = self._normalize_dt(start_date)
        end_dt = self._normalize_dt(end_date)

        rows = list(self._audit_logs.values())
        if user_id is not None:
            rows = [r for r in rows if getattr(r, "user_id", None) == user_id]
        if action and action.strip():
            target = action.strip().lower()
            rows = [r for r in rows if str(
                getattr(r, "action", "")).lower() == target]
        if status and status.strip():
            target = status.strip().lower()
            rows = [r for r in rows if str(
                getattr(r, "status", "")).lower() == target]
        if start_dt is not None:
            rows = [
                r for r in rows
                if (self._normalize_dt(getattr(r, "timestamp", None)) or datetime.min.replace(tzinfo=timezone.utc)) >= start_dt
            ]
        if end_dt is not None:
            rows = [
                r for r in rows
                if (self._normalize_dt(getattr(r, "timestamp", None)) or datetime.max.replace(tzinfo=timezone.utc)) <= end_dt
            ]

        rows.sort(key=lambda r: self._normalize_dt(getattr(r, "timestamp", None))
                  or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return rows[:limit]

    async def get_audit_log_statistics(self) -> Dict[str, Any]:
        rows = list(self._audit_logs.values())
        logs_by_type: Dict[str, int] = {}
        logs_by_user: Dict[int, int] = {}
        oldest = None

        for row in rows:
            action = getattr(row, "action", None)
            if action:
                logs_by_type[action] = logs_by_type.get(action, 0) + 1

            uid = getattr(row, "user_id", None)
            if uid is not None:
                logs_by_user[uid] = logs_by_user.get(uid, 0) + 1

            ts = self._normalize_dt(getattr(row, "timestamp", None))
            if ts and (oldest is None or ts < oldest):
                oldest = ts

        return {
            "total_logs": len(rows),
            "audit_logs_count": len(rows),
            "metrics_count": 0,
            "logs_by_type": logs_by_type,
            "logs_by_user": logs_by_user,
            "oldest_audit_log": oldest.isoformat() if oldest else None,
            "oldest_metric": None,
        }

    async def list_user_audit_activity(self, target_user_id: int, days: int = 30, limit: int = 500) -> List[SimpleNamespace]:
        since = datetime.now(timezone.utc) - timedelta(days=days)
        rows = [
            r for r in self._audit_logs.values()
            if getattr(r, "user_id", None) == target_user_id and
            (self._normalize_dt(getattr(r, "timestamp", None))
             or datetime.min.replace(tzinfo=timezone.utc)) >= since
        ]
        rows.sort(key=lambda r: self._normalize_dt(getattr(r, "timestamp", None))
                  or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return rows[:limit]

    async def list_failed_audit_attempts(self, hours: int = 24, limit: int = 500) -> List[SimpleNamespace]:
        since = datetime.now(timezone.utc) - timedelta(hours=hours)

        rows = []
        for row in self._audit_logs.values():
            ts = self._normalize_dt(getattr(row, "timestamp", None))
            if not ts or ts < since:
                continue

            status_val = str(getattr(row, "status", "")).lower()
            action_val = str(getattr(row, "action", "")).lower()
            if status_val in ("failure", "error") or "failure" in action_val:
                rows.append(row)

        rows.sort(key=lambda r: self._normalize_dt(getattr(r, "timestamp", None))
                  or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return rows[:limit]

    async def cleanup_old_logs(self, retention_days: int = 30) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        to_delete = []
        for row_id, row in self._audit_logs.items():
            ts = self._normalize_dt(getattr(row, "timestamp", None))
            if ts and ts < cutoff:
                to_delete.append(row_id)

        for row_id in to_delete:
            del self._audit_logs[row_id]

        return len(to_delete)

    def __repr__(self) -> str:
        """String representation of the in-memory database."""
        stats = self.get_stats()
        return (
            f"InMemoryDB(apis={stats['apis']}, users={stats['users']}, "
            f"tokens={stats['refresh_tokens']}, otps={stats['otps']})"
        )
