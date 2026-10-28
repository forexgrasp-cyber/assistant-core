"""
Workflow API endpoints: Definitions, Executions, Triggers.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from datetime import datetime
import uuid
import structlog

from ...core.config import get_settings
from ...core.database import get_db
from ...core.security import get_current_active_user
from ...models import WorkflowDefinition, WorkflowExecution, WorkflowNodeExecution, WorkflowTrigger

logger = structlog.get_logger()
router = APIRouter()

settings = get_settings()

@router.post("", status_code=201)
async def create_workflow(
    workflow_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WorkflowDefinition
    
    workflow = WorkflowDefinition(
        client_id=current_user.client_id,
        name=workflow_data.get("name"),
        description=workflow_data.get("description"),
        category=workflow_data.get("category", "general"),
        tags=workflow_data.get("tags", []),
        nodes=workflow_data.get("nodes", []),
        edges=workflow_data.get("edges", []),
        viewport=workflow_data.get("viewport"),
        triggers=workflow_data.get("triggers", []),
        settings=workflow_data.get("settings", {}),
    )
    db.add(workflow)
    await db.commit()
    await db.refresh(workflow)
    return {"id": str(workflow.id), "message": "Workflow created"}

@router.get("")
async def list_workflows(
    status: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WorkflowDefinition
    from sqlalchemy import desc
    
    query = select(WorkflowDefinition).where(WorkflowDefinition.client_id == current_user.client_id)
    
    if status:
        query = query.where(WorkflowDefinition.status == status)
    if category:
        query = query.where(WorkflowDefinition.category == category)
    
    query = query.order_by(desc(WorkflowDefinition.updated_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    workflows = result.scalars().all()
    
    return [
        {
            "id": str(w.id),
            "name": w.name,
            "slug": w.slug,
            "description": w.description,
            "category": w.category,
            "status": w.status,
            "version": w.version,
            "total_executions": w.total_executions,
            "successful_executions": w.successful_executions,
            "failed_executions": w.failed_executions,
            "created_at": w.created_at.isoformat(),
            "updated_at": w.updated_at.isoformat(),
        }
        for w in workflows
    ]

@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WorkflowDefinition
    result = await db.execute(
        select(WorkflowDefinition).where(
            WorkflowDefinition.id == workflow_id,
            WorkflowDefinition.client_id == current_user.client_id
        )
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return {
        "id": str(workflow.id),
        "name": workflow.name,
        "slug": workflow.slug,
        "description": workflow.description,
        "category": workflow.category,
        "tags": workflow.tags,
        "version": workflow.version,
        "status": workflow.status,
        "nodes": workflow.nodes,
        "edges": workflow.edges,
        "viewport": workflow.viewport,
        "triggers": workflow.triggers,
        "settings": workflow.settings,
        "max_concurrent_executions": workflow.max_concurrent_executions,
        "timeout_seconds": workflow.timeout_seconds,
        "max_retries": workflow.max_retries,
        "retry_backoff_seconds": workflow.retry_backoff_seconds,
        "schedule": workflow.schedule,
        "timezone": workflow.timezone,
        "published_at": workflow.published_at.isoformat() if workflow.published_at else None,
        "total_executions": workflow.total_executions,
        "successful_executions": workflow.successful_executions,
        "failed_executions": workflow.failed_executions,
        "avg_execution_time_ms": float(workflow.avg_execution_time_ms or 0),
        "created_at": workflow.created_at.isoformat(),
        "updated_at": workflow.updated_at.isoformat(),
    }

@router.patch("/{workflow_id}")
async def update_workflow(
    workflow_id: str,
    workflow_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WorkflowDefinition
    result = await db.execute(
        select(WorkflowDefinition).where(
            WorkflowDefinition.id == workflow_id,
            WorkflowDefinition.client_id == current_user.client_id
        )
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    update_data = workflow_data
    for field, value in update_data.items():
        if hasattr(workflow, field):
            setattr(workflow, field, value)
    
    workflow.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(workflow)
    return {"message": "Workflow updated"}

@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(
    workflow_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WorkflowDefinition
    result = await db.execute(
        select(WorkflowDefinition).where(
            WorkflowDefinition.id == workflow_id,
            WorkflowDefinition.client_id == current_user.client_id
        )
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    await db.delete(workflow)
    await db.commit()
    return Response(status_code=204)

@router.post("/{workflow_id}/publish")
async def publish_workflow(
    workflow_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WorkflowDefinition
    result = await db.execute(
        select(WorkflowDefinition).where(
            WorkflowDefinition.id == workflow_id,
            WorkflowDefinition.client_id == current_user.client_id
        )
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    workflow.status = "published"
    workflow.published_at = datetime.utcnow()
    workflow.version += 1
    await db.commit()
    return {"message": "Workflow published", "version": workflow.version}

@router.post("/{workflow_id}/execute", status_code=202)
async def execute_workflow(
    workflow_id: str,
    trigger_data: dict = {},
    trigger_source: str = "api",
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WorkflowDefinition, WorkflowExecution
    import uuid
    
    result = await db.execute(
        select(WorkflowDefinition).where(
            WorkflowDefinition.id == workflow_id,
            WorkflowDefinition.client_id == current_user.client_id,
            WorkflowDefinition.status == "published"
        )
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Published workflow not found")
    
    execution = WorkflowExecution(
        id=uuid.uuid4(),
        workflow_id=workflow.id,
        client_id=current_user.client_id,
        trigger_type="api",
        trigger_data=trigger_data,
        trigger_source=trigger_source,
        context={},
        variables={},
        status="pending",
        queued_at=datetime.utcnow(),
    )
    db.add(execution)
    await db.commit()
    
    return {"execution_id": str(execution.id), "status": "queued"}

@router.get("/{workflow_id}/executions")
async def list_executions(
    workflow_id: str,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WorkflowExecution
    from sqlalchemy import desc
    
    query = select(WorkflowExecution).where(WorkflowExecution.workflow_id == workflow_id)
    if status:
        query = query.where(WorkflowExecution.status == status)
    query = query.order_by(desc(WorkflowExecution.queued_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    executions = result.scalars().all()
    
    return [
        {
            "id": str(e.id),
            "status": e.status,
            "trigger_type": e.trigger_type,
            "trigger_source": e.trigger_source,
            "current_node_id": e.current_node_id,
            "completed_nodes": e.completed_nodes,
            "total_nodes": e.total_nodes,
            "progress_percent": float(e.progress_percent or 0),
            "retry_count": e.retry_count,
            "started_at": e.started_at.isoformat() if e.started_at else None,
            "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            "duration_ms": e.duration_ms,
            "revenue_attributed": float(e.revenue_attributed or 0),
        }
        for e in executions
    ]

@router.get("/{workflow_id}/executions/{execution_id}")
async def get_execution(
    workflow_id: str,
    execution_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WorkflowExecution
    result = await db.execute(
        select(WorkflowExecution).where(
            WorkflowExecution.id == execution_id,
            WorkflowExecution.workflow_id == workflow_id,
            WorkflowExecution.client_id == current_user.client_id
        )
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    return {
        "id": str(execution.id),
        "workflow_id": str(execution.workflow_id),
        "status": execution.status,
        "trigger_type": execution.trigger_type,
        "trigger_data": execution.trigger_data,
        "context": execution.context,
        "variables": execution.variables,
        "status": execution.status,
        "current_node_id": execution.current_node_id,
        "completed_nodes": execution.completed_nodes,
        "total_nodes": execution.total_nodes,
        "progress_percent": float(execution.progress_percent or 0),
        "error": execution.error,
        "error_node_id": execution.error_node_id,
        "retry_count": execution.retry_count,
        "started_at": execution.started_at.isoformat() if execution.started_at else None,
        "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
        "duration_ms": execution.duration_ms,
        "output": execution.output,
        "revenue_attributed": float(execution.revenue_attributed or 0),
    }

@router.post("/{workflow_id}/executions/{execution_id}/cancel")
async def cancel_execution(
    workflow_id: str,
    execution_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WorkflowExecution
    result = await db.execute(
        select(WorkflowExecution).where(
            WorkflowExecution.id == execution_id,
            WorkflowExecution.workflow_id == workflow_id,
            WorkflowExecution.client_id == current_user.client_id
        )
    )
    execution = result.scalar_one_or_none()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")
    
    if execution.status not in ["pending", "running", "retrying"]:
        raise HTTPException(status_code=400, detail="Cannot cancel execution in current state")
    
    execution.status = "cancelled"
    execution.completed_at = datetime.utcnow()
    await db.commit()
    return {"message": "Execution cancelled"}

@router.get("/{workflow_id}/triggers")
async def list_triggers(
    workflow_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WorkflowTrigger
    result = await db.execute(
        select(WorkflowTrigger).where(
            WorkflowTrigger.workflow_id == workflow_id,
            WorkflowTrigger.client_id == current_user.client_id
        )
    )
    triggers = result.scalars().all()
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "type": t.type,
            "is_active": t.is_active,
            "cron_expression": t.cron_expression,
            "config": t.config,
        }
        for t in triggers
    ]

@router.post("/{workflow_id}/triggers", status_code=201)
async def create_trigger(
    workflow_id: str,
    trigger_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WorkflowTrigger
    
    trigger = WorkflowTrigger(
        workflow_id=workflow_id,
        name=trigger_data.get("name"),
        type=trigger_data.get("type"),
        config=trigger_data.get("config", {}),
        conditions=trigger_data.get("conditions", []),
        deduplication_key=trigger_data.get("deduplication_key"),
        deduplication_window_seconds=trigger_data.get("deduplication_window_seconds", 0),
        rate_limit=trigger_data.get("rate_limit"),
        rate_limit_window=trigger_data.get("rate_limit_window", 60),
    )
    db.add(trigger)
    await db.commit()
    await db.refresh(trigger)
    return {"id": str(trigger.id), "message": "Trigger created"}

@router.patch("/{workflow_id}/triggers/{trigger_id}")
async def update_trigger(
    workflow_id: str,
    trigger_id: str,
    trigger_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WorkflowTrigger
    result = await db.execute(
        select(WorkflowTrigger).where(
            WorkflowTrigger.id == trigger_id,
            WorkflowTrigger.workflow_id == workflow_id
        )
    )
    trigger = result.scalar_one_or_none()
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    
    for field, value in trigger_data.items():
        if hasattr(trigger, field):
            setattr(trigger, field, value)
    
    await db.commit()
    return {"message": "Trigger updated"}

@router.delete("/{workflow_id}/triggers/{trigger_id}", status_code=204)
async def delete_trigger(
    workflow_id: str,
    trigger_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WorkflowTrigger
    result = await db.execute(
        select(WorkflowTrigger).where(
            WorkflowTrigger.id == trigger_id,
            WorkflowTrigger.workflow_id == workflow_id
        )
    )
    trigger = result.scalar_one_or_none()
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    await db.delete(trigger)
    await db.commit()
    return Response(status_code=204)


# Event-based workflow triggers
@router.post("/trigger", status_code=202)
async def trigger_workflow_by_event(
    event_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger workflows based on event type.
    Body: { event_type: string, event_data: object, client_id?: string }
    """
    from ...models import WorkflowTrigger, WorkflowDefinition, WorkflowExecution
    import uuid
    
    event_type = event_data.get("event_type")
    event_payload = event_data.get("event_data", {})
    target_client_id = event_data.get("client_id", current_user.client_id)
    
    if not event_type:
        raise HTTPException(status_code=400, detail="event_type is required")
    
    # Find workflows with matching event triggers
    result = await db.execute(
        select(WorkflowTrigger).where(
            WorkflowTrigger.client_id == target_client_id,
            WorkflowTrigger.type == "event",
            WorkflowTrigger.is_active == True,
            WorkflowTrigger.config.op("->>")("event_type") == event_type
        ).options(selectinload(WorkflowTrigger.workflow))
    )
    triggers = result.scalars().all()
    
    executions = []
    for trigger in triggers:
        workflow = trigger.workflow
        if workflow and workflow.status == "published":
            # Check conditions
            conditions_met = True
            for condition in trigger.conditions:
                field = condition.get("field")
                operator = condition.get("operator", "eq")
                expected = condition.get("value")
                actual = _get_nested_value(event_payload, field)
                if not _evaluate_condition(actual, operator, expected):
                    conditions_met = False
                    break
            
            if conditions_met:
                execution = WorkflowExecution(
                    id=uuid.uuid4(),
                    workflow_id=workflow.id,
                    client_id=target_client_id,
                    trigger_type="event",
                    trigger_data=event_payload,
                    trigger_source="event",
                    context={},
                    variables={},
                    status="pending",
                    queued_at=datetime.utcnow(),
                )
                db.add(execution)
                executions.append({
                    "workflow_id": str(workflow.id),
                    "workflow_name": workflow.name,
                    "execution_id": str(execution.id),
                })
    
    await db.commit()
    
    return {
        "message": f"Triggered {len(executions)} workflows",
        "executions": executions,
    }


