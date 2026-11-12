"""Async database session factory for the platform.

Creates an async SQLAlchemy engine with a proper connection pool and a
sessionmaker from the platform ``DATABASE_URL`` setting. All persistence goes
through this factory so the API, workers, and scripts share one connection
configuration.

Pool settings (PRODUCTION_STANDARDS.md §8):
- pool_size=20, max_overflow=10 for production workloads
- pool_pre_ping=True to detect stale connections
- pool_recycle=3600 to avoid MySQL/PostgreSQL idle timeouts
- Falls back to SQLite for dev/test when DATABASE_URL is sqlite://
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


def _pool_kwargs(settings: Any) -> dict[str, Any]:
    """Return pool configuration based on environment and database type."""
    url = settings.database_url
    if url.startswith("sqlite"):
        from sqlalchemy.pool import NullPool

        return {"poolclass": NullPool}
    kwargs: dict[str, Any] = {
        "pool_size": 20,
        "max_overflow": 10,
        "pool_pre_ping": True,
        "pool_recycle": 3600,
    }
    return kwargs


def _normalize_url(url: str) -> str:
    """Convert sync sqlite URL to async (aiosqlite) for the async engine."""
    if url.startswith("sqlite:///") and "+aiosqlite" not in url:
        return url.replace("sqlite:///", "sqlite+aiosqlite:///")
    if url.startswith("sqlite://") and "+aiosqlite" not in url:
        return url.replace("sqlite://", "sqlite+aiosqlite://")
    return url


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()
        _engine = create_async_engine(
            _normalize_url(settings.database_url),
            echo=False,
            future=True,
            **_pool_kwargs(settings),
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            expire_on_commit=False,
            autoflush=True,
        )
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
