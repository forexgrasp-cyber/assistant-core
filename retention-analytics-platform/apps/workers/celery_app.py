"""Celery worker app: runs workflows and pipelines as background jobs."""

from __future__ import annotations

from celery import Celery

celery_app = Celery(
    "retention_analytics_workers",
    broker="redis://localhost:6379/1",
    backend="redis://localhost:6379/2",
    include=["retention_analytics_workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)


__all__ = ["celery_app"]
