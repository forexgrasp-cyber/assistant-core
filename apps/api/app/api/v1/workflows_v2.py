"""
Workflow API v2 endpoints — Production-grade using shared canonical services.

Endpoints:
- CRUD for workflow definitions
- Execution management (run, list, get, cancel)
- Event-based triggers
- Schedule management (cron, interval, once)
- Health and monitoring
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from datetime import datetime
import structlog

from ...core.config import get_settings
from ...core.security import get_current_active_user
from ...services.workflow_engine_v2 import (
    WorkflowEngineV2,
    get_workflow_engine,
    startup_workflow_engine,
    shutdown_workflow_engine,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/v2", tags=["Workflows v2"])

settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Dependency Injection
# ─────────────────────────────────────────────────────────────────────────────


async def get_engine(current_user=Depends(get_current_active_user)) -> WorkflowEngineV2:
    """Get workflow engine for current user's tenant."""
    return get_workflow_engine(current_user.client_id)


# ─────────────────────────────────────────────────────────────────────────────
# Request/Response Models
# ─────────────────────────────────────────────────────────────────────────────


class WorkflowCreate(BaseModel):
    name: str
    description: str = ""
    category: str = "general"
    tags: list[str] = Field(default_factory=list)
    steps: list[dict] = Field(default_factory=list)
    triggers: list[dict] = Field(default_factory=list)
    settings: dict = Field(default_factory=dict)


class WorkflowUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    tags: list[str] | None = None
    steps: list[dict] | None = None
    triggers: list[dict] | None = None
    settings: dict | None = None
    status: str | None = None
    is_active: bool | None = None


class WorkflowExecute(BaseModel):
    trigger_data: dict = Field(default_factory=dict)
    trigger_source: str = "api"
    trigger_type: str = "api"


class ScheduleCreate(BaseModel):
    workflow_id: str
    schedule_type: str  # cron, interval, once
    cron_expression: str | None = None
    interval_seconds: int | None = None
    run_at: str | None = None
    timezone: str = "UTC"
    name: str = ""
    max_runs: int = 0
    payload: dict = Field(default_factory=dict)


class TriggerEvent(BaseModel):
    event_type: str
    event_data: dict


# ─────────────────────────────────────────────────────────────────────────────
# Workflow CRUD
# ─────────────────────────────────────────────────────────────────────────────


@router.post("", status_code=201)
async def create_workflow(
    workflow_data: WorkflowCreate,
    engine: WorkflowEngineV2 = Depends(get_engine),
):
    workflow = await engine.create_workflow(
        name=workflow_data.name,
        steps=workflow_data.steps,
        triggers=workflow_data.triggers,
        settings=workflow_data.settings,
        description=workflow_data.description,
    )
    return {"id": workflow.id, "message": "Workflow created"}


