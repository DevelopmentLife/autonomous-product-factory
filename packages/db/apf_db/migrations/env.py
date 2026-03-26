"""Alembic environment configuration with async SQLAlchemy support."""

from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

# ---------------------------------------------------------------------------
# Alembic Config object — provides access to values in alembic.ini
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Import the ORM metadata so Alembic can diff the schema
# ---------------------------------------------------------------------------
# Allow the DATABASE_URL env var to override the ini value at runtime.
from apf_db.models import Base  # noqa: E402

target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_url() -> str:
    """Return the database URL, preferring the DATABASE_URL env var."""
    return os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url", "")


# ---------------------------------------------------------------------------
# Offline migrations  (no live DB connection needed)
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Emit SQL to stdout / a file without connecting to the database.

    Useful for generating migration scripts for review or manual application.
    """
    url = _get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migrations  (async)
# ---------------------------------------------------------------------------


def do_run_migrations(connection: Connection) -> None:
    """Synchronous callback executed inside the async engine's run_sync."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create the async engine and drive migrations through it."""
    url = _get_url()

    # Use NullPool so that migration connections are not pooled — important
    # for single-use migration runs.
    connectable = create_async_engine(url, poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online (connected) migrations."""
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Main dispatch
# ---------------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
