"""API gateway for the retention analytics platform.

Security and correctness rules enforced here (PRODUCTION_STANDARDS.md §5-§7):

* the tenant a request acts on is derived from the authenticated principal
  (:mod:`retention_analytics_core.tenancy`); a tenant supplied by the client
  never widens access;
* mutating endpoints are written to the canonical hash-chained audit log;
* event ingestion is idempotent through the canonical idempotency ledger, so
  a retried webhook never double-processes;
* webhook signatures are verified before any payload is processed;
* outbound requests use the canonical resilient HTTP client, inbound requests
  are rate limited by the canonical sliding-window limiter;
* responses carry correlation IDs and the canonical security headers.
"""

from __future__ import annotations

import hmac
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from hashlib import sha256
from typing import Annotated, Any
from uuid import UUID

import structlog
from fastapi import Body, Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pydantic import AliasChoices, BaseModel, Field
from retention_analytics_analytics_core.cohort_service import CohortService
from retention_analytics_analytics_core.metric_service import MetricService
from retention_analytics_core.auth import CurrentUser, get_current_user
from retention_analytics_core.canonical import get_adapters
from retention_analytics_core.database import get_engine, get_session, get_session_factory
from retention_analytics_core.entities.kernel import (
    EntityKernel,
    EntityRecord,
)
from retention_analytics_core.middleware import (
    CorrelationIdMiddleware,
    RateLimitMiddleware,
    TenantContextMiddleware,
    TracingMiddleware,
    get_metrics_prometheus,
)
from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_core.tenancy import DEFAULT_TENANT, resolve_tenant
from retention_analytics_core.workflows.engine import WorkflowEngine, WorkflowRun
from retention_analytics_ecommerce.core.service import EcommerceCoreService
from retention_analytics_ecommerce.payments.service import PaymentService
from retention_analytics_ecommerce.subscriptions.service import SubscriptionService
from retention_analytics_engagement.email.service import EmailService
from retention_analytics_engagement.flows.triggers import FlowTriggerService
from retention_analytics_engagement.push.service import PushService
from retention_analytics_engagement.sms.service import SmsService
from retention_analytics_reporting_engine.report_service import ReportService
from retention_analytics_shared_config import get_settings
from retention_analytics_shared_types import EventType
from retention_analytics_templates.service import TemplateService
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.trustedhost import TrustedHostMiddleware

from apps.api.workflows_seed import build_workflows, workflow_event_bindings

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Registry / engine wiring
# ---------------------------------------------------------------------------

registry = ServiceRegistry()
engine = WorkflowEngine(registry)

email_service = EmailService(registry)
sms_service = SmsService(registry)
push_service = PushService(registry)
subscription_service = SubscriptionService(registry)
ecommerce_service = EcommerceCoreService(registry)
payment_service = PaymentService(registry)
metric_service = MetricService(registry)
cohort_service = CohortService(registry)
report_service = ReportService(registry)
template_service = TemplateService(registry)

for _service in (
    email_service,
    sms_service,
    push_service,
    subscription_service,
    ecommerce_service,
    payment_service,
    metric_service,
    cohort_service,
    report_service,
):
    _service.register()

# The template service registers itself with the registry on construction.
trigger_service = FlowTriggerService(registry, engine)

for _definition in build_workflows():
    engine.register_definition(_definition)

