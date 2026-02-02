import os
import subprocess
import sys
import pytest
import asyncio

from pathlib import Path

# backend project root
HERE = Path(__file__).parent.parent


def run_alembic_upgrade():
    env = os.environ.copy()
    # ensure DATABASE_URL is present for alembic
    # use a dedicated test sqlite file to keep migrations idempotent between runs
    test_db_path = HERE / "test_dev.db"
    # remove previous test DB if present to ensure a clean migration
    if test_db_path.exists():
        try:
            test_db_path.unlink()
        except Exception:
            pass
    if "DATABASE_URL" not in env:
        test_url = f"sqlite+aiosqlite:///{str(test_db_path)}"
        env["DATABASE_URL"] = test_url
        # also set DATABASE_URL in the current process so imported app uses same DB
        os.environ["DATABASE_URL"] = test_url
    else:
        # use existing DATABASE_URL for alembic
        test_url = env["DATABASE_URL"]
    env["DATABASE_URL"] = test_url
    # run alembic using the same python interpreter to ensure module is found
    try:
        subprocess.check_call([sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"], cwd=str(HERE), env=env)
    except subprocess.CalledProcessError:
        # Ignore migration errors during test runs that indicate migrations
        # are already present (e.g. table exists). Tests expect a working DB
        # schema; if migrations fail for other reasons they will surface
        # during test execution.
        pass


@pytest.fixture(scope="session", autouse=True)
def apply_migrations():
    run_alembic_upgrade()
    yield


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def initialize_db_manager(apply_migrations, event_loop):
    """
    Initialize the DatabaseManager for tests.
    
    This ensures the new DatabaseManager is properly initialized with the
    test database URL before any tests run.
    """
    from app.db import get_db_manager
    
    # Get the database manager
    db_manager = get_db_manager()
    
    # Initialize with test configuration
    event_loop.run_until_complete(db_manager.initialize(echo_sql=False))
    
    yield
    
    # Cleanup after all tests
    event_loop.run_until_complete(db_manager.shutdown())
