# Workers

Celery worker app that runs workflows and pipelines in the background.

```bash
celery -A apps.workers.celery_app worker --loglevel=info
```

Tasks:
- `workflows.run` — execute a workflow definition
- `events.ingest` — ingest an event and trigger matching workflows
- `reports.generate` — generate a report in the background
