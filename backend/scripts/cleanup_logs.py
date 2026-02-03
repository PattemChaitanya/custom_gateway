"""Cleanup script for old logs and metrics (30-day retention)."""

import asyncio
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.connector import get_db_manager
from app.logging.cleanup import cleanup_old_logs, get_log_statistics
from app.logging_config import configure_logging, get_logger

configure_logging(level="INFO")
logger = get_logger("cleanup_script")


async def main():
    """Main cleanup function."""
    logger.info("Starting log cleanup process...")
    
    # Initialize database
    db_manager = get_db_manager()
    await db_manager.initialize(echo_sql=False)
    
    try:
        # Get session
        async for session in db_manager.get_session():
            # Get statistics before cleanup
            logger.info("Getting log statistics before cleanup...")
            stats_before = await get_log_statistics(session)
            logger.info(f"Before cleanup: {stats_before}")
            
            # Perform cleanup (default 30 days)
            retention_days = int(os.getenv("LOG_RETENTION_DAYS", "30"))
            logger.info(f"Cleaning up logs older than {retention_days} days...")
            result = await cleanup_old_logs(session, retention_days=retention_days)
            logger.info(f"Cleanup result: {result}")
            
            # Get statistics after cleanup
            stats_after = await get_log_statistics(session)
            logger.info(f"After cleanup: {stats_after}")
            
            # Summary
            logger.info(
                f"Cleanup summary: Deleted {result['audit_logs_deleted']} audit logs "
                f"and {result['metrics_deleted']} metrics"
            )
            
            break
    
    finally:
        await db_manager.close()
        logger.info("Database connections closed")


if __name__ == "__main__":
    asyncio.run(main())
