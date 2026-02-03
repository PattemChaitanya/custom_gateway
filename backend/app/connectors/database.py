"""Database connectors for various databases."""

from typing import Dict, Any, Optional, List
import asyncpg
import pymongo
from app.logging_config import get_logger

logger = get_logger("db_connector")


class DatabaseConnector:
    """Base class for database connectors."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.connection = None
    
    async def connect(self):
        """Establish connection to database."""
        raise NotImplementedError
    
    async def disconnect(self):
        """Close connection to database."""
        raise NotImplementedError
    
    async def execute(self, query: str, params: Optional[List] = None) -> Any:
        """Execute a query."""
        raise NotImplementedError
    
    async def health_check(self) -> bool:
        """Check if connection is healthy."""
        raise NotImplementedError


class PostgreSQLConnector(DatabaseConnector):
    """PostgreSQL database connector."""
    
    async def connect(self):
        """Connect to PostgreSQL database."""
        try:
            self.connection = await asyncpg.create_pool(
                host=self.config.get("host", "localhost"),
                port=self.config.get("port", 5432),
                user=self.config["user"],
                password=self.config["password"],
                database=self.config["database"],
                min_size=self.config.get("min_pool_size", 1),
                max_size=self.config.get("max_pool_size", 10),
            )
            logger.info(f"Connected to PostgreSQL: {self.config['database']}")
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from PostgreSQL."""
        if self.connection:
            await self.connection.close()
            logger.info("Disconnected from PostgreSQL")
    
    async def execute(self, query: str, params: Optional[List] = None) -> Any:
        """Execute SQL query."""
        if not self.connection:
            raise RuntimeError("Not connected to database")
        
        async with self.connection.acquire() as conn:
            if query.strip().upper().startswith("SELECT"):
                return await conn.fetch(query, *(params or []))
            else:
                return await conn.execute(query, *(params or []))
    
    async def health_check(self) -> bool:
        """Check PostgreSQL connection."""
        try:
            if not self.connection:
                return False
            async with self.connection.acquire() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False


class MongoDBConnector(DatabaseConnector):
    """MongoDB database connector."""
    
    async def connect(self):
        """Connect to MongoDB."""
        try:
            connection_string = self.config.get("connection_string")
            if not connection_string:
                host = self.config.get("host", "localhost")
                port = self.config.get("port", 27017)
                user = self.config.get("user")
                password = self.config.get("password")
                
                if user and password:
                    connection_string = f"mongodb://{user}:{password}@{host}:{port}"
                else:
                    connection_string = f"mongodb://{host}:{port}"
            
            self.connection = pymongo.MongoClient(connection_string)
            self.db = self.connection[self.config["database"]]
            
            # Test connection
            self.connection.server_info()
            logger.info(f"Connected to MongoDB: {self.config['database']}")
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from MongoDB")
    
    async def execute(self, operation: str, collection: str, **kwargs) -> Any:
        """Execute MongoDB operation."""
        if not self.connection:
            raise RuntimeError("Not connected to database")
        
        coll = self.db[collection]
        
        if operation == "find":
            return list(coll.find(kwargs.get("filter", {})))
        elif operation == "insert_one":
            return coll.insert_one(kwargs["document"])
        elif operation == "update_one":
            return coll.update_one(kwargs["filter"], kwargs["update"])
        elif operation == "delete_one":
            return coll.delete_one(kwargs["filter"])
        else:
            raise ValueError(f"Unknown operation: {operation}")
    
    async def health_check(self) -> bool:
        """Check MongoDB connection."""
        try:
            if not self.connection:
                return False
            self.connection.server_info()
            return True
        except Exception as e:
            logger.error(f"MongoDB health check failed: {e}")
            return False


def create_database_connector(db_type: str, config: Dict[str, Any]) -> DatabaseConnector:
    """Factory function to create database connector."""
    if db_type == "postgresql":
        return PostgreSQLConnector(config)
    elif db_type == "mongodb":
        return MongoDBConnector(config)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")