# Bind platform events to the workflows they trigger.
for _event_name, _workflow_ids in workflow_event_bindings().items():
    try:
        _event_type = EventType(_event_name)
    except ValueError:
        logger.warning("workflow.event_binding.unknown", event=_event_name)
        continue
    for _workflow_id in _workflow_ids:
        trigger_service.bind(_event_type, _workflow_id)


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start-up / shut-down hooks."""
    settings = get_settings()
    get_engine()
    get_session_factory()
    logger.info(
        "api.startup",
        environment=settings.environment,
        services=len(registry.list_services()),
        workflows=len(engine.list_definitions()),
    )
    yield
    engine_instance = get_engine()
    await engine_instance.dispose()
    logger.info("api.shutdown")


app = FastAPI(
    title="Retention Analytics Platform API",
    version="0.1.0",
    lifespan=lifespan,
)

settings = get_settings()

# ---------------------------------------------------------------------------
# Middleware (order matters: outermost first)
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Tenant-Id", "X-Correlation-Id", "X-Idempotency-Key"],
)
if settings.allowed_host_list:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_host_list)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(TracingMiddleware)
app.add_middleware(TenantContextMiddleware)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.rate_limit_per_minute,
)


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})


@app.exception_handler(PermissionError)
async def permission_error_handler(request: Request, exc: PermissionError) -> JSONResponse:
    return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content={"detail": str(exc)})


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class EntityCreateRequest(BaseModel):
    schema_id: str
    data: dict[str, Any] = Field(default_factory=dict)


class EntityUpdateRequest(BaseModel):
    schema_id: str
    record_id: str
    data: dict[str, Any] = Field(default_factory=dict)


class EventIngestRequest(BaseModel):
    event_type: str = Field(validation_alias=AliasChoices("event_type", "type"))
    payload: dict[str, Any] = Field(default_factory=dict)
    tenant_id: str | None = None
    idempotency_key: str | None = None


class WorkflowRunRequest(BaseModel):
    context: dict[str, Any] = Field(default_factory=dict)
    tenant_id: str | None = None


class ServiceInvokeRequest(BaseModel):
    payload: dict[str, Any] = Field(default_factory=dict)
    tenant_id: str | None = None


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def current_tenant(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> str:
    """Resolve the tenant the request may act on."""
    return resolve_tenant(
        user.tenant_id,
        requested_tenant_id=None,
        header_tenant_id=request.headers.get("x-tenant-id"),
    )


def request_tenant(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    requested_tenant_id: str | None = None,
) -> str:
    """Resolve the tenant for a request whose body may carry a tenant id."""
    return resolve_tenant(
        user.tenant_id,
        requested_tenant_id=requested_tenant_id,
        header_tenant_id=request.headers.get("x-tenant-id"),
    )


# ---------------------------------------------------------------------------
# Health / observability
# ---------------------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, Any]:
    """Liveness probe."""
    return {
        "status": "ok",
        "service": "retention-analytics-platform",
        "version": app.version,
        "environment": get_settings().environment,
        "services": registry.list_services(),
        "workflows": [d.name for d in engine.list_definitions()],
    }


@app.get("/health/ready")
async def health_ready(response: Response) -> dict[str, Any]:
    """Readiness probe with dependency checks."""
    adapters = get_adapters()
    result = await adapters.health.check_readiness()
    if result.get("status") != "healthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return result


@app.get("/health/live")
async def health_live() -> dict[str, Any]:
    return await get_adapters().health.check_liveness()


@app.get("/api/v1/health")
async def api_health() -> dict[str, Any]:
    """Frontend-facing health endpoint (same payload as ``/health``)."""
    return await health()


@app.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=get_metrics_prometheus(), media_type="text/plain; version=0.0.4")


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------


@app.post("/api/v1/entities/{schema_id}")
async def create_entity(
    schema_id: str,
    body: EntityCreateRequest,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """Create an entity record for the authenticated tenant."""
    tenant_id = current_tenant(request, user)
    kernel = EntityKernel(session)
    record = await kernel.create_record(schema_id, tenant_id, body.data)
    await session.commit()
    _audit(
        event_type="entity.created",
        user=user,
        tenant_id=tenant_id,
        resource_type="entity_record",
        resource_id=str(record.id),
        action="create",
        details={"schema_id": schema_id},
    )
    return {"status": "created", "record": _record_payload(record)}


@app.get("/api/v1/entities/{schema_id}")
async def list_entities(
    schema_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    """List entity records belonging to the authenticated tenant."""
    tenant_id = current_tenant(request, user)
    kernel = EntityKernel(session)
    records = await kernel.list_records(schema_id, tenant_id)
    return {
        "status": "ok",
        "schema_id": schema_id,
        "tenant_id": tenant_id,
        "count": len(records),
        "records": [_record_payload(record) for record in records],
    }


@app.get("/api/v1/entities/{schema_id}/{record_id}")
async def get_entity(
    schema_id: str,
    record_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    kernel = EntityKernel(session)
    try:
        record = await kernel.get_record(schema_id, _as_uuid(record_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Record not found") from exc
    if record.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Record not found")
    return {"status": "ok", "record": _record_payload(record)}


@app.patch("/api/v1/entities/{schema_id}/{record_id}")
async def update_entity(
    schema_id: str,
    record_id: str,
    body: EntityUpdateRequest,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    kernel = EntityKernel(session)
    try:
        record = await kernel.get_record(schema_id, _as_uuid(record_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Record not found") from exc
    if record.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Record not found")
    updated = await kernel.update_record(schema_id, record.id, body.data)
    await session.commit()
    _audit(
        event_type="entity.updated",
        user=user,
        tenant_id=tenant_id,
        resource_type="entity_record",
        resource_id=str(record.id),
        action="update",
        details={"schema_id": schema_id},
    )
    return {"status": "updated", "record": _record_payload(updated)}


@app.delete("/api/v1/entities/{schema_id}/{record_id}")
async def delete_entity(
    schema_id: str,
    record_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    kernel = EntityKernel(session)
    try:
        record = await kernel.get_record(schema_id, _as_uuid(record_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Record not found") from exc
    if record.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Record not found")
    await kernel.delete_record(schema_id, record.id)
    await session.commit()
    _audit(
        event_type="entity.deleted",
        user=user,
        tenant_id=tenant_id,
        resource_type="entity_record",
        resource_id=str(record.id),
        action="delete",
        details={"schema_id": schema_id},
    )
    return {"status": "deleted", "record_id": str(record.id)}

# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


@app.post("/api/v1/events")
async def ingest_event(
    body: EventIngestRequest,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Ingest a platform event and trigger the matching workflows.

    The request is idempotent: replaying the same idempotency key returns the
    original result instead of processing the event twice.
    """
    tenant_id = request_tenant(request, user, body.tenant_id)

    try:
        event_type = EventType(body.event_type)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"unknown event type '{body.event_type}'") from exc

    adapters = get_adapters()
    key = body.idempotency_key or request.headers.get("x-idempotency-key")
    ledger_key = adapters.idempotency.build_key(
        "event", tenant_id, str(event_type), key or sha256(
            json.dumps(body.payload, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest()
    )

    claimed, prior = adapters.idempotency.claim(ledger_key, tenant_id)
    if not claimed:
        if prior is not None:
            return {**prior, "idempotent_replay": True}
        raise HTTPException(status_code=409, detail="event already being processed")

    result: dict[str, Any] = {
        "status": "accepted",
        "event_type": str(event_type),
        "tenant_id": tenant_id,
        "received_at": datetime.now(UTC).isoformat(),
    }
    try:
        await trigger_service.handle_event(event_type, tenant_id, body.payload)
    except Exception as exc:  # noqa: BLE001
        adapters.idempotency.release(ledger_key)
        logger.error("event.ingest_failed", event_type=str(event_type), error=str(exc))
        raise HTTPException(status_code=500, detail="event processing failed") from exc

    adapters.idempotency.complete(ledger_key, result)
    _audit(
        event_type="event.ingested",
        user=user,
        tenant_id=tenant_id,
        resource_type="event",
        resource_id=ledger_key,
        action="ingest",
        details={"event_type": str(event_type)},
    )
    return result


@app.post("/api/v1/webhooks/{provider}")
async def receive_webhook(
    provider: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Receive a provider webhook.

    The signature is verified *before* the payload is processed, and the
    delivery is idempotent per provider event id.
    """
    raw_body = await request.body()
    signature = request.headers.get("x-signature") or request.headers.get(
        "x-webhook-signature", ""
    )
    if not _verify_webhook_signature(provider, raw_body, signature):
        raise HTTPException(status_code=401, detail="invalid webhook signature")

    try:
        payload = json.loads(raw_body or b"{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid JSON payload") from exc

    tenant_id = current_tenant(request, user)
    adapters = get_adapters()
    event_id = str(payload.get("id") or payload.get("event_id") or sha256(raw_body).hexdigest()[:16])
    ledger_key = adapters.idempotency.build_key("webhook", provider, tenant_id, event_id)

    claimed, prior = adapters.idempotency.claim(ledger_key, tenant_id)
    if not claimed:
        if prior is not None:
            return {**prior, "idempotent_replay": True}
        raise HTTPException(status_code=409, detail="webhook already being processed")

    result = {
        "status": "accepted",
        "provider": provider,
        "event_id": event_id,
        "tenant_id": tenant_id,
        "received_at": datetime.now(UTC).isoformat(),
    }
    adapters.idempotency.complete(ledger_key, result)
    _audit(
        event_type="webhook.received",
        user=user,
        tenant_id=tenant_id,
        resource_type="webhook",
        resource_id=event_id,
        action="receive",
        details={"provider": provider},
    )
    return result


def _verify_webhook_signature(provider: str, raw_body: bytes, signature: str) -> bool:
    """Verify a webhook signature using the configured provider secret.

    Development without a configured secret accepts the delivery; production
    always fails closed because no secret means the signature cannot be
    trusted.
    """
    current_settings = get_settings()
    secret = current_settings.webhook_secret
    if not secret:
        if current_settings.is_production:
            logger.error("webhook.signature.missing_secret", provider=provider)
            return False
        return True

    if not signature:
        return False

    expected = hmac.new(secret.encode("utf-8"), raw_body, sha256).hexdigest()
    provided = signature.split("=", 1)[-1].strip()
    return hmac.compare_digest(expected, provided)


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------


@app.get("/api/v1/services")
async def list_services() -> dict[str, Any]:
    services = []
    for name in registry.list_services():
        registration = registry.get(name)
        services.append(
            {
                "name": registration.name,
                "version": registration.version,
                "actions": sorted(registration.actions.keys()),
                "subscribes_to": [str(event) for event in registration.subscribes_to],
                "metadata": registration.metadata,
            }
        )
    return {"status": "ok", "services": services, "count": len(services)}


@app.post("/api/v1/services/{service_name}/actions/{action_name}")
async def invoke_service(
    service_name: str,
    action_name: str,
    body: ServiceInvokeRequest,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Invoke a registered service action for the authenticated tenant."""
    tenant_id = request_tenant(request, user, body.tenant_id)
    payload = {**body.payload, "tenant_id": tenant_id}
    try:
        result = await registry.invoke(service_name, action_name, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("service.invoke_failed", service=service_name, action=action_name, error=str(exc))
        raise HTTPException(status_code=500, detail="service action failed") from exc

    _audit(
        event_type="service.invoked",
        user=user,
        tenant_id=tenant_id,
        resource_type="service_action",
        resource_id=f"{service_name}.{action_name}",
        action="invoke",
        details={"payload_keys": sorted(body.payload.keys())},
    )
    return {
        "status": result.get("status", "ok"),
        "service": service_name,
        "action": action_name,
        "result": result,
    }


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------


@app.get("/api/v1/workflows")
async def list_workflows() -> dict[str, Any]:
    workflows = []
    for definition in engine.list_definitions():
        workflows.append(
            {
                "id": definition.id,
                "name": definition.name,
                "tenant_id": definition.tenant_id,
                "steps": [
                    {"id": step.id, "service": step.service, "action": step.action}
                    for step in definition.steps
                ],
                "trigger_event": definition.trigger_event,
                "active": definition.active,
            }
        )
    return {"status": "ok", "workflows": workflows, "count": len(workflows)}


@app.post("/api/v1/workflows/{workflow_id}/run")
async def run_workflow(
    workflow_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: WorkflowRunRequest = Body(default_factory=WorkflowRunRequest),
) -> dict[str, Any]:
    tenant_id = request_tenant(request, user, body.tenant_id)
    try:
        run = await engine.run(workflow_id, tenant_id, initial_context=body.context)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.error("workflow.run_failed", workflow_id=workflow_id, error=str(exc))
        raise HTTPException(status_code=500, detail="workflow execution failed") from exc

    _audit(
        event_type="workflow.run",
        user=user,
        tenant_id=tenant_id,
        resource_type="workflow_run",
        resource_id=run.id,
        action="run",
        details={"workflow_id": workflow_id, "status": run.status},
    )
    return {"status": run.status, "run": _run_payload(run)}


@app.get("/api/v1/workflows/runs/{run_id}")
async def get_workflow_run(
    run_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    try:
        run = engine.get_run(run_id)
    except KeyError:
        from retention_analytics_core.repository import repository_for

        record = await repository_for("workflow_runs", tenant_id).load(run_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Workflow run not found") from None
        return {"status": "ok", "run": record}
    if run.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Workflow run not found")
    return {"status": "ok", "run": _run_payload(run)}


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


@app.post("/api/v1/reports")
async def generate_report(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    name: str | None = None,
    format: str = "html",
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    result = await registry.invoke(
        "reporting.engine",
        "generate_report",
        {"tenant_id": tenant_id, "name": name or "Retention Report", "format": format},
    )
    if result.get("success") is False:
        raise HTTPException(status_code=422, detail=str(result.get("error")))
    return result


@app.get("/api/v1/reports/{report_id}/download")
async def download_report(
    report_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> Response:
    tenant_id = current_tenant(request, user)
    result = await registry.invoke(
        "reporting.engine",
        "download_report",
        {"tenant_id": tenant_id, "report_id": report_id},
    )
    if result.get("success") is False:
        raise HTTPException(status_code=404, detail=str(result.get("error")))
    from pathlib import Path

    path = Path(result["path"])
    if not path.is_file():
        raise HTTPException(status_code=404, detail="report artifact is missing")
    return Response(
        content=path.read_bytes(),
        media_type=result.get("content_type", "application/octet-stream"),
        headers={"Content-Disposition": f'attachment; filename="{report_id}{path.suffix}"'},
    )


# ---------------------------------------------------------------------------
# Billing
# ---------------------------------------------------------------------------


@app.get("/api/v1/payments/providers")
async def list_payment_providers(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    result = await registry.invoke("payments", "list_providers", {"tenant_id": user.tenant_id})
    return result


@app.post("/api/v1/payments")
async def create_payment(
    body: ServiceInvokeRequest,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = request_tenant(request, user, body.tenant_id)
    result = await registry.invoke(
        "payments", "create_payment", {**body.payload, "tenant_id": tenant_id}
    )
    if result.get("success") is False:
        raise HTTPException(status_code=422, detail=str(result.get("error")))
    _audit(
        event_type="payment.created",
        user=user,
        tenant_id=tenant_id,
        resource_type="payment",
        resource_id=str(result.get("payment_id", "")),
        action="create",
        details={"amount": body.payload.get("amount")},
    )
    return result


@app.get("/api/v1/entitlements")
async def list_entitlements(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """List the entitlements granted to the authenticated tenant."""
    from retention_analytics_core.repository import data_root
    from shared.billing.entitlements_service import EntitlementsService

    service = EntitlementsService(str(data_root() / "billing" / "entitlements.db"))
    return {
        "status": "ok",
        "account": user.tenant_id,
        "entitlements": service.list_active(account=user.tenant_id),
    }


# ---------------------------------------------------------------------------
# SEO / surfaces
# ---------------------------------------------------------------------------


@app.get("/robots.txt", include_in_schema=False)
async def robots_txt() -> Response:
    return Response(
        content="User-agent: *\nAllow: /\nDisallow: /api/\n",
        media_type="text/plain",
    )


@app.get("/sitemap.xml", include_in_schema=False)
async def sitemap_xml() -> Response:
    base = get_settings().allowed_hosts.split(",")[0] if get_settings().allowed_hosts else ""
    urls = ["/", "/api/v1/health", "/api/v1/services", "/api/v1/workflows"]
    body = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">"
    for url in urls:
        location = f"https://{base}{url}" if base else url
        body += f"<url><loc>{location}</loc></url>"
    body += "</urlset>"
    return Response(content=body, media_type="application/xml")


@app.get("/llms.txt", include_in_schema=False)
async def llms_txt() -> Response:
    return Response(
        content=(
            "# Retention Analytics Platform\n\n"
            "Multi-tenant retention analytics API: roster, retention, RFM and cohort "
            "metrics driven by workflows that send email, SMS and push messages.\n\n"
            "## Surfaces\n"
            "- POST /api/v1/events - ingest a platform event\n"
            "- GET /api/v1/workflows - list retention workflows\n"
            "- POST /api/v1/reports - generate a retention report\n"
        ),
        media_type="text/plain",
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _kernel(request: Request) -> EntityKernel:
    """Return an entity kernel bound to the request's database session."""
    session = getattr(request.app.state, "db_session", None)
    if session is None:
        raise HTTPException(status_code=503, detail="database session unavailable")
    return EntityKernel(session)


async def _commit(request: Request) -> None:
    session = getattr(request.app.state, "db_session", None)
    if session is not None:
        await session.commit()


def _audit(
    *,
    event_type: str,
    user: CurrentUser,
    tenant_id: str,
    resource_type: str,
    resource_id: str,
    action: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Write a hash-chained audit entry; never breaks the request."""
    try:
        get_adapters().audit.record(
            event_type=event_type,
            actor_id=user.user_id,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            details=details or {},
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("audit.write_failed", event_type=event_type, error=str(exc))


def _record_payload(record: EntityRecord) -> dict[str, Any]:
    return {
        "id": str(record.id),
        "schema_id": record.schema_id,
        "tenant_id": record.tenant_id,
        "data": record.data,
    }


def _as_uuid(value: str) -> UUID:
    """Parse a record id, rejecting malformed input with 404."""
    try:
        return UUID(str(value))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Record not found") from exc


def _run_payload(run: WorkflowRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "workflow_id": run.workflow_id,
        "tenant_id": run.tenant_id,
        "status": run.status,
        "context": run.context,
        "step_outputs": run.step_outputs,
        "error": run.error,
    }


__all__ = ["app", "engine", "registry", "trigger_service", "DEFAULT_TENANT"]
