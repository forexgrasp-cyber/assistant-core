"""Flow trigger service.

Maps platform events to workflow triggers and subscribes to events so that an
event (e.g. client.churn_risk) automatically starts the configured workflow.
This bridges events → workflows → services.
"""

from __future__ import annotations

from typing import Any

import structlog
from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_core.workflows.engine import WorkflowEngine
from retention_analytics_shared_types import EventType

logger = structlog.get_logger(__name__)


class FlowTriggerService:
    """Subscribes to platform events and launches matching workflows."""

    def __init__(self, registry: ServiceRegistry, engine: WorkflowEngine) -> None:
        self.registry = registry
        self.engine = engine
        # event_type -> list of workflow_ids to trigger
        self._event_workflow_map: dict[EventType, list[str]] = {}

    def bind(self, event_type: EventType, workflow_id: str) -> None:
        self._event_workflow_map.setdefault(event_type, []).append(workflow_id)

    async def handle_event(self, event_type: EventType, tenant_id: str, payload: dict[str, Any]) -> None:
        # Merge the flat payload and a nested "event" key so that placeholders
        # like {email} resolve from either flat keys or a nested "event" dict.
        flat = dict(payload)
        event = payload.get("event")
        if isinstance(event, dict):
            flat.update(event)
        # Bind to every workflow that cares about this event type.
        workflow_ids = self._event_workflow_map.get(event_type, [])
        for workflow_id in workflow_ids:
            try:
                await self.engine.run(workflow_id, tenant_id, initial_context=flat)
                logger.info("flow.triggered", event_type=event_type, workflow_id=workflow_id, tenant_id=tenant_id)
            except Exception as exc:  # noqa: BLE001
                logger.error("flow.trigger.failed", event_type=event_type, workflow_id=workflow_id, error=str(exc))

    @property
    def subscriptions(self) -> list[EventType]:
        return list(self._event_workflow_map.keys())


__all__ = ["FlowTriggerService"]
