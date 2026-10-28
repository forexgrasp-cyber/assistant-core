from logging.config import fileConfig
import sys
import os
from pathlib import Path

# Add the project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from sqlalchemy import engine_from_config, pool
from alembic import context

# Import models to register them
from apps.api.app.models import Base

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

# Get database URL from environment or settings
def get_database_url():
    # For migrations, we need a SYNC database URL (not async)
    # Try to get from shared_config first
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "shared-canonical-services"))
        from shared_config import get_settings
        settings = get_settings()
        url = settings.database.url
        # Convert async URL to sync for migrations
        if url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        return url
    except ImportError:
        pass
    
    # Fallback to environment variable
    url = os.getenv("DATABASE_URL")
    if url:
        if url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
        return url
    
    # Default fallback - use SQLite for migration generation (no DB needed)
    # This works for autogenerate since we just need a DB to compare against
    return "sqlite:///alembic_migration.db"

# Set the URL in the config BEFORE creating the engine
config.set_main_option("sqlalchemy.url", get_database_url())

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
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


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # For SQLite, we need to use a file-based database
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_schemas=True,
            # SQLite doesn't support all PostgreSQL features, so we skip some comparisons
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()