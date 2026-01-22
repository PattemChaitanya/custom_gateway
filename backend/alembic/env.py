import asyncio
import sys
from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import context

config = context.config

# ensure project root is on sys.path so imports like `app.db.models` work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# add your model's MetaData object here for 'autogenerate' support
from app.db.models import Base  # noqa: E402

target_metadata = Base.metadata

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    # support alembic config using 'env: VAR' to reference environment variables
    if url and url.strip().lower().startswith("env:"):
        env_key = url.split(':', 1)[1].strip()
        url = os.environ.get(env_key)
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    # pull config section and resolve any 'env: VAR' placeholders to actual values
    cfg = config.get_section(config.config_ini_section).copy()
    url_val = cfg.get("sqlalchemy.url")
    if url_val and str(url_val).strip().lower().startswith("env:"):
        env_key = str(url_val).split(':', 1)[1].strip()
        cfg["sqlalchemy.url"] = os.environ.get(env_key)

    connectable = AsyncEngine(
        engine_from_config(
            cfg,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async def run():
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)

    asyncio.run(run())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
