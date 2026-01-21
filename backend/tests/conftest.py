import os
import subprocess
import sys
import pytest

from pathlib import Path

# backend project root
HERE = Path(__file__).parent.parent


def run_alembic_upgrade():
    env = os.environ.copy()
    # ensure DATABASE_URL is present for alembic
    if "DATABASE_URL" not in env:
        # use a dedicated test sqlite file to keep migrations idempotent between runs
        test_db_path = HERE / "test_dev.db"
        # remove previous test DB if present to ensure a clean migration
        if test_db_path.exists():
            try:
                test_db_path.unlink()
            except Exception:
                pass
        env["DATABASE_URL"] = f"sqlite+aiosqlite:///{str(test_db_path)}"
    # run alembic using the same python interpreter to ensure module is found
    subprocess.check_call([sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"], cwd=str(HERE), env=env)


@pytest.fixture(scope="session", autouse=True)
def apply_migrations():
    run_alembic_upgrade()
    yield
