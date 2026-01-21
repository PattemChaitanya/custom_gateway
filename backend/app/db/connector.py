from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .progress_sql import DATABASE_URL, SQL_ECHO
from typing import AsyncGenerator

async def init_db():
    # import here to avoid circular imports
    from .models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

engine = create_async_engine(DATABASE_URL, echo=SQL_ECHO, future=True)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
