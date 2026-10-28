"""
Demo Tenant Management Service for Retention Analytics Platform.

This service integrates the shared demo tenant management utilities
with the platform's database and authentication.
"""

from __future__ import annotations

from typing import Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from shared.demo.tenant_manager import (
    DemoTenantManager,
    DemoSessionManager,
    DemoSnapshotManager,
    TenantConfig,
    SessionConfig,
    DemoMode,
    SnapshotType,
    DemoTenantStatus,
    DemoSessionStatus,
    create_demo_engine,
    create_demo_session_factory,
    init_demo_database,
    get_demo_tenant_manager,
    get_demo_session_manager,
    get_demo_snapshot_manager,
    DEFAULT_SCENARIOS,
)
from shared.db_paths import DB_WORKFLOW_SAAS

from ..core.config import get_settings

settings = get_settings()

# Global instances (initialized on startup)
_demo_engine = None
_demo_session_factory = None
_demo_tenant_manager: Optional[DemoTenantManager] = None
_demo_session_manager: Optional[DemoSessionManager] = None
_demo_snapshot_manager: Optional[DemoSnapshotManager] = None


async def init_demo_services():
    """Initialize demo services on application startup."""
    global _demo_engine, _demo_session_factory, _demo_tenant_manager, _demo_session_manager, _demo_snapshot_manager
    
    # Use the main workflow database for demo data
    # In production, you might want a separate demo database
    demo_db_url = settings.database_url.replace("workflow_saas", "demo_tenant") if "workflow_saas" in settings.database_url else settings.database_url
    
    _demo_engine = create_async_engine(demo_db_url)
    _demo_session_factory = create_demo_session_factory(_demo_engine)
    
    # Initialize database tables
    await init_demo_database(_demo_engine)
    
    # Initialize managers
    _demo_tenant_manager = DemoTenantManager(_demo_session_factory)
    _demo_session_manager = DemoSessionManager(_demo_session_factory)
    _demo_snapshot_manager = DemoSnapshotManager(_demo_session_factory)
    
    # Create default demo tenant if it doesn't exist
    await _ensure_default_tenant()
    
    # Load default scenarios into database
    await _load_default_scenarios()
    
    print("Demo services initialized")


async def _ensure_default_tenant():
    """Ensure a default demo tenant exists."""
    try:
        existing = await _demo_tenant_manager.get_tenant("demo-default")
        if not existing:
            config = TenantConfig(
                id="demo-default",
                name="Demo Workspace",
                description="Default demo workspace with sample data",
                mode=DemoMode.INTERACTIVE,
                reset_interval_minutes=60,
                max_session_minutes=30,
                allowed_features=["workflows", "reports", "analytics", "llm", "engagement"],
                readonly=False,
            )
            await _demo_tenant_manager.create_tenant(config)
            print("Created default demo tenant")
    except Exception as e:
        print(f"Warning: Could not create default demo tenant: {e}")


async def _load_default_scenarios():
    """Load default scenarios into the database."""
    try:
        async with _demo_session_factory() as session:
            from shared.demo.tenant_manager import DemoScenario
            
            for scenario in DEFAULT_SCENARIOS:
                # Check if scenario already exists
                result = await session.execute(
                    select(DemoScenario).where(DemoScenario.key == scenario.key)
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    db_scenario = DemoScenario(
                        key=scenario.key,
                        name=scenario.name,
                        description=scenario.description,
                        category=scenario.category,
                        estimated_minutes=scenario.estimated_minutes,
                        steps=scenario.steps,
                        prerequisites=scenario.prerequisites,
                        tags=scenario.tags,
                        thumbnail_url=scenario.thumbnail_url,
                        featured=scenario.featured,
                        enabled=scenario.enabled,
                    )
                    session.add(db_scenario)
            
            await session.commit()
            print("Default scenarios loaded")
    except Exception as e:
        print(f"Warning: Could not load default scenarios: {e}")


@asynccontextmanager
async def get_demo_session() -> AsyncSession:
    """Get a demo database session."""
    async with _demo_session_factory() as session:
        yield session


def get_tenant_manager() -> DemoTenantManager:
    if _demo_tenant_manager is None:
        raise RuntimeError("Demo services not initialized. Call init_demo_services() first.")
    return _demo_tenant_manager


def get_session_manager() -> DemoSessionManager:
    if _demo_session_manager is None:
        raise RuntimeError("Demo services not initialized. Call init_demo_services() first.")
    return _demo_session_manager


def get_snapshot_manager() -> DemoSnapshotManager:
    if _demo_snapshot_manager is None:
        raise RuntimeError("Demo services not initialized. Call init_demo_services() first.")
    return _demo_snapshot_manager


async def shutdown_demo_services():
    """Shutdown demo services on application shutdown."""
    global _demo_engine
    if _demo_engine:
        await _demo_engine.dispose()
    print("Demo services shutdown")


# ─────────────────────────────────────────────────────────────────────────────
# Helper Functions for API Endpoints
# ─────────────────────────────────────────────────────────────────────────────

async def create_demo_tenant_for_user(user_id: str, name: str = "My Demo Workspace") -> str:
    """Create a demo tenant for a specific user."""
    manager = get_tenant_manager()
    config = TenantConfig(
        id=f"demo_{user_id}_{uuid.uuid4().hex[:8]}",
        name=name,
        description=f"Demo workspace for user {user_id}",
        mode=DemoMode.INTERACTIVE,
        reset_interval_minutes=60,
        max_session_minutes=30,
        allowed_features=["workflows", "reports", "analytics", "llm", "engagement"],
    )
    tenant = await manager.create_tenant(config)
    return tenant.id


async def start_user_demo_session(user_id: str, tenant_id: str, scenario_key: Optional[str] = None) -> str:
    """Start a demo session for a user."""
    manager = get_session_manager()
    config = SessionConfig(
        tenant_id=tenant_id,
        user_id=user_id,
        scenario_key=scenario_key,
        mode=DemoMode.INTERACTIVE,
        max_duration_minutes=30,
    )
    session = await manager.create_session(config)
    return session.id


async def get_user_demo_tenant(user_id: str) -> Optional[str]:
    """Get the demo tenant ID for a user."""
    manager = get_tenant_manager()
    # In a real implementation, you'd query by user_id
    # For now, return the default tenant
    tenant = await manager.get_tenant("demo-default")
    return tenant.id if tenant else None


async def cleanup_user_demo_sessions(user_id: str) -> int:
    """Clean up expired demo sessions for a user."""
    manager = get_session_manager()
    # This would need a method to list sessions by user_id
    # For now, just call the general cleanup
    return await manager.cleanup_expired_sessions()


# ─────────────────────────────────────────────────────────────────────────────
# Import dependencies
# ─────────────────────────────────────────────────────────────────────────────

import uuid
from sqlalchemy import select
from shared.demo.tenant_manager import DemoScenario