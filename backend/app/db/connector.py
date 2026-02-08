"""
Database Connector - Backward Compatibility Layer

This module provides backward-compatible functions that use the new DatabaseManager
internally. It maintains the existing API for legacy code while leveraging the
improved connection management.

The DatabaseManager follows a three-tier fallback strategy:
1. PostgreSQL (Primary)
2. SQLite (Secondary fallback)
3. In-memory storage (Final fallback)

For new code, prefer using db_manager.get_db_manager() and db_manager.get_db() directly.
"""

import logging
import os
from sqlalchemy.ext.asyncio import AsyncSession

from .db_manager import get_db_manager, get_db
from .progress_sql import SQL_ECHO

logger = logging.getLogger(__name__)

# Legacy module-level variables for backward compatibility
# These are maintained for existing code that may access them directly
engine = None
AsyncSessionLocal = None
is_inmemory = False
is_sqlite = False
inmemory_db = None
sqlite_db = None


def _sync_module_state():
    """Synchronize module-level variables with DatabaseManager state."""
    global engine, AsyncSessionLocal, is_inmemory, is_sqlite, inmemory_db, sqlite_db

    manager = get_db_manager()
    engine = manager.engine
    AsyncSessionLocal = manager.session_factory
    is_inmemory = not manager.is_using_primary and not manager.is_using_sqlite
    is_sqlite = manager.is_using_sqlite
    inmemory_db = manager.inmemory_db
    sqlite_db = manager.sqlite_db


async def init_db():
    """
    Initialize database tables (backward compatibility).

    This function is maintained for backward compatibility. It ensures
    database tables are created when using PostgreSQL. SQLite tables
    are created automatically. In-memory storage doesn't require initialization.
    """
    manager = get_db_manager()

    if manager.is_using_primary and manager.engine:
        from .models import Base
        try:
            async with manager.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables initialized (PostgreSQL)")
        except Exception as e:
            logger.error(
                f"Failed to initialize database tables: {e}", exc_info=True)
            raise
    elif manager.is_using_sqlite:
        logger.info("Using SQLite database (tables auto-created)")
    else:
        logger.info("Using in-memory database (no table creation needed)")


def init_engine_from_url(url: str, echo: bool = SQL_ECHO):
    """
    Initialize database from explicit URL (backward compatibility).

    Note: This function is synchronous but triggers async initialization internally.
    For new code, prefer using DatabaseManager directly with async/await.

    Args:
        url: Database connection URL
        echo: Whether to echo SQL statements
    """
    logger.warning(
        "init_engine_from_url is deprecated. Use DatabaseManager.initialize() instead."
    )

    # Set DATABASE_URL in environment for DatabaseManager to pick up
    os.environ["DATABASE_URL"] = url

    # Re-initialize the database manager
    manager = get_db_manager()
    import asyncio
    try:
        asyncio.create_task(manager.reinitialize())
    except RuntimeError:
        # If no event loop is running, we can't initialize async
        logger.warning("Cannot initialize async engine synchronously")

    _sync_module_state()


def init_engine_from_aws_env():
    """
    Initialize database from AWS environment variables (backward compatibility).

    This function attempts to initialize the database connection using AWS_*
    environment variables. If AWS variables are not configured, it raises
    RuntimeError to maintain backward compatibility with existing error handling.

    Raises:
        RuntimeError: If AWS database environment variables are not set or
                     connection cannot be established
    """
    from .progress_sql import build_aws_database_url

    url = build_aws_database_url()
    if not url:
        raise RuntimeError("AWS database environment variables are not set")

    # Set the URL and reinitialize
    os.environ["DATABASE_URL"] = url

    manager = get_db_manager()
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, schedule the initialization
            asyncio.create_task(manager.reinitialize())
        else:
            # If no loop is running, run it synchronously
            loop.run_until_complete(manager.reinitialize())
    except RuntimeError as e:
        logger.error(f"Failed to initialize from AWS environment: {e}")
        raise RuntimeError("AWS database is not reachable from this host")

    _sync_module_state()

    if not manager.is_using_primary:
        raise RuntimeError("Failed to connect to AWS database")


def create_engine_from_url(url: str, echo: bool = SQL_ECHO):
    """
    Create engine from URL (backward compatibility).

    Args:
        url: Database connection URL
        echo: Whether to echo SQL statements

    Returns:
        tuple: (engine, sessionmaker) - legacy return format

    Note: This is a synchronous wrapper that may not work in all contexts.
    Prefer using DatabaseManager directly for new code.
    """
    logger.warning(
        "create_engine_from_url is deprecated. "
        "Use DatabaseManager for connection management."
    )

    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.orm import sessionmaker
    import ssl

    # Build connect args
    connect_args = {}
    sslroot = os.getenv("AWS_SSLROOTCERT")
    if sslroot and os.path.exists(sslroot):
        try:
            ssl_context = ssl.create_default_context(cafile=sslroot)
            ssl_context.check_hostname = True
            connect_args["ssl"] = ssl_context
        except Exception:
            pass

    # Create engine
    if connect_args:
        eng = create_async_engine(
            url, echo=echo, future=True, connect_args=connect_args)
    else:
        eng = create_async_engine(url, echo=echo, future=True)

    sess = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)

    return eng, sess


def create_engine_from_aws_env():
    """
    Create engine from AWS environment variables (backward compatibility).

    Returns:
        tuple: (engine, sessionmaker) - legacy return format

    Raises:
        RuntimeError: If AWS configuration is missing or connection fails
    """
    from .progress_sql import build_aws_database_url, validate_postgres_sync

    url = build_aws_database_url()
    if not url:
        raise RuntimeError("AWS database environment variables are not set")

    # Validate connection
    sync_url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
    if not validate_postgres_sync(sync_url):
        raise RuntimeError("AWS database is not reachable from this host")

    return create_engine_from_url(url)


# Export the main dependency function from db_manager
# This is the primary function that should be used with FastAPI Depends()
__all__ = [
    'get_db',
    'init_db',
    'init_engine_from_url',
    'init_engine_from_aws_env',
    'create_engine_from_url',
    'create_engine_from_aws_env',
    'engine',
    'AsyncSessionLocal',
    'is_inmemory',
    'is_sqlite',
    'inmemory_db',
    'sqlite_db',
]


# Initialize module state on import
_sync_module_state()
