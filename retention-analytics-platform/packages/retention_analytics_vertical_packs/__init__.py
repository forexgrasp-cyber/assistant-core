"""Vertical pack base module.

Each vertical pack exports domain-specific entity schemas, workflow
definitions, and reports, plus a ``register`` function that wires them into
the platform ``ServiceRegistry`` and ``WorkflowEngine``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from retention_analytics_core.entities.kernel import EntityKernel, EntitySchema
from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_core.workflows.engine import WorkflowDefinition, WorkflowEngine

TENANT_ID = "00000000-0000-0000-0000-000000000001"


@dataclass
class VerticalPack:
    id: str
    name: str
    description: str
    schemas: list[EntitySchema] = field(default_factory=list)
    workflows: list[WorkflowDefinition] = field(default_factory=list)
    reports: list[dict[str, Any]] = field(default_factory=list)

    def register(self, registry: ServiceRegistry, engine: WorkflowEngine, kernel: EntityKernel) -> None:
        for schema in self.schemas:
            kernel.register_schema(schema)
        for wf in self.workflows:
            engine.register_definition(wf)


__all__ = ["VerticalPack", "TENANT_ID"]
