"""
Workflow Execution Engine v2 — Production-grade engine using shared canonical services.

Integrates:
- shared.workflows.WorkflowExecutionService (saga, outbox, idempotency, durable execution)
- shared.workflows.WorkflowScheduler (cron-based triggers)
- shared.base.BaseService (cost tracking, budget, tenant isolation, event emission)

This replaces the legacy workflow_engine.py with a production-ready implementation.
"""

from __future__ import annotations

import asyncio
import structlog
from typing import Any

from shared.workflows.workflow_execution_service import (
    WorkflowExecutionService,
    WorkflowDefinition,
    WorkflowExecution,
    WorkflowExecutionResult,
    StepExecutionResult,
    get_workflow_execution_service,
)
from shared.workflows.workflow_scheduler import WorkflowScheduler, get_workflow_execution_service as get_scheduler
from shared.infrastructure.service_registry import (
    DB_WORKFLOW_SAAS,
    DB_PIPELINE_OUTBOX,
    DB_IDEMPOTENCY,
    DB_CRON_JOBS,
)

logger = structlog.get_logger(__name__)

__version__ = "2026.10.WORKFLOW_ENGINE_V2"


class WorkflowEngineV2:
    """
    Production-grade workflow engine using shared canonical services.

    This engine delegates all execution logic to WorkflowExecutionService
    which provides:
    - Saga-based multi-stage execution with compensation
    - Pipeline outbox for cross-DB transaction safety
    - Durable execution store for crash recovery
    - Idempotency ledger for deduplication
    - At-rest encryption for sensitive config
    - Cost tracking and budget enforcement
    - Tenant isolation
    - Event emission for observability
    """

    def __init__(
        self,
        *,
        tenant_id: str,
        max_budget_usd: float | None = 10.0,
        event_bus: Any | None = None,
        billing: Any | None = None,
        credentials: Any | None = None,
        dry_run: bool = False,
    ):
        self.tenant_id = tenant_id

        # Core execution service
        self._execution_svc = get_workflow_execution_service(
            tenant_id=tenant_id,
            workflow_db_path=DB_WORKFLOW_SAAS,
            outbox_db_path=DB_PIPELINE_OUTBOX,
            idempotency_db_path=DB_IDEMPOTENCY,
            max_budget_usd=max_budget_usd,
            event_bus=event_bus,
            billing=billing,
            credentials=credentials,
            dry_run=dry_run,
        )

        # Scheduler for cron-based triggers
        self._scheduler = WorkflowScheduler(
            tenant_id=tenant_id,
            cron_db_path=DB_CRON_JOBS,
            workflow_db_path=DB_WORKFLOW_SAAS,
            outbox_db_path=DB_PIPELINE_OUTBOX,
            idempotency_db_path=DB_IDEMPOTENCY,
            max_budget_usd=max_budget_usd,
            event_bus=event_bus,
            billing=billing,
            credentials=credentials,
            dry_run=dry_run,
        )

    # =========================================================================
    # Lifecycle
    # =========================================================================

    async def start(self):
        """Start scheduler background task."""
        await self._scheduler.start()
        logger.info("workflow_engine_v2.started", tenant_id=self.tenant_id)

    async def stop(self):
        """Stop scheduler gracefully."""
        await self._scheduler.stop()
        logger.info("workflow_engine_v2.stopped", tenant_id=self.tenant_id)

    # =========================================================================
    # Workflow CRUD
    # =========================================================================

    async def create_workflow(
        self,
        name: str,
        steps: list[dict[str, Any]],
        triggers: list[dict[str, Any]] | None = None,
        settings: dict[str, Any] | None = None,
        description: str = "",
    ) -> WorkflowDefinition:
        """Create new workflow definition."""
        result = await self._execution_svc.create_workflow(
            name=name,
            steps=steps,
            triggers=triggers,
            settings=settings,
            description=description,
        )
        if not result.success:
            raise ValueError(result.error)
        return result.data

    async def get_workflow(self, workflow_id: str) -> WorkflowDefinition | None:
        """Get workflow by ID."""
        return await self._execution_svc.get_workflow(workflow_id)

    async def update_workflow(
        self,
        workflow_id: str,
        updates: dict[str, Any],
    ) -> WorkflowDefinition:
        """Update workflow definition."""
        result = await self._execution_svc.update_workflow(workflow_id, updates)
        if not result.success:
            raise ValueError(result.error)
        return result.data

    async def publish_workflow(self, workflow_id: str) -> WorkflowDefinition:
        """Publish workflow (make executable)."""
        result = await self._execution_svc.publish_workflow(workflow_id)
        if not result.success:
            raise ValueError(result.error)
        return result.data

    async def list_workflows(self, status: str | None = None) -> list[WorkflowDefinition]:
        """List workflows for tenant."""
        result = await self._execution_svc.list_workflows(status=status)
        if not result.success:
            raise ValueError(result.error)
        return result.data

    # =========================================================================
    # Execution
    # =========================================================================

    async def execute_workflow(
        self,
        workflow_id: str,
        trigger_data: dict[str, Any],
        trigger_source: str = "api",
        trigger_type: str = "api",
    ) -> WorkflowExecutionResult:
        """
        Execute a workflow.

        Returns WorkflowExecutionResult with step results, duration, success status.
        """
        result = await self._execution_svc.execute_workflow(
            workflow_id=workflow_id,
            trigger_data=trigger_data,
            trigger_source=trigger_source,
            trigger_type=trigger_type,
        )
        if not result.success:
            raise RuntimeError(f"Workflow execution failed: {result.error}")
        return result.data

    async def trigger_by_event(
        self,
        event_type: str,
        event_data: dict[str, Any],
    ) -> list[WorkflowExecutionResult]:
        """
        Trigger workflows by event type.

        Finds all published workflows with matching event triggers
        and executes them if conditions are met.
        """
        result = await self._execution_svc.trigger_by_event(event_type, event_data)
        if not result.success:
            raise RuntimeError(f"Event trigger failed: {result.error}")
        return result.data

    async def get_execution(self, execution_id: str) -> WorkflowExecution | None:
        """Get execution by ID."""
        return await self._execution_svc.get_execution(execution_id)

    async def list_executions(
        self,
        workflow_id: str | None = None,
        status: str | None = None,
    ) -> list[WorkflowExecution]:
        """List executions for tenant."""
        result = await self._execution_svc.list_executions(workflow_id=workflow_id, status=status)
        if not result.success:
            raise ValueError(result.error)
        return result.data

    async def cancel_execution(self, execution_id: str) -> bool:
        """Cancel a running execution."""
        result = await self._execution_svc.cancel_execution(execution_id)
        if not result.success:
            raise ValueError(result.error)
        return result.data

    # =========================================================================
    # Schedule Management
    # =========================================================================

    def schedule_workflow(
        self,
        workflow_id: str,
        schedule_type: str,
        cron_expression: str | None = None,
        interval_seconds: int | None = None,
        run_at: str | None = None,
        timezone: str = "UTC",
        name: str = "",
        max_runs: int = 0,
        payload: dict | None = None,
    ) -> dict:
        """Create a schedule for a workflow."""
        result = self._scheduler.schedule_workflow(
            workflow_id=workflow_id,
            schedule_type=schedule_type,
            cron_expression=cron_expression,
            interval_seconds=interval_seconds,
            run_at=run_at,
            timezone=timezone,
            name=name,
            max_runs=max_runs,
            payload=payload,
        )
        if not result.success:
            raise ValueError(result.error)
        return result.data

    def get_schedules(self, workflow_id: str | None = None, status: str | None = None) -> list[dict]:
        """Get schedules for tenant."""
        result = self._scheduler.get_schedules(workflow_id=workflow_id, status=status)
        if not result.success:
            raise ValueError(result.error)
        return result.data

    def pause_schedule(self, schedule_id: str) -> dict | None:
        """Pause a schedule."""
        result = self._scheduler.pause_schedule(schedule_id)
        if not result.success:
            raise ValueError(result.error)
        return result.data

    def resume_schedule(self, schedule_id: str) -> dict | None:
        """Resume a paused schedule."""
        result = self._scheduler.resume_schedule(schedule_id)
        if not result.success:
            raise ValueError(result.error)
        return result.data

    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a schedule."""
        result = self._scheduler.delete_schedule(schedule_id)
        if not result.success:
            raise ValueError(result.error)
        return result.data

    def get_run_history(self, schedule_id: str, limit: int = 50) -> list[dict]:
        """Get run history for a schedule."""
        result = self._scheduler.get_run_history(schedule_id, limit)
        if not result.success:
            raise ValueError(result.error)
        return result.data

    # =========================================================================
    # Health / Maintenance
    # =========================================================================

    def health(self) -> dict:
        """Combined health check."""
        return {
            "execution_service": self._execution_svc.health(),
            "scheduler": self._scheduler.health(),
        }

    def cleanup_old_data(self, max_age_hours: int = 168) -> dict[str, int]:
        """Clean up old idempotency keys and completed outbox entries."""
        return self._execution_svc.cleanup_old_data(max_age_hours)


# ─────────────────────────────────────────────────────────────────────────────
# Factory / Dependency Injection
# ─────────────────────────────────────────────────────────────────────────────


_engine_instances: dict[str, WorkflowEngineV2] = {}


def get_workflow_engine(tenant_id: str, **kwargs) -> WorkflowEngineV2:
    """Get or create workflow engine for tenant."""
    if tenant_id not in _engine_instances:
        _engine_instances[tenant_id] = WorkflowEngineV2(tenant_id=tenant_id, **kwargs)
    return _engine_instances[tenant_id]


async def startup_workflow_engine(tenant_id: str, **kwargs) -> WorkflowEngineV2:
    """Initialize and start workflow engine for tenant."""
    engine = get_workflow_engine(tenant_id, **kwargs)
    await engine.start()
    return engine


async def shutdown_workflow_engine(tenant_id: str):
    """Shutdown workflow engine for tenant."""
    if tenant_id in _engine_instances:
        await _engine_instances[tenant_id].stop()
        del _engine_instances[tenant_id]


__all__ = [
    "WorkflowEngineV2",
    "get_workflow_engine",
    "startup_workflow_engine",
    "shutdown_workflow_engine",
]