from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .progress_sql import DATABASE_URL, SQL_ECHO, build_aws_database_url
from .inmemory import InMemoryDB
import typing as t


async def init_db():
    # import here to avoid circular imports
    from .models import Base
    # Only run create_all when using an actual SQL engine
    if not is_inmemory:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)


# Global flags and objects. If DATABASE_URL is None, we'll use the in-memory
# fallback to avoid requiring a local sqlite file here.
is_inmemory = DATABASE_URL is None
inmemory_db: InMemoryDB | None = InMemoryDB() if is_inmemory else None

# Module-level engine and sessionmaker used by the application when a DB URL is
# present.
if not is_inmemory:
    engine = create_async_engine(DATABASE_URL, echo=SQL_ECHO, future=True)

    AsyncSessionLocal = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
else:
    engine = None
    AsyncSessionLocal = None


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
    global engine, AsyncSessionLocal, is_inmemory, inmemory_db
    is_inmemory = False
    inmemory_db = None
    engine, AsyncSessionLocal = create_engine_from_url(url, echo=echo)


def init_engine_from_aws_env():
    """Initialize module-level engine and AsyncSessionLocal from AWS env vars.

    Raises RuntimeError if AWS env vars are not present.
    """
    global engine, AsyncSessionLocal, is_inmemory, inmemory_db
    eng, sess = create_engine_from_aws_env()
    engine = eng
    AsyncSessionLocal = sess
    is_inmemory = False
    inmemory_db = None


async def get_db():
    """Yield either an AsyncSession (when using SQL) or an InMemoryDB instance.

    The router and CRUD layers should accept either and branch accordingly.
    """
    if is_inmemory:
        # In-memory DB object used directly by CRUD functions
        yield inmemory_db
    else:
        async with AsyncSessionLocal() as session:
            yield session
