"""Worker tasks: background execution of workflows and pipelines.

The worker consumes events and scheduled jobs, running workflows via the
WorkflowEngine. This keeps the API responsive while retention workflows
(email + SMS + metric + report) run durably in the background.
"""

from __future__ import annotations

import asyncio

from apps.workers.celery_app import celery_app


def _run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# The platform instance is shared with the API process in dev via the registry
# imported from apps.api.main. In production these run in separate containers
# and communicate over Redis streams / the shared database.
from apps.api.main import engine, trigger_service  # noqa: E402


@celery_app.task(name="workflows.run")
def run_workflow_task(workflow_id: str, tenant_id: str, context: dict | None = None):
    return _run_async(engine.run(workflow_id, tenant_id, initial_context=context or {}))


@celery_app.task(name="events.ingest")
def ingest_event_task(event_type: str, tenant_id: str, payload: dict):

    async def _go():
        from retention_analytics_shared_types import EventType
        try:
            et = EventType(event_type)
        except ValueError:
            et = EventType.CLIENT_UPDATED
        await trigger_service.handle_event(et, tenant_id, payload)
        return {"status": "accepted", "event_type": event_type}

    return _run_async(_go())


@celery_app.task(name="reports.generate")
def generate_report_task(tenant_id: str, name: str, fmt: str = "pdf"):
    from apps.api.main import registry

    return _run_async(
        registry.invoke("reporting.engine", "generate_report", {"tenant_id": tenant_id, "name": name, "format": fmt})
    )


@celery_app.task(name="reports.run_scheduled")
def run_scheduled_reports_task(tenant_id: str):
    """Cron tick: run all due scheduled reports and email them (Baremetrics Email Reports)."""
    from apps.api.main import registry

    return _run_async(registry.invoke("reports.scheduler", "run_due", {"tenant_id": tenant_id}))


@celery_app.task(name="service_due.scan")
def scan_service_due_task(tenant_id: str, within_days: int = 7):
    """Cron tick: scan customer records for services due/overdue and schedule reminders."""
    from apps.api.main import registry

    return _run_async(
        registry.invoke("customers.service_due", "schedule_reminders", {"tenant_id": tenant_id, "within_days": within_days})
    )


@celery_app.task(name="agency.run_due_digests")
def run_due_digests_task(tenant_id: str):
    """Cron tick: run all due scheduled agency digests and send to Slack (Hiro parity)."""
    from apps.api.main import registry

    return _run_async(registry.invoke("agency", "run_due_digests", {"tenant_id": tenant_id}))


__all__ = ["run_workflow_task", "ingest_event_task", "generate_report_task", "run_scheduled_reports_task", "scan_service_due_task", "run_due_digests_task"]
