"""
Database migration helper script

This script updates the database to fix any NULL values in user boolean fields.
Run this from the backend directory:
    python scripts/fix_user_booleans.py
"""

from sqlalchemy import text
from app.db.connector import get_db_manager
import asyncio
import sys
import os

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def fix_user_booleans():
    """Update any NULL boolean values in users table to proper defaults."""
    from app.db.connector import get_db

    # Get a database session
    async for session in get_db():
        try:
            # Update is_active NULL values to TRUE
            await session.execute(
                text("UPDATE users SET is_active = TRUE WHERE is_active IS NULL")
            )

            # Update is_superuser NULL values to FALSE
            await session.execute(
                text("UPDATE users SET is_superuser = FALSE WHERE is_superuser IS NULL")
            )

            await session.commit()
            print("✓ Fixed NULL boolean values in users table")
            break  # Only need one iteration
        except Exception as e:
            print(f"Error: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(fix_user_booleans())
    print("✓ Database migration complete!")
