"""
In-Memory Database Fallback

Provides a simple in-memory database implementation that mimics the SQLAlchemy
AsyncSession interface for seamless fallback when PostgreSQL is unavailable.
"""

from types import SimpleNamespace
from typing import Dict, Optional, List, Any
import logging

logger = logging.getLogger(__name__)


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
        
        # ID counters
        self._next_api_id = 1
        self._next_user_id = 1
        self._next_token_id = 1
        self._next_otp_id = 1
        
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
                raise ValueError("API with same name and version already exists")

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
        """
        No-op refresh for compatibility with SQLAlchemy sessions.
        
        Args:
            obj: Object to refresh (no-op in memory)
        """
        pass
    
    async def add(self, obj: SimpleNamespace) -> None:
        """
        No-op add for compatibility with SQLAlchemy sessions.
        
        Args:
            obj: Object to add (no-op in memory, objects are added via specific methods)
        """
        pass
    
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
    
    async def execute(self, statement):
        """
        Placeholder for execute method to maintain interface compatibility.
        
        Args:
            statement: SQL statement (not used in in-memory DB)
            
        Raises:
            NotImplementedError: This method is not implemented for in-memory DB
        """
        raise NotImplementedError(
            "InMemoryDB does not support raw SQL execution. "
            "Use specific CRUD methods instead."
        )
    
    # Utility Methods
    
    def clear_all(self) -> None:
        """Clear all data from the in-memory database."""
        self._apis.clear()
        self._users.clear()
        self._refresh_tokens.clear()
        self._otps.clear()
        
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
