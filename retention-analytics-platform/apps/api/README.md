# Retention Analytics Platform API

The gateway wires every service into workflows and pipelines and exposes them
to the frontend. Run with:

```bash
uv run uvicorn app.main:app --reload --port 8765
```

## Endpoints

- `GET /health` — services + workflows registered
- `GET /api/v1/services` — all registered services + their actions
- `POST /api/v1/services/{service}/actions/{action}` — invoke a service action
- `GET /api/v1/workflows` — registered workflows (pipelines)
- `POST /api/v1/workflows/{id}/run` — run a workflow
- `POST /api/v1/events` — ingest an event (triggers matching workflows)
- `GET|POST /api/v1/entities/{schema_id}` — dynamic entities
- `POST /api/v1/reports` — generate a report
- `GET /api/v1/reports/{id}/download` — download a report

## Example: trigger churn-prevention workflow

The `churn-prevention` workflow is bound to `client.churn_risk`. Ingesting that
event runs: compute retention → send email → send SMS.

```bash
curl -X POST http://localhost:8765/api/v1/events \
  -H 'Content-Type: application/json' \
  -d '{"type":"client.churn_risk","tenant_id":"00000000-0000-0000-0000-000000000001","payload":{"client_email":"a@example.com","client_phone":"+15550000000"}}'
```
