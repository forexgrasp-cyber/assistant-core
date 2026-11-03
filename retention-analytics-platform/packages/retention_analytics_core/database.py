"""Async database session factory for the platform.

Creates an async SQLAlchemy engine and sessionmaker from the platform
``DATABASE_URL`` setting. All persistence goes through this factory so the
API, workers, and scripts share one connection configuration.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from retention_analytics_shared_config import get_settings
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(settings.database_url, echo=False, future=True)
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session (for FastAPI dependency injection)."""
    async with get_session_factory()() as session:
        yield session


async def init_db() -> None:
    """Create all tables (dev convenience; use Alembic migrations in prod)."""
    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


__all__ = ["Base", "get_engine", "get_session_factory", "get_session", "init_db"]
