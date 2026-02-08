"""
Database Connection Manager with Primary/Fallback Strategy

This module implements a robust database connection manager that follows the priority:
1. AWS PostgreSQL (Primary)
2. SQLite (Secondary Fallback)
3. In-memory storage (Final Fallback)

The manager handles connection health checks, automatic fallback, and graceful degradation.
"""

import asyncio
import logging
import os
from typing import Optional, Union, AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from .progress_sql import (
    build_aws_database_url,
    get_database_url_from_env,
    validate_postgres_connection,
)
from .inmemory import InMemoryDB
from .sqlite_db import SQLiteDB
from .models import Base

logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """Raised when database connection cannot be established."""
    pass


class DatabaseManager:
    """
    Manages database connections with automatic fallback from PostgreSQL to SQLite to in-memory storage.

    This singleton class ensures only one instance manages the database connections throughout
    the application lifecycle. It attempts to connect to AWS PostgreSQL first, falls back to
    SQLite if PostgreSQL fails, and finally to in-memory storage if both fail.

    Attributes:
        engine: SQLAlchemy async engine for PostgreSQL connections
        session_factory: Factory for creating AsyncSession instances
        sqlite_db: SQLite database instance used as secondary fallback
        inmemory_db: In-memory database instance used as final fallback
        is_using_primary: Flag indicating whether primary database is active
        is_using_sqlite: Flag indicating whether SQLite fallback is active
    """

    _instance: Optional['DatabaseManager'] = None
    _initialized: bool = False

    def __new__(cls):
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize database manager (only once)."""
        if self._initialized:
            return

        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[sessionmaker] = None
        self.sqlite_db: Optional[SQLiteDB] = None
        self.inmemory_db: Optional[InMemoryDB] = None
        self.is_using_primary: bool = False
        self.is_using_sqlite: bool = False
        self._connection_url: Optional[str] = None
        self._echo_sql: bool = False
        self._sqlite_path: str = os.getenv("SQLITE_DB_PATH", "gateway.db")

        self._initialized = True
        logger.info("DatabaseManager initialized")

    async def initialize(self, echo_sql: bool = False, timeout: int = 15) -> None:
        """
        Initialize database connections following the priority strategy.

        Attempts to connect to AWS PostgreSQL first. If that fails, tries SQLite.
        If SQLite also fails, falls back to in-memory storage. This method is
        idempotent and can be called multiple times safely.

        Args:
            echo_sql: Whether to echo SQL statements (useful for debugging)
            timeout: Total timeout for initialization in seconds (default: 15)
        """
        self._echo_sql = echo_sql

        try:
            # Wrap entire initialization in timeout to prevent hanging
            await asyncio.wait_for(
                self._try_initialize_databases(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"Database initialization timed out after {timeout}s, "
                "falling back to in-memory storage"
            )
            self._initialize_fallback_database()
        except Exception as e:
            logger.error(f"Database initialization error: {e}", exc_info=True)
            self._initialize_fallback_database()

    async def _try_initialize_databases(self) -> None:
        """
        Try to initialize databases in order: PostgreSQL -> SQLite -> In-memory.
        This is a separate method to allow timeout wrapping.
        """
        # Try to connect to primary database (AWS PostgreSQL)
        if await self._initialize_primary_database():
            logger.info(
                "Successfully connected to primary database (PostgreSQL)")
            return

        # Try SQLite as secondary fallback
        if await self._initialize_sqlite_database():
            logger.info("Connected to secondary fallback database (SQLite)")
            return

        # Fallback to in-memory database as final option
        logger.warning(
            "Primary and secondary database connections failed or not configured. "
            "Falling back to in-memory storage."
        )
        self._initialize_fallback_database()

    async def _initialize_primary_database(self) -> bool:
        """
        Attempt to initialize connection to AWS PostgreSQL database.

        Returns:
            bool: True if successfully connected, False otherwise
        """
        try:
            # Try to get AWS database URL
            database_url = build_aws_database_url()

            # If no AWS configuration, try DATABASE_URL from environment
            if not database_url:
                database_url = get_database_url_from_env()

            if not database_url:
                logger.info("No database URL configured")
                return False

            # Validate connection before creating engine (with reduced timeout)
            if not await validate_postgres_connection(database_url, timeout=3):
                logger.warning("PostgreSQL connection validation failed")
                return False

            # Ensure asyncpg dialect
            if not database_url.startswith("postgresql+asyncpg://"):
                database_url = database_url.replace(
                    "postgresql://", "postgresql+asyncpg://", 1
                )

            # Create engine with connection pooling
            self.engine = create_async_engine(
                database_url,
                echo=self._echo_sql,
                future=True,
                pool_pre_ping=True,  # Verify connections before using them
                pool_size=5,  # Number of connections to maintain
                max_overflow=10,  # Maximum overflow connections
                pool_recycle=3600,  # Recycle connections after 1 hour
                connect_args=self._get_connect_args(),
            )

            # Test the connection
            if not await self._test_connection():
                logger.error("Database connection test failed")
                await self._cleanup_engine()
                return False

            # Create session factory
            self.session_factory = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            # Create tables if they don't exist
            await self._create_tables()

            self.is_using_primary = True
            self._connection_url = database_url
            logger.info("Primary database initialized successfully")
            return True

        except Exception as e:
            logger.error(
                f"Failed to initialize primary database: {e}", exc_info=True)
            await self._cleanup_engine()
            return False

    async def _initialize_sqlite_database(self) -> bool:
        """
        Attempt to initialize connection to SQLite database.

        Returns:
            bool: True if successfully connected, False otherwise
        """
        try:
            # Add timeout for SQLite initialization to prevent hanging
            async def _init_sqlite():
                self.sqlite_db = SQLiteDB(db_path=self._sqlite_path)
                await self.sqlite_db.connect()
                self.is_using_sqlite = True
                self.is_using_primary = False
                logger.info(
                    f"SQLite database initialized successfully at: {self._sqlite_path}")

            await asyncio.wait_for(_init_sqlite(), timeout=10.0)
            return True

        except asyncio.TimeoutError:
            logger.warning("SQLite initialization timed out after 10s")
            if self.sqlite_db:
                try:
                    await self.sqlite_db.disconnect()
                except:
                    pass
                self.sqlite_db = None
            self.is_using_sqlite = False
            return False
        except Exception as e:
            logger.warning(f"Failed to initialize SQLite database: {e}")
            if self.sqlite_db:
                try:
                    await self.sqlite_db.disconnect()
                except:
                    pass
                self.sqlite_db = None
            self.is_using_sqlite = False
            return False

    def _initialize_fallback_database(self) -> None:
        """Initialize in-memory database as final fallback."""
        try:
            self.inmemory_db = InMemoryDB()
            self.is_using_primary = False
            self.is_using_sqlite = False
            logger.info("In-memory database initialized as final fallback")
        except Exception as e:
            logger.error(
                f"Failed to initialize fallback database: {e}", exc_info=True)
            raise DatabaseConnectionError(
                "Could not initialize any database (primary, secondary, or fallback)"
            )

    def _get_connect_args(self) -> dict:
        """
        Get connection arguments including SSL configuration for AWS.

        Returns:
            dict: Connection arguments for SQLAlchemy engine
        """
        import os
        import ssl

        connect_args = {}
        # Support both AWS_SSLROOTCERT and AWS_DB_SSL_FILE_PATH
        sslroot = os.getenv("AWS_SSLROOTCERT") or os.getenv(
            "AWS_DB_SSL_FILE_PATH")

        if sslroot and os.path.exists(sslroot):
            try:
                ssl_context = ssl.create_default_context(cafile=sslroot)
                ssl_context.check_hostname = True
                connect_args["ssl"] = ssl_context
                logger.debug(
                    f"SSL configured with root certificate: {sslroot}")
            except Exception as e:
                logger.warning(f"Failed to configure SSL: {e}")

        return connect_args

    async def _test_connection(self) -> bool:
        """
        Test database connection by executing a simple query.

        Returns:
            bool: True if connection test succeeds
        """
        if not self.engine:
            return False

        try:
            async with self.engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    async def _create_tables(self) -> None:
        """Create database tables if they don't exist."""
        if not self.engine:
            return

        try:
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}", exc_info=True)
            raise

    async def _cleanup_engine(self) -> None:
        """Cleanup database engine and connections."""
        if self.engine:
            try:
                await self.engine.dispose()
            except Exception as e:
                logger.error(f"Error disposing engine: {e}")
            finally:
                self.engine = None
                self.session_factory = None

    async def health_check(self) -> dict:
        """
        Perform health check on the database connection.

        Returns:
            dict: Health status information
        """
        if self.is_using_primary:
            try:
                if await self._test_connection():
                    return {
                        "status": "healthy",
                        "database": "postgresql",
                        "message": "Primary database connection is healthy"
                    }
                else:
                    return {
                        "status": "degraded",
                        "database": "postgresql",
                        "message": "Primary database connection failed health check"
                    }
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "database": "postgresql",
                    "message": f"Health check error: {str(e)}"
                }
        elif self.is_using_sqlite:
            try:
                # Basic check if SQLite is accessible
                if self.sqlite_db and self.sqlite_db._db:
                    return {
                        "status": "healthy",
                        "database": "sqlite",
                        "message": "Using SQLite secondary fallback storage"
                    }
                else:
                    return {
                        "status": "degraded",
                        "database": "sqlite",
                        "message": "SQLite database not properly connected"
                    }
            except Exception as e:
                return {
                    "status": "unhealthy",
                    "database": "sqlite",
                    "message": f"SQLite health check error: {str(e)}"
                }
        else:
            return {
                "status": "degraded",
                "database": "in-memory",
                "message": "Using final fallback in-memory storage"
            }

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[Union[AsyncSession, SQLiteDB, InMemoryDB], None]:
        """
        Get a database session (PostgreSQL, SQLite, or in-memory).

        This is the main method to use for getting database access. It returns
        either an AsyncSession for PostgreSQL, a SQLiteDB instance, or an InMemoryDB instance.

        Yields:
            AsyncSession | SQLiteDB | InMemoryDB: Database session

        Example:
            async with db_manager.get_session() as session:
                # Use session for database operations
                result = await crud.list_apis(session)
        """
        if self.is_using_primary and self.session_factory:
            # Return PostgreSQL session
            async with self.session_factory() as session:
                try:
                    yield session
                except Exception as e:
                    logger.error(f"Session error: {e}", exc_info=True)
                    await session.rollback()
                    raise
        elif self.is_using_sqlite:
            # Return SQLite database
            if not self.sqlite_db:
                await self._initialize_sqlite_database()
            yield self.sqlite_db
        else:
            # Return in-memory database
            if not self.inmemory_db:
                self._initialize_fallback_database()
            yield self.inmemory_db

    async def shutdown(self) -> None:
        """
        Gracefully shutdown database connections.

        This should be called during application shutdown to clean up resources.
        """
        logger.info("Shutting down database manager")

        if self.engine:
            await self._cleanup_engine()

        if self.sqlite_db:
            try:
                await self.sqlite_db.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting SQLite: {e}")
            finally:
                self.sqlite_db = None

        if self.inmemory_db:
            self.inmemory_db = None

        self.is_using_primary = False
        self.is_using_sqlite = False
        logger.info("Database manager shut down successfully")

    async def reinitialize(self, force_fallback: bool = False) -> None:
        """
        Reinitialize database connections.

        Useful for reconnecting after a connection failure or configuration change.

        Args:
            force_fallback: If True, skip primary and use fallback directly
        """
        logger.info("Reinitializing database connections")
        await self.shutdown()

        if force_fallback:
            self._initialize_fallback_database()
        else:
            await self.initialize(echo_sql=self._echo_sql)

    def get_connection_info(self) -> dict:
        """
        Get information about current database connection.

        Returns:
            dict: Connection information
        """
        db_type = "postgresql" if self.is_using_primary else (
            "sqlite" if self.is_using_sqlite else "in-memory")
        return {
            "is_using_primary": self.is_using_primary,
            "is_using_sqlite": self.is_using_sqlite,
            "database_type": db_type,
            "has_engine": self.engine is not None,
            "has_session_factory": self.session_factory is not None,
            "has_sqlite_db": self.sqlite_db is not None,
            "has_inmemory_db": self.inmemory_db is not None,
            "sqlite_path": self._sqlite_path if self.is_using_sqlite else None,
        }


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """
    Get the global database manager instance.

    Returns:
        DatabaseManager: The singleton database manager instance
    """
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager


async def get_db() -> AsyncGenerator[Union[AsyncSession, SQLiteDB, InMemoryDB], None]:
    """
    Dependency function for FastAPI to inject database sessions.

    This is the function to use with FastAPI's Depends() for endpoints.

    Yields:
        AsyncSession | SQLiteDB | InMemoryDB: Database session

    Example:
        @app.get("/apis")
        async def list_apis(db: AsyncSession = Depends(get_db)):
            return await crud.list_apis(db)
    """
    manager = get_db_manager()
    async with manager.get_session() as session:
        yield session
