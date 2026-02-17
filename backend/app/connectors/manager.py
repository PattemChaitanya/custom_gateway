"""Connector management and orchestration."""

from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Connector
from app.logging_config import get_logger
from .database import create_database_connector
from .queue import create_queue_connector
from .storage import create_storage_connector

logger = get_logger("connector_manager")


class ConnectorManager:
    """Manager for connector lifecycle and operations."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.active_connectors = {}  # Store active connector instances

    async def create_connector(
        self,
        name: str,
        connector_type: str,
        config: Dict[str, Any],
        api_id: Optional[int] = None,
    ) -> Connector:
        """Create a new connector configuration."""
        connector = Connector(
            name=name,
            type=connector_type,
            config=config,
            api_id=api_id,
        )

        self.session.add(connector)
        # Flush to ensure DB assigns autoincrement ID before commit/refresh
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(connector)

        logger.info(f"Created connector: {name} ({connector_type})")
        return connector

    async def get_connector(self, connector_id: int) -> Optional[Connector]:
        """Get a connector by ID."""
        result = await self.session.execute(
            select(Connector).where(Connector.id == connector_id)
        )
        return result.scalar_one_or_none()

    async def list_connectors(self, api_id: Optional[int] = None) -> list:
        """List all connectors."""
        query = select(Connector)
        if api_id:
            query = query.where(Connector.api_id == api_id)

        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_connector(
        self,
        connector_id: int,
        **kwargs
    ) -> Optional[Connector]:
        """Update a connector."""
        connector = await self.get_connector(connector_id)

        if not connector:
            return None

        for key, value in kwargs.items():
            if hasattr(connector, key) and value is not None:
                setattr(connector, key, value)

        await self.session.commit()
        await self.session.refresh(connector)

        # Remove from active connectors if config changed
        if "config" in kwargs and connector_id in self.active_connectors:
            await self.disconnect_connector(connector_id)

        logger.info(f"Updated connector: {connector_id}")
        return connector

    async def delete_connector(self, connector_id: int) -> bool:
        """Delete a connector."""
        connector = await self.get_connector(connector_id)

        if not connector:
            return False

        # Disconnect if active
        if connector_id in self.active_connectors:
            await self.disconnect_connector(connector_id)

        await self.session.delete(connector)
        await self.session.commit()

        logger.info(f"Deleted connector: {connector_id}")
        return True

    async def connect_connector(self, connector_id: int):
        """Establish connection using connector configuration."""
        connector = await self.get_connector(connector_id)

        if not connector:
            raise ValueError(f"Connector {connector_id} not found")

        # Check if already connected
        if connector_id in self.active_connectors:
            logger.info(f"Connector {connector_id} already connected")
            return self.active_connectors[connector_id]

        # Create connector instance based on type
        connector_type = connector.type.lower()

        try:
            if connector_type in ["postgresql", "mongodb"]:
                instance = create_database_connector(
                    connector_type, connector.config)
            elif connector_type in ["redis", "kafka"]:
                instance = create_queue_connector(
                    connector_type, connector.config)
            elif connector_type in ["s3", "azure"]:
                instance = create_storage_connector(
                    connector_type, connector.config)
            else:
                raise ValueError(f"Unknown connector type: {connector_type}")

            await instance.connect()
            self.active_connectors[connector_id] = instance

            logger.info(f"Connected connector {connector_id}")
            return instance

        except Exception as e:
            logger.error(f"Failed to connect connector {connector_id}: {e}")
            raise

    async def disconnect_connector(self, connector_id: int):
        """Disconnect an active connector."""
        if connector_id not in self.active_connectors:
            return

        instance = self.active_connectors[connector_id]

        try:
            await instance.disconnect()
            del self.active_connectors[connector_id]
            logger.info(f"Disconnected connector {connector_id}")
        except Exception as e:
            logger.error(f"Error disconnecting connector {connector_id}: {e}")

    async def test_connector(self, connector_id: int) -> Dict[str, Any]:
        """Test connector connection."""
        try:
            instance = await self.connect_connector(connector_id)
            healthy = await instance.health_check()

            return {
                "connector_id": connector_id,
                "status": "healthy" if healthy else "unhealthy",
                "connected": True,
            }
        except Exception as e:
            logger.error(f"Connector test failed: {e}")
            return {
                "connector_id": connector_id,
                "status": "error",
                "connected": False,
                "error": str(e),
            }

    async def disconnect_all(self):
        """Disconnect all active connectors."""
        for connector_id in list(self.active_connectors.keys()):
            await self.disconnect_connector(connector_id)
