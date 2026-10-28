"""
Demo Management API endpoints.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
import structlog

from ...core.config import get_settings
from ...core.database import get_db
from ...core.security import get_current_active_user

logger = structlog.get_logger()
router = APIRouter(prefix="/demo", tags=["Demo"])


# ─────────────────────────────────────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────────────────────────────────────

class DemoTenantCreate(BaseModel):
    name: str
    description: str = ""
    mode: str = "interactive"
    reset_interval_minutes: int = 60
    max_session_minutes: int = 30
    allowed_features: List[str] = Field(default_factory=list)
    readonly: bool = False
    branding: Optional[dict] = None


class DemoTenantUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    mode: Optional[str] = None
    reset_interval_minutes: Optional[int] = None
    max_session_minutes: Optional[int] = None
    allowed_features: Optional[List[str]] = None
    readonly: Optional[bool] = None
    branding: Optional[dict] = None


class DemoSessionCreate(BaseModel):
    tenant_id: str
    scenario_key: Optional[str] = None
    mode: str = "interactive"


class DemoSnapshotCreate(BaseModel):
    tenant_id: str
    name: str
    state_data: dict
    session_id: Optional[str] = None
    description: Optional[str] = None
    snapshot_type: str = "manual"


class DemoScenarioCreate(BaseModel):
    key: str
    name: str
    description: str = ""
    category: str = "general"
    estimated_minutes: int = 5
    steps: List[dict] = Field(default_factory=list)
    prerequisites: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Demo Tenant Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/tenants", status_code=201)
async def create_demo_tenant(
    tenant_data: DemoTenantCreate,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import DemoTenantManager, TenantConfig, get_demo_tenant_manager
    
    manager = get_demo_tenant_manager(db)
    
    config = TenantConfig(
        id=f"demo_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        name=tenant_data.name,
        description=tenant_data.description,
        mode=tenant_data.mode,
        reset_interval_minutes=tenant_data.reset_interval_minutes,
        max_session_minutes=tenant_data.max_session_minutes,
        allowed_features=tenant_data.allowed_features,
        readonly=tenant_data.readonly,
        branding=tenant_data.branding,
    )
    
    tenant = await manager.create_tenant(config)
    return {"id": tenant.id, "message": "Demo tenant created"}


@router.get("/tenants")
async def list_demo_tenants(
    status: Optional[str] = None,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import get_demo_tenant_manager, DemoTenantStatus
    
    manager = get_demo_tenant_manager(db)
    tenant_status = DemoTenantStatus(status) if status else None
    tenants = await manager.list_tenants(tenant_status)
    
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "mode": t.mode,
            "status": t.status,
            "reset_interval_minutes": t.reset_interval_minutes,
            "max_session_minutes": t.max_session_minutes,
            "total_sessions": t.total_sessions,
            "last_reset_at": t.last_reset_at.isoformat() if t.last_reset_at else None,
            "next_reset_at": t.next_reset_at.isoformat() if t.next_reset_at else None,
            "created_at": t.created_at.isoformat(),
        }
        for t in tenants
    ]


@router.get("/tenants/{tenant_id}")
async def get_demo_tenant(
    tenant_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import get_demo_tenant_manager
    
    manager = get_demo_tenant_manager(db)
    tenant = await manager.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Demo tenant not found")
    
    return {
        "id": tenant.id,
        "name": tenant.name,
        "description": tenant.description,
        "mode": tenant.mode,
        "status": tenant.status,
        "seed_data": tenant.seed_data,
        "reset_interval_minutes": tenant.reset_interval_minutes,
        "max_session_minutes": tenant.max_session_minutes,
        "allowed_features": tenant.allowed_features,
        "readonly": tenant.readonly,
        "branding": tenant.branding,
        "total_sessions": tenant.total_sessions,
        "last_reset_at": tenant.last_reset_at.isoformat() if tenant.last_reset_at else None,
        "next_reset_at": tenant.next_reset_at.isoformat() if tenant.next_reset_at else None,
        "created_at": tenant.created_at.isoformat(),
        "updated_at": tenant.updated_at.isoformat(),
    }


@router.patch("/tenants/{tenant_id}")
async def update_demo_tenant(
    tenant_id: str,
    tenant_data: DemoTenantUpdate,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import get_demo_tenant_manager
    
    manager = get_demo_tenant_manager(db)
    updates = tenant_data.model_dump(exclude_unset=True)
    tenant = await manager.update_tenant(tenant_id, updates)
    if not tenant:
        raise HTTPException(status_code=404, detail="Demo tenant not found")
    return {"message": "Demo tenant updated"}


@router.delete("/tenants/{tenant_id}", status_code=204)
async def delete_demo_tenant(
    tenant_id: str,
    force: bool = False,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import get_demo_tenant_manager
    
    manager = get_demo_tenant_manager(db)
    success = await manager.delete_tenant(tenant_id, force=force)
    if not success:
        raise HTTPException(status_code=404, detail="Demo tenant not found")
    return Response(status_code=204)


@router.post("/tenants/{tenant_id}/reset")
async def reset_demo_tenant(
    tenant_id: str,
    preserve_snapshots: bool = True,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import get_demo_tenant_manager
    
    manager = get_demo_tenant_manager(db)
    success = await manager.reset_tenant(tenant_id, preserve_snapshots)
    if not success:
        raise HTTPException(status_code=404, detail="Demo tenant not found or reset failed")
    return {"message": "Demo tenant reset completed"}


@router.get("/tenants/{tenant_id}/stats")
async def get_demo_tenant_stats(
    tenant_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import get_demo_tenant_manager
    
    manager = get_demo_tenant_manager(db)
    stats = await manager.get_tenant_stats(tenant_id)
    return stats


# ─────────────────────────────────────────────────────────────────────────────
# Demo Session Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/tenants/{tenant_id}/sessions", status_code=201)
async def create_demo_session(
    tenant_id: str,
    session_data: DemoSessionCreate,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import get_demo_session_manager, SessionConfig, DemoMode
    
    manager = get_demo_session_manager(db)
    
    config = SessionConfig(
        tenant_id=tenant_id,
        user_id=str(current_user.id),
        scenario_key=session_data.scenario_key,
        mode=DemoMode(session_data.mode),
        max_duration_minutes=60,  # Default, could be from tenant config
    )
    
    session_obj = await manager.create_session(config)
    return {
        "id": session_obj.id,
        "tenant_id": session_obj.tenant_id,
        "scenario_key": session_obj.scenario_key,
        "mode": session_obj.mode,
        "status": session_obj.status,
        "expires_at": session_obj.expires_at.isoformat() if session_obj.expires_at else None,
        "started_at": session_obj.started_at.isoformat(),
    }


@router.get("/tenants/{tenant_id}/sessions")
async def list_demo_sessions(
    tenant_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import get_demo_session_manager, DemoSessionStatus
    
    manager = get_demo_session_manager(db)
    session_status = DemoSessionStatus(status) if status else None
    sessions = await manager.list_sessions(tenant_id, session_status, limit, offset)
    
    return [
        {
            "id": s.id,
            "tenant_id": s.tenant_id,
            "user_id": s.user_id,
            "scenario_key": s.scenario_key,
            "mode": s.mode,
            "status": s.status,
            "current_step_index": s.current_step_index,
            "steps_completed": s.steps_completed,
            "started_at": s.started_at.isoformat(),
            "ended_at": s.ended_at.isoformat() if s.ended_at else None,
            "step_count": s.step_count,
            "action_count": s.action_count,
        }
        for s in sessions
    ]


@router.get("/tenants/{tenant_id}/sessions/{session_id}")
async def get_demo_session(
    tenant_id: str,
    session_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import get_demo_session_manager
    
    manager = get_demo_session_manager(db)
    session_obj = await manager.get_session(session_id)
    if not session_obj or session_obj.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Demo session not found")
    
    return {
        "id": session_obj.id,
        "tenant_id": session_obj.tenant_id,
        "user_id": session_obj.user_id,
        "scenario_key": session_obj.scenario_key,
        "mode": session_obj.mode,
        "status": session_obj.status,
        "current_step_index": session_obj.current_step_index,
        "steps_completed": session_obj.steps_completed,
        "recording_enabled": session_obj.recording_enabled,
        "recording_id": session_obj.recording_id,
        "started_at": session_obj.started_at.isoformat(),
        "ended_at": session_obj.ended_at.isoformat() if session_obj.ended_at else None,
        "expires_at": session_obj.expires_at.isoformat() if session_obj.expires_at else None,
        "step_count": session_obj.step_count,
        "action_count": session_obj.action_count,
    }


@router.post("/tenants/{tenant_id}/sessions/{session_id}/end")
async def end_demo_session(
    tenant_id: str,
    session_id: str,
    status: str = "completed",
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import get_demo_session_manager, DemoSessionStatus
    
    manager = get_demo_session_manager(db)
    session_status = DemoSessionStatus(status)
    success = await manager.end_session(session_id, session_status)
    if not success:
        raise HTTPException(status_code=404, detail="Demo session not found")
    return {"message": "Demo session ended"}


@router.post("/tenants/{tenant_id}/sessions/{session_id}/progress")
async def update_session_progress(
    tenant_id: str,
    session_id: str,
    step_index: int,
    step_key: str,
    action_count: int = 1,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import get_demo_session_manager
    
    manager = get_demo_session_manager(db)
    success = await manager.update_session_progress(session_id, step_index, step_key, action_count)
    if not success:
        raise HTTPException(status_code=404, detail="Demo session not found")
    return {"message": "Session progress updated"}


@router.post("/tenants/{tenant_id}/sessions/{session_id}/actions")
async def record_session_action(
    tenant_id: str,
    session_id: str,
    event_type: str,
    target_selector: str,
    event_data: dict,
    viewport: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import get_demo_session_manager
    
    manager = get_demo_session_manager(db)
    success = await manager.record_action(session_id, event_type, target_selector, event_data, viewport)
    if not success:
        raise HTTPException(status_code=404, detail="Demo session not found")
    return {"message": "Action recorded"}


@router.post("/tenants/{tenant_id}/sessions/{session_id}/record/start")
async def start_session_recording(
    tenant_id: str,
    session_id: str,
    name: Optional[str] = None,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import get_demo_session_manager
    
    manager = get_demo_session_manager(db)
    recording = await manager.start_recording(session_id, name)
    if not recording:
        raise HTTPException(status_code=404, detail="Demo session not found")
    return {
        "id": recording.id,
        "session_id": recording.session_id,
        "name": recording.name,
        "started_at": recording.started_at.isoformat(),
    }


@router.post("/tenants/{tenant_id}/sessions/{session_id}/record/stop")
async def stop_session_recording(
    tenant_id: str,
    session_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import get_demo_session_manager
    
    manager = get_demo_session_manager(db)
    recording = await manager.stop_recording(session_id)
    if not recording:
        raise HTTPException(status_code=404, detail="Demo session or recording not found")
    return {
        "id": recording.id,
        "session_id": recording.session_id,
        "name": recording.name,
        "started_at": recording.started_at.isoformat(),
        "ended_at": recording.ended_at.isoformat() if recording.ended_at else None,
        "duration_seconds": recording.duration_seconds,
        "events_count": recording.events_count,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Demo Snapshot Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/tenants/{tenant_id}/snapshots", status_code=201)
async def create_demo_snapshot(
    tenant_id: str,
    snapshot_data: DemoSnapshotCreate,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import get_demo_snapshot_manager, SnapshotType
    
    manager = get_demo_snapshot_manager(db)
    snapshot = await manager.create_snapshot(
        tenant_id=tenant_id,
        name=snapshot_data.name,
        state_data=snapshot_data.state_data,
        session_id=snapshot_data.session_id,
        description=snapshot_data.description,
        snapshot_type=SnapshotType(snapshot_data.snapshot_type),
        auto_generated=False,
        created_by=str(current_user.id),
    )
    return {
        "id": snapshot.id,
        "name": snapshot.name,
        "snapshot_type": snapshot.snapshot_type,
        "created_at": snapshot.created_at.isoformat(),
        "state_size_bytes": snapshot.state_size_bytes,
    }


@router.get("/tenants/{tenant_id}/snapshots")
async def list_demo_snapshots(
    tenant_id: str,
    session_id: Optional[str] = None,
    snapshot_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import get_demo_snapshot_manager, SnapshotType
    
    manager = get_demo_snapshot_manager(db)
    snap_type = SnapshotType(snapshot_type) if snapshot_type else None
    snapshots = await manager.list_snapshots(tenant_id, session_id, snap_type, limit, offset)
    
    return [
        {
            "id": s.id,
            "tenant_id": s.tenant_id,
            "session_id": s.session_id,
            "name": s.name,
            "description": s.description,
            "snapshot_type": s.snapshot_type,
            "auto_generated": s.auto_generated,
            "state_size_bytes": s.state_size_bytes,
            "created_at": s.created_at.isoformat(),
            "expires_at": s.expires_at.isoformat() if s.expires_at else None,
            "restored_count": s.restored_count,
            "last_restored_at": s.last_restored_at.isoformat() if s.last_restored_at else None,
        }
        for s in snapshots
    ]


@router.post("/tenants/{tenant_id}/snapshots/{snapshot_id}/restore")
async def restore_demo_snapshot(
    tenant_id: str,
    snapshot_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import get_demo_snapshot_manager
    
    manager = get_demo_snapshot_manager(db)
    state_data = await manager.restore_snapshot(snapshot_id, str(current_user.id))
    return {"message": "Snapshot restored", "state_data": state_data}


@router.delete("/tenants/{tenant_id}/snapshots/{snapshot_id}", status_code=204)
async def delete_demo_snapshot(
    tenant_id: str,
    snapshot_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import get_demo_snapshot_manager
    
    manager = get_demo_snapshot_manager(db)
    success = await manager.delete_snapshot(snapshot_id)
    if not success:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return Response(status_code=204)


# ─────────────────────────────────────────────────────────────────────────────
# Demo Scenario Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/scenarios")
async def list_demo_scenarios(
    category: Optional[str] = None,
    enabled_only: bool = True,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import DEFAULT_SCENARIOS
    
    scenarios = DEFAULT_SCENARIOS
    if enabled_only:
        scenarios = [s for s in scenarios if s.enabled]
    if category:
        scenarios = [s for s in scenarios if s.category == category]
    
    return [
        {
            "key": s.key,
            "name": s.name,
            "description": s.description,
            "category": s.category,
            "estimated_minutes": s.estimated_minutes,
            "steps_count": len(s.steps),
            "prerequisites": s.prerequisites,
            "tags": s.tags,
            "featured": s.featured,
            "enabled": s.enabled,
        }
        for s in scenarios
    ]


@router.get("/scenarios/{scenario_key}")
async def get_demo_scenario(
    scenario_key: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...services.demo_tenant_manager import DEFAULT_SCENARIOS
    
    scenario = next((s for s in DEFAULT_SCENARIOS if s.key == scenario_key), None)
    if not scenario:
        raise HTTPException(status_code=404, detail="Demo scenario not found")
    
    return {
        "key": scenario.key,
        "name": scenario.name,
        "description": scenario.description,
        "category": scenario.category,
        "estimated_minutes": scenario.estimated_minutes,
        "steps": scenario.steps,
        "prerequisites": scenario.prerequisites,
        "tags": scenario.tags,
        "featured": scenario.featured,
        "enabled": scenario.enabled,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Demo Analytics Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/tenants/{tenant_id}/analytics")
async def get_demo_analytics(
    tenant_id: str,
    days: int = 30,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get demo analytics for a tenant."""
    # This would query the DemoAnalytics table
    # For now, return mock data
    return {
        "tenant_id": tenant_id,
        "period_days": days,
        "sessions": {
            "started": 0,
            "completed": 0,
            "abandoned": 0,
            "avg_duration_seconds": 0,
        },
        "steps": {
            "completed": 0,
            "failed": 0,
            "avg_per_session": 0,
        },
        "scenarios": {},
        "recordings": {
            "created": 0,
            "total_duration_seconds": 0,
        },
        "snapshots": {
            "created": 0,
            "restored": 0,
        },
        "errors": {
            "count": 0,
            "types": {},
        },
    }


# Need to import Response for delete endpoints
from fastapi import Response