def _get_nested_value(data: dict, field: str):
    """Get nested value from dict using dot notation."""
    parts = field.split(".")
    value = data
    for part in parts:
        if isinstance(value, dict):
            value = value.get(part)
        else:
            return None
        if value is None:
            return None
    return value


def _evaluate_condition(actual: any, operator: str, expected: any) -> bool:
    if operator == "eq":
        return actual == expected
    elif operator == "neq":
        return actual != expected
    elif operator == "gt":
        return actual > expected
    elif operator == "gte":
        return actual >= expected
    elif operator == "lt":
        return actual < expected
    elif operator == "lte":
        return actual <= expected
    elif operator == "contains":
        return expected in str(actual)
    elif operator == "not_contains":
        return expected not in str(actual)
    elif operator == "in":
        return actual in expected if isinstance(expected, list) else False
    elif operator == "not_in":
        return actual not in expected if isinstance(expected, list) else True
    elif operator == "is_null":
        return actual is None
    elif operator == "not_null":
        return actual is not None
    return False


@router.post("/{workflow_id}/trigger", status_code=202)
async def trigger_specific_workflow(
    workflow_id: str,
    trigger_data: dict = {},
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WorkflowDefinition, WorkflowExecution
    import uuid
    
    result = await db.execute(
        select(WorkflowDefinition).where(
            WorkflowDefinition.id == workflow_id,
            WorkflowDefinition.client_id == current_user.client_id,
            WorkflowDefinition.status == "published"
        )
    )
    workflow = result.scalar_one_or_none()
    if not workflow:
        raise HTTPException(status_code=404, detail="Published workflow not found")
    
    execution = WorkflowExecution(
        id=uuid.uuid4(),
        workflow_id=workflow.id,
        client_id=current_user.client_id,
        trigger_type="api",
        trigger_data=trigger_data,
        trigger_source="api",
        context={},
        variables={},
        status="pending",
        queued_at=datetime.utcnow(),
    )
    db.add(execution)
    await db.commit()
    
    return {"execution_id": str(execution.id), "status": "queued"}