@router.get("")
async def list_workflows(
    status: Optional[str] = None,
    engine: WorkflowEngineV2 = Depends(get_engine),
):
    workflows = await engine.list_workflows(status=status)
    return [
        {
            "id": w.id,
            "name": w.name,
            "description": w.description,
            "category": w.category,
            "status": w.status,
            "version": w.version,
            "is_active": w.is_active,
            "steps_count": len(w.steps),
            "triggers_count": len(w.triggers),
            "created_at": w.created_at,
            "updated_at": w.updated_at,
        }
        for w in workflows
    ]


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    engine: WorkflowEngineV2 = Depends(get_engine),
):
    workflow = await engine.get_workflow(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {
        "id": workflow.id,
        "name": workflow.name,
        "description": workflow.description,
        "category": "general",  # Add to model if needed
        "status": workflow.status,
        "version": workflow.version,
        "is_active": workflow.is_active,
        "steps": workflow.steps,
        "triggers": workflow.triggers,
        "settings": workflow.settings,
        "created_at": workflow.created_at,
        "updated_at": workflow.updated_at,
    }


@router.patch("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    workflow_data: WorkflowUpdate,
    engine: WorkflowEngineV2 = Depends(get_engine),
):
    updates = workflow_data.model_dump(exclude_unset=True)
    workflow = await engine.update_workflow(workflow_id, updates)
    return {"message": "Workflow updated"}


@router.post("/{workflow_id}/publish")
async def publish_workflow(
    workflow_id: str,
    engine: WorkflowEngineV2 = Depends(get_engine),
):
    workflow = await engine.publish_workflow(workflow_id)
    return {"message": "Workflow published", "version": workflow.version}


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(
    workflow_id: str,
    engine: WorkflowEngineV2 = Depends(get_engine),
):
    # TODO: Add delete method to engine
    raise HTTPException(status_code=501, detail="Not implemented")


# ─────────────────────────────────────────────────────────────────────────────
# Execution
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/{workflow_id}/execute", status_code=202)
async def execute_workflow(
    workflow_id: str,
    execute_data: WorkflowExecute,
    engine: WorkflowEngineV2 = Depends(get_engine),
):
    try:
        result = await engine.execute_workflow(
            workflow_id=workflow_id,
            trigger_data=execute_data.trigger_data,
            trigger_source=execute_data.trigger_source,
            trigger_type=execute_data.trigger_type,
        )
        return {
            "execution_id": result.execution_id,
            "status": result.final_status,
            "success": result.success,
            "total_duration_ms": result.total_duration_ms,
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{workflow_id}/executions")
async def list_executions(
    workflow_id: str,
    status: Optional[str] = None,
    engine: WorkflowEngineV2 = Depends(get_engine),
):
    executions = await engine.list_executions(workflow_id=workflow_id, status=status)
    return [
        {
            "id": e.id,
            "workflow_id": e.workflow_id,
            "status": e.status,
            "trigger_type": e.trigger_type,
            "trigger_source": e.trigger_source,
            "current_step": e.current_step,
            "retry_count": e.retry_count,
            "started_at": e.started_at,
            "completed_at": e.completed_at,
        }
        for e in executions
    ]


@router.get("/{workflow_id}/executions/{execution_id}")
async def get_execution(
    workflow_id: str,
    execution_id: str,
    engine: WorkflowEngineV2 = Depends(get_engine),
):
    execution = await engine.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    return {
        "id": execution.id,
        "workflow_id": execution.workflow_id,
        "status": execution.status,
        "trigger_type": execution.trigger_type,
        "trigger_data": execution.trigger_data,
        "trigger_source": execution.trigger_source,
        "current_step": execution.current_step,
        "context": execution.context,
        "step_results": execution.step_results,
        "error_message": execution.error_message,
        "retry_count": execution.retry_count,
        "started_at": execution.started_at,
        "completed_at": execution.completed_at,
    }


@router.post("/{workflow_id}/executions/{execution_id}/cancel")
async def cancel_execution(
    workflow_id: str,
    execution_id: str,
    engine: WorkflowEngineV2 = Depends(get_engine),
):
    try:
        await engine.cancel_execution(execution_id)
        return {"message": "Execution cancelled"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Event Triggers
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/trigger", status_code=202)
async def trigger_by_event(
    event: TriggerEvent,
    engine: WorkflowEngineV2 = Depends(get_engine),
):
    """
    Trigger workflows by event type.

    Body: { event_type: string, event_data: object }
    """
    try:
        results = await engine.trigger_by_event(event.event_type, event.event_data)
        return {
            "message": f"Triggered {len(results)} workflows",
            "executions": [
                {
                    "execution_id": r.execution_id,
                    "workflow_id": r.workflow_id,
                    "status": r.final_status,
                }
                for r in results
            ],
        }
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Schedules
# ─────────────────────────────────────────────────────────────────────────────


@router.post("/schedules", status_code=201)
async def create_schedule(
    schedule_data: ScheduleCreate,
    engine: WorkflowEngineV2 = Depends(get_engine),
):
    try:
        result = engine.schedule_workflow(
            workflow_id=schedule_data.workflow_id,
            schedule_type=schedule_data.schedule_type,
            cron_expression=schedule_data.cron_expression,
            interval_seconds=schedule_data.interval_seconds,
            run_at=schedule_data.run_at,
            timezone=schedule_data.timezone,
            name=schedule_data.name,
            max_runs=schedule_data.max_runs,
            payload=schedule_data.payload,
        )
        return {"id": result["id"], "message": "Schedule created"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/schedules")
async def list_schedules(
    workflow_id: Optional[str] = None,
    status: Optional[str] = None,
    engine: WorkflowEngineV2 = Depends(get_engine),
):
    schedules = engine.get_schedules(workflow_id=workflow_id, status=status)
    return schedules


@router.get("/schedules/{schedule_id}")
async def get_schedule(
    schedule_id: str,
    engine: WorkflowEngineV2 = Depends(get_engine),
):
    schedule = engine.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.post("/schedules/{schedule_id}/pause")
async def pause_schedule(
    schedule_id: str,
    engine: WorkflowEngineV2 = Depends(get_engine),
):
    result = engine.pause_schedule(schedule_id)
    if not result:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"message": "Schedule paused"}


@router.post("/schedules/{schedule_id}/resume")
async def resume_schedule(
    schedule_id: str,
    engine: WorkflowEngineV2 = Depends(get_engine),
):
    result = engine.resume_schedule(schedule_id)
    if not result:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return {"message": "Schedule resumed"}


@router.delete("/schedules/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: str,
    engine: WorkflowEngineV2 = Depends(get_engine),
):
    try:
        engine.delete_schedule(schedule_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/schedules/{schedule_id}/runs")
async def get_schedule_runs(
    schedule_id: str,
    limit: int = 50,
    engine: WorkflowEngineV2 = Depends(get_engine),
):
    runs = engine.get_run_history(schedule_id, limit)
    return runs


# ─────────────────────────────────────────────────────────────────────────────
# Health / Maintenance
# ─────────────────────────────────────────────────────────────────────────────


@router.get("/health")
async def health_check(
    engine: WorkflowEngineV2 = Depends(get_engine),
):
    return engine.health()


@router.post("/maintenance/cleanup")
async def cleanup_old_data(
    max_age_hours: int = 168,
    engine: WorkflowEngineV2 = Depends(get_engine),
):
    result = engine.cleanup_old_data(max_age_hours)
    return {"cleaned": result, "message": "Cleanup completed"}


__all__ = ["router"]