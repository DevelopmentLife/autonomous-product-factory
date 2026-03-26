"""Async SQLAlchemy engine and session management."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, StaticPool

from .models import Base


def create_engine(database_url: str, **kwargs) -> AsyncEngine:
    """Create an async SQLAlchemy engine.

    Handles both ``sqlite+aiosqlite`` (for tests / local dev) and
    ``postgresql+asyncpg`` (for production).  Extra keyword arguments are
    forwarded to :func:`create_async_engine`, allowing callers to customise
    pool settings etc.

    SQLite-specific notes
    ---------------------
    * ``check_same_thread=False`` is required by aiosqlite.
    * In-memory databases (``:///:memory:``) use :class:`StaticPool` so that
      all connections share a single underlying connection — without this the
      schema created by one connection is invisible to others.
    * File-based SQLite databases use :class:`NullPool` to avoid issues with
      multi-process use.
    """
    connect_args: dict = kwargs.pop("connect_args", {})

    if database_url.startswith("sqlite"):
        connect_args.setdefault("check_same_thread", False)
        if ":memory:" in database_url:
            kwargs.setdefault(
                "poolclass", StaticPool
            )
        else:
            kwargs.setdefault("poolclass", NullPool)

    return create_async_engine(
        database_url,
        connect_args=connect_args,
        **kwargs,
    )


async def init_db(engine: AsyncEngine) -> None:
    """Create all tables defined in the ORM metadata.

    Safe to call multiple times; ``CREATE TABLE IF NOT EXISTS`` semantics are
    used by SQLAlchemy under the hood.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_db(engine: AsyncEngine) -> None:
    """Drop all tables — intended for tests only."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


def _make_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


@asynccontextmanager
async def get_session(engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """Async context manager that yields a database session.

    Usage::

        async with get_session(engine) as session:
            session.add(obj)
            await session.commit()

    The session is automatically closed when the context exits.  On
    exception the transaction is rolled back before the session is closed.
    """
    factory = _make_session_factory(engine)
    async with factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
