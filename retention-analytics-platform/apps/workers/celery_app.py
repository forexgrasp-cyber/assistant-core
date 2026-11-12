"""Celery worker app: runs workflows and pipelines as background jobs."""

from __future__ import annotations

from celery import Celery

from retention_analytics_shared_config import get_settings

_settings = get_settings()

celery_app = Celery(
    "retention_analytics_workers",
    broker=_settings.celery_broker_url,
    backend=_settings.celery_result_backend,
    include=["apps.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    broker_connection_retry_on_startup=True,
    beat_schedule={
        # Run due scheduled reports every hour (Baremetrics Email Reports)
        "reports-scheduled-hourly": {
            "task": "reports.run_scheduled",
            "schedule": 3600.0,
            "args": ("00000000-0000-0000-0000-000000000001",),
        },
        # Scan for service-due customers every morning
        "service-due-daily": {
            "task": "service_due.scan",
            "schedule": 86400.0,
            "args": ("00000000-0000-0000-0000-000000000001", 7),
        },
    },
)


__all__ = ["celery_app"]
