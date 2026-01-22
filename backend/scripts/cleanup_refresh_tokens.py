"""Simple maintenance script to remove expired or revoked refresh tokens.

Run with the same environment as the app (DATABASE_URL set).
"""
import asyncio
import os
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.models import RefreshToken, Base


DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./dev.db")


async def cleanup():
    engine = create_async_engine(DATABASE_URL, future=True)
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with AsyncSessionLocal() as session:
        now = datetime.now(timezone.utc)
        q = await session.execute(
            "DELETE FROM refresh_tokens WHERE revoked = 1 OR expires_at < :now RETURNING id",
            {"now": now},
        )
        # SQL-returning engines may differ across backends; using raw SQL for simplicity
        await session.commit()
        print("Cleanup complete")


if __name__ == "__main__":
    asyncio.run(cleanup())
