"""Database handler for centralized logging."""

import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import os


class DatabaseLogHandler(logging.Handler):
    """Custom logging handler that stores logs in database.

    The engine/session are created lazily (on first real DB write) so
    that importing or attaching this handler has near-zero cost.  The
    current ``emit`` implementation only prints to the console, so the
    engine is never actually created unless a subclass overrides
    ``emit`` and calls ``_ensure_db()``.
    """

    def __init__(self, level=logging.INFO):
        super().__init__(level)
        self.engine = None
        self.SessionLocal = None

    def _ensure_db(self):
        """Lazily initialize the database connection on first use."""
        if self.engine is not None:
            return

        database_url = os.getenv(
            "DATABASE_URL", "sqlite+aiosqlite:///./gateway.db")
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1)

        self.engine = create_async_engine(
            database_url, echo=False, pool_pre_ping=True)
        self.SessionLocal = sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

    def emit(self, record: logging.LogRecord):
        """Emit a log record to the database."""
        # Skip async operations in sync context - just format the message
        # In production, use a queue-based approach for async logging
        try:
            log_entry = self.format(record)
            # For now, just print to console - full DB logging requires async context
            print(f"[DB_LOG] {log_entry}")
        except Exception:
            self.handleError(record)
