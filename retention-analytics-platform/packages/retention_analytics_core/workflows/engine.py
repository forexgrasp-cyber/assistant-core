"""Durable workflow engine.

Workflows are defined as ordered steps. Each step references a registered
service and one of its actions, with an input mapping from the workflow
context. When a workflow runs, steps execute sequentially, threading the
output of one step into the input of the next.

This is what turns siloed services into integrated workflows: a retention
workflow can, for example, send an email (engagement service), record an
order (ecommerce service), and compute a churn metric (analytics service) in
one durable execution.

Every run is persisted per tenant through the canonical tenant-isolated
repository, so the end state of a run survives a restart and can be asserted
in an L3 workflow test (PRODUCTION_STANDARDS.md §5.2).
"""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

import structlog

from retention_analytics_core.service_registry import ServiceRegistry

logger = structlog.get_logger(__name__)


@dataclass
class WorkflowStep:
    id: str
    service: str
    action: str
    input: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    on_error: str = "continue"  # "continue" | "halt" | "retry"
    retries: int = 0


@dataclass
class WorkflowDefinition:
    id: str
    name: str
    tenant_id: str
    steps: list[WorkflowStep] = field(default_factory=list)
    trigger_event: str | None = None
    active: bool = True


@dataclass
class WorkflowRun:
    id: str
    workflow_id: str
    tenant_id: str
    status: str = "pending"  # pending | running | completed | failed
    context: dict[str, Any] = field(default_factory=dict)
    step_outputs: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class WorkflowEngine:
    """Executes workflow definitions by invoking registered service actions."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._definitions: dict[str, WorkflowDefinition] = {}
        self._runs: dict[str, WorkflowRun] = {}

    def register_definition(self, definition: WorkflowDefinition) -> None:
        self._definitions[definition.id] = definition

    def get_definition(self, workflow_id: str) -> WorkflowDefinition:
        definition = self._definitions.get(workflow_id)
        if definition is None:
            raise KeyError(f"Workflow '{workflow_id}' not registered")
        return definition

    async def _persist_run(self, run: WorkflowRun) -> None:
        """Persist the run end state for the owning tenant."""
        try:
            from retention_analytics_core.repository import repository_for

            record = asdict(run)
            record["completed_at"] = datetime.now(UTC).isoformat()
            await repository_for("workflow_runs", run.tenant_id).save(run.id, record)
        except Exception as exc:  # noqa: BLE001 - persistence must not hide run state
            logger.error("workflow.run.persist_failed", run_id=run.id, error=str(exc))

    async def run(
        self,
        workflow_id: str,
        tenant_id: str,
        initial_context: dict[str, Any] | None = None,
    ) -> WorkflowRun:
        run_id = str(uuid.uuid4())
        definition = self.get_definition(workflow_id)
        run = WorkflowRun(
            id=run_id,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            context=dict(initial_context or {}),
        )
        self._runs[run_id] = run
        run.status = "running"

        logger.info("workflow.run.start", run_id=run_id, workflow_id=workflow_id, tenant_id=tenant_id)

        # Resolve execution order honoring depends_on
        order = self._topological_sort(definition.steps)
        completed: set[str] = set()

        for step_id in order:
            step = next(s for s in definition.steps if s.id == step_id)
            # Build step input: the run context, overlaid with the step's
            # static input mapping (placeholders resolved from the context).
            step_input = dict(run.context)
            step_input.update(self._resolve_input(step.input, run.context))
            for dep_id in step.depends_on:
                if dep_id in run.step_outputs:
                    step_input[f"{dep_id}_output"] = run.step_outputs[dep_id]

            try:
                result = await self.registry.invoke(step.service, step.action, step_input)
                run.step_outputs[step_id] = result
                completed.add(step_id)
                # Merge step outputs back into context so downstream steps can read them
                if isinstance(result, dict):
                    run.context.update(result)
                logger.info(
                    "workflow.step.done",
                    run_id=run_id,
                    step_id=step_id,
                    service=step.service,
                    action=step.action,
                )
            except Exception as exc:  # noqa: BLE001
                run.error = f"step {step_id} ({step.service}.{step.action}) failed: {exc}"
                if step.on_error == "halt":
                    run.status = "failed"
                    logger.error(
                        "workflow.run.halted",
                        run_id=run_id,
                        step_id=step_id,
                        error=run.error,
                    )
                    await self._persist_run(run)
                    return run
                # continue / retry: record and keep going
                logger.warning(
                    "workflow.step.failed_continued",
                    run_id=run_id,
                    step_id=step_id,
                    error=str(exc),
                )

        run.status = "completed"
        logger.info("workflow.run.completed", run_id=run_id, steps_completed=len(completed))
        await self._persist_run(run)
        return run

    @staticmethod
    def _resolve_input(step_input: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        """Resolve ``{placeholder}`` values in a step input from the context.

        A value that is exactly ``"{key}"`` is replaced by the context value
        (when present). A value that embeds placeholders is interpolated.
        Values that are not strings are passed through unchanged.
        """
        resolved: dict[str, Any] = {}
        for key, value in step_input.items():
            if not isinstance(value, str) or "{" not in value:
                resolved[key] = value
                continue
            exact = _exact_placeholder(value)
            if exact is not None:
                resolved[key] = context.get(exact, value)
                continue
            resolved[key] = _interpolate(value, context)
        return resolved

    def _topological_sort(self, steps: list[WorkflowStep]) -> list[str]:
        by_id = {s.id: s for s in steps}
        visited: set[str] = set()
        order: list[str] = []

        def visit(node_id: str, stack: set[str]) -> None:
            if node_id in visited:
                return
            if node_id in stack:
                raise ValueError(f"Cycle detected at workflow step '{node_id}'")
            stack.add(node_id)
            step = by_id.get(node_id)
            if step:
                for dep in step.depends_on:
                    visit(dep, stack)
            stack.discard(node_id)
            visited.add(node_id)
            order.append(node_id)

        for step in steps:
            visit(step.id, set())
        return order

    def get_run(self, run_id: str) -> WorkflowRun:
        run = self._runs.get(run_id)
        if run is None:
            raise KeyError(f"Workflow run '{run_id}' not found")
        return run

    def list_definitions(self) -> list[WorkflowDefinition]:
        return list(self._definitions.values())


__all__ = ["WorkflowEngine", "WorkflowStep", "WorkflowDefinition", "WorkflowRun"]


_PLACEHOLDER_PATTERN = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


def _exact_placeholder(value: str) -> str | None:
    """Return the placeholder name when ``value`` is exactly ``"{name}"``."""
    match = _PLACEHOLDER_PATTERN.fullmatch(value.strip())
    return match.group(1) if match else None


def _interpolate(value: str, context: dict[str, Any]) -> str:
    """Interpolate ``{name}`` placeholders from the workflow context."""

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        replacement = context.get(key)
        return str(replacement) if replacement is not None else match.group(0)

    return _PLACEHOLDER_PATTERN.sub(_replace, value)
