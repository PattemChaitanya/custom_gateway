"""
Database Package

Provides database connection management with automatic fallback from PostgreSQL
to in-memory storage.

Recommended usage for new code:
    from app.db.db_manager import get_db_manager, get_db
    from app.db import models
    
For backward compatibility, legacy connector functions are also available:
    from app.db.connector import get_db, init_db, init_engine_from_aws_env
"""

# Core database manager (preferred for new code)
from .db_manager import (
    DatabaseManager,
    get_db_manager,
    get_db,
    DatabaseConnectionError,
)

# Database models
from . import models

# Legacy connector functions (backward compatibility)
from .connector import (
    init_db,
    init_engine_from_url,
    init_engine_from_aws_env,
    create_engine_from_url,
    create_engine_from_aws_env,
)

# In-memory database
from .inmemory import InMemoryDB

# Utility functions
from .progress_sql import (
    build_aws_database_url,
    get_database_url_from_env,
    is_postgres_url,
    SQL_ECHO,
    DATABASE_URL,
)

__all__ = [
    # Core exports (preferred)
    'DatabaseManager',
    'get_db_manager',
    'get_db',
    'DatabaseConnectionError',
    'models',
    'InMemoryDB',
    
    # Legacy exports (backward compatibility)
    'init_db',
    'init_engine_from_url',
    'init_engine_from_aws_env',
    'create_engine_from_url',
    'create_engine_from_aws_env',
    
    # Utilities
    'build_aws_database_url',
    'get_database_url_from_env',
    'is_postgres_url',
    'SQL_ECHO',
    'DATABASE_URL',
]