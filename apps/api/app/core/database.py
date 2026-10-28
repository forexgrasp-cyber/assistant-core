"""
Database connection and session management.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from .config import get_settings

settings = get_settings()

# Create async engine (pool args only valid with pooled engines, not NullPool)
engine_kwargs = {
    "pool_pre_ping": True,
    "echo": settings.database.echo,
}
if not settings.is_development():
    engine_kwargs.update({
        "pool_size": settings.database.pool_size,
        "max_overflow": settings.database.max_overflow,
    })
engine = create_async_engine(settings.database.url, **engine_kwargs)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Initialize database (create tables if using dev/create_all mode)."""
    from ..models import Base as ModelsBase

    async with engine.begin() as conn:
        await conn.run_sync(ModelsBase.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get a database session with auto-commit/rollback."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session."""
    async with async_session_maker() as session:
        yield session


def get_sync_engine():
    """Get synchronous engine for migrations and Celery tasks."""
    sync_url = settings.database.sync_url or settings.database.url.replace(
        "postgresql+asyncpg://", "postgresql+psycopg2://"
    )
    return create_engine(sync_url, poolclass=NullPool, echo=False)