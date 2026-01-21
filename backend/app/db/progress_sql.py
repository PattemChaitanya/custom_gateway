import os

# Database URL. Prefer setting DATABASE_URL in environment for production, e.g.
# postgresql+asyncpg://user:password@host:port/dbname
# Default to a local SQLite async DB for development/testing to avoid requiring
# an external Postgres instance.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./dev.db",
)

# SQLAlchemy echo flag
SQL_ECHO = os.getenv("SQL_ECHO", "False").lower() in ("1", "true", "yes")
