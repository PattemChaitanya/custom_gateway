from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .progress_sql import DATABASE_URL, SQL_ECHO, build_aws_database_url
import typing as t


async def init_db():
    # import here to avoid circular imports
    from .models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


# Module-level engine and sessionmaker used by the application. These are
# initialized from DATABASE_URL on import to preserve existing behavior.
engine = create_async_engine(DATABASE_URL, echo=SQL_ECHO, future=True)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


def create_engine_from_url(url: str, echo: bool = SQL_ECHO):
    """Create and return an async SQLAlchemy engine for the given URL.

    Returns: (engine, sessionmaker)
    """
    eng = create_async_engine(url, echo=echo, future=True)
    sess = sessionmaker(eng, class_=AsyncSession, expire_on_commit=False)
    return eng, sess


def create_engine_from_aws_env():
    """Build a DB URL from AWS_* env vars and return (engine, sessionmaker).

    Raises RuntimeError if required AWS env vars are missing.
    """
    url = build_aws_database_url()
    if not url:
        raise RuntimeError("AWS database environment variables are not set")
    return create_engine_from_url(url)


def init_engine_from_url(url: str, echo: bool = SQL_ECHO):
    """Initialize module-level engine and AsyncSessionLocal from an explicit URL."""
    global engine, AsyncSessionLocal
    engine, AsyncSessionLocal = create_engine_from_url(url, echo=echo)


def init_engine_from_aws_env():
    """Initialize module-level engine and AsyncSessionLocal from AWS env vars.

    Raises RuntimeError if AWS env vars are not present.
    """
    global engine, AsyncSessionLocal
    eng, sess = create_engine_from_aws_env()
    engine = eng
    AsyncSessionLocal = sess


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
