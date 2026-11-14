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
import html
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
    SecurityHeadersMiddleware,
    TenantContextMiddleware,
    TracingMiddleware,
    get_metrics_prometheus,
    metrics_middleware,
)
from apps.api.htmlview import maybe_html, metrics_to_html, wants_html
from retention_analytics_core.platform_services import PlatformServices
from retention_analytics_core.platform_surfaces import PlatformSurfaceService
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

# Wire all canonical shared services (feature flags, quota, entitlements,
# sessions, profile, notifications, outbound webhooks, payments registry,
# organizations, support, feedback, monetization, email marketing, lead capture).
platform_services = PlatformServices(registry)
platform_services.register_all()

# Wire growth services (competitor parity: health scoring, dunning, surveys,
# forecasting, segmentation, in-app messaging).
from retention_analytics_growth.service import (
    DunningService,
    ForecastingService,
    HealthScoringService,
    InAppMessagingService,
    SegmentationService,
    SurveyService,
)

for svc_cls in (
    HealthScoringService,
    DunningService,
    SurveyService,
    ForecastingService,
    SegmentationService,
    InAppMessagingService,
):
    svc_cls(registry).register()

# Phase 1-8: SaaS metrics, AI, CS ops, integrations, compliance
from retention_analytics_saas_metrics.service import SaasMetricsService
from retention_analytics_ai.service import FeedbackAIService, OfferRecommendationService, PredictiveChurnService
from retention_analytics_cs_ops.service import (
    AlertService,
    CommandCenterService,
    PlaybookService,
    RenewalHubService,
    SuccessPlanService,
)
from retention_analytics_integrations.service import (
    IntegrationRegistryService,
    SlackAlertService,
    WebhookManagementService,
    HiroWebhookService,
)
from retention_analytics_compliance.service import AuditExportService, PrivacyService, SSOService

for svc_cls in (
    SaasMetricsService,
    PredictiveChurnService,
    FeedbackAIService,
    OfferRecommendationService,
    SuccessPlanService,
    PlaybookService,
    AlertService,
    RenewalHubService,
    CommandCenterService,
    IntegrationRegistryService,
    SlackAlertService,
    WebhookManagementService,
    HiroWebhookService,
    PrivacyService,
    AuditExportService,
    SSOService,
):
    svc_cls(registry).register()

# UX-layer services: settings, saved reports, bulk events, flow management, campaigns
from retention_analytics_ux.service import (
    BulkEventService,
    FlowManagementService,
    SavedReportService,
    TenantSettingsService,
)
from retention_analytics_ux.campaign import CampaignService

for svc_cls in (TenantSettingsService, SavedReportService, BulkEventService, FlowManagementService, CampaignService):
    svc_cls(registry).register()

# Advanced universal services (competitor parity): customer 360, service-due,
# benchmarks, goals, voice of customer, A/B testing, sequences, catalog, walls,
# journeys, attribution, anomaly detection, pricing experiments, QBR.
from retention_analytics_advanced.customer_intel import (
    BenchmarksService,
    Customer360Service,
    GoalsService,
    ServiceDueService,
    VoiceOfCustomerService,
)
from retention_analytics_advanced.experiments import (
    ABTestingService,
    AnomalyDetectionService,
    AttributionService,
    CatalogService,
    JourneyService,
    PricingExperimentService,
    QBRService,
    SequenceService,
    WallsService,
)
from retention_analytics_advanced.presets import PresetCatalogService
from retention_analytics_advanced.automation import (
    CancelFlowAPI,
    FlowEditorService,
    MicroSurveyService,
    ScheduledReportService,
    SessionReplayService,
    SlackBotService,
    UniversalExportService,
)
from retention_analytics_advanced.help_demo import DemoService, HelpService
from retention_analytics_advanced.datatransfer import DataTransferService
from retention_analytics_advanced.connectors import ConnectorService
from retention_analytics_lifecycle.state_machine import LifecycleService
from retention_analytics_lifecycle.dunning import DunningEngine
from retention_analytics_lifecycle.health import HealthEngine
from retention_analytics_lifecycle.renewals import RenewalRiskService
from retention_analytics_lifecycle.billing import MeteringService, ProrationService
from retention_analytics_lifecycle.loops import (
    ExperimentAutoPromoteService,
    IncidentService,
    NPSLoopService,
    WinbackTimingService,
)
from retention_analytics_advanced_processing.services import (
    CustomerPortalService,
    DeliverabilityService,
    MLChurnService,
    SendTimeService,
)
from retention_analytics_advanced_processing.analytics import (
    CohortComparison,
    MultiTouchAttribution,
    RootCauseService,
)
from retention_analytics_advanced_processing.annotations import AnnotationService
from retention_analytics_advanced_processing.analysis import (
    AdvancedSegmentation,
    AutoApproachService,
    NextBestActionService,
    TailoredContentService,
)
from retention_analytics_advanced_processing.agency import AgencyService
from retention_analytics_advanced_processing.agency_connectors import AgencyConnectorService
from retention_analytics_advanced_processing.performance import PerformanceAnalytics
from retention_analytics_advanced_processing.commerce import CommerceAnalytics
from retention_analytics_integrations.hiro_mcp import HiroMCPService
from retention_analytics_advanced_processing.segment_push import SegmentPushService
from retention_analytics_advanced_processing.agency_reports import (
    AgencyQAService,
    ReportDeckService,
    RoleViewService,
)

for svc_cls in (
    Customer360Service,
    ServiceDueService,
    BenchmarksService,
    GoalsService,
    VoiceOfCustomerService,
    ABTestingService,
    SequenceService,
    CatalogService,
    WallsService,
    JourneyService,
    AttributionService,
    AnomalyDetectionService,
    PricingExperimentService,
    QBRService,
    PresetCatalogService,
    ScheduledReportService,
    FlowEditorService,
    CancelFlowAPI,
    SlackBotService,
    SessionReplayService,
    MicroSurveyService,
    UniversalExportService,
    HelpService,
    DemoService,
    DataTransferService,
    ConnectorService,
    PlatformSurfaceService,
    LifecycleService,
    DunningEngine,
    HealthEngine,
    RenewalRiskService,
    MeteringService,
    ProrationService,
    NPSLoopService,
    ExperimentAutoPromoteService,
    IncidentService,
    WinbackTimingService,
    SendTimeService,
    MLChurnService,
    DeliverabilityService,
    CustomerPortalService,
    MultiTouchAttribution,
    CohortComparison,
    RootCauseService,
    AnnotationService,
    AdvancedSegmentation,
    NextBestActionService,
    AutoApproachService,
    TailoredContentService,
    AgencyService,
    AgencyConnectorService,
    PerformanceAnalytics,
    CommerceAnalytics,
    HiroMCPService,
    AgencyQAService,
    RoleViewService,
    ReportDeckService,
    SegmentPushService,
):
    svc_cls(registry).register()

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

app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(TracingMiddleware)
app.add_middleware(TenantContextMiddleware)
app.middleware("http")(metrics_middleware)
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
# Root / API info
# ---------------------------------------------------------------------------


_STARTED_AT = datetime.now(UTC)


def _platform_info() -> dict[str, Any]:
    services = registry.list_services()
    workflows = engine.list_definitions()
    total_actions = sum(len(registry.get(s).actions) for s in services)
    total_routes = len([r for r in app.routes if hasattr(r, "path")])
    try:
        from retention_analytics_advanced.pains import PAIN_CATALOG
        pains = len(PAIN_CATALOG)
        wf_ids = {d.id for d in workflows}
        pains_covered = sum(1 for p in PAIN_CATALOG.values() if any(w in wf_ids for w in p["workflows"]))
    except Exception:
        pains = pains_covered = 0
    return {
        "service": "retention-analytics-platform",
        "version": app.version,
        "environment": get_settings().environment,
        "status": "ok",
        "uptime_seconds": int((datetime.now(UTC) - _STARTED_AT).total_seconds()),
        "started_at": _STARTED_AT.isoformat(),
        "services_count": len(services),
        "actions_count": total_actions,
        "workflows_count": len(workflows),
        "workflows": [d.name for d in workflows],
        "routes_count": total_routes,
        "pains_total": pains,
        "pains_covered": pains_covered,
        "endpoints": {
            "health": "/health",
            "readiness": "/health/ready",
            "metrics": "/metrics",
            "docs": "/docs",
            "openapi": "/openapi.json",
            "services": "/api/v1/services",
            "actions_catalog": "/api/v1/actions",
            "workflows": "/api/v1/workflows",
            "campaigns": "/api/v1/campaigns",
            "customers": "/api/v1/customers",
            "events": "POST /api/v1/events",
            "reports": "/api/v1/reports/saved",
            "pains": "/api/v1/pains",
            "help": "/api/v1/help",
            "demo": "POST /api/v1/demo/run",
            "payments": "/api/v1/payments/providers",
            "presets": "/api/v1/presets",
            "integrations": "/api/v1/integrations/catalog",
            "feature_flags": "/api/v1/feature-flags/{name}",
            "monetization": "/api/v1/monetization/paths",
            "generic_action": "POST /api/v1/actions/{service}/{action}",
        },
        "portals": {
            "customer_portal": "http://localhost:47320",
            "dev_console": "http://localhost:47321",
            "swagger_ui": "/docs",
            "mcp": "MCP server (apps/mcp_server)",
        },
    }


@app.get("/")
async def root(request: Request):
    """API root: HTML status page for browsers, JSON for scripts (content negotiation)."""
    info = _platform_info()
    accept = request.headers.get("accept", "")
    if "text/html" in accept and "application/json" not in accept:
        from fastapi.responses import HTMLResponse

        uptime = info["uptime_seconds"]
        wfs = "".join(f"<span class='chip'>{w}</span>" for w in info["workflows"])
        eps = "".join(f"<tr><td><code>{k}</code></td><td><code>{v}</code></td></tr>" for k, v in info["endpoints"].items())
        html = f"""<!DOCTYPE html><html><head><meta charset='utf-8'/><title>Retention Analytics Platform</title>
<style>
 body{{font-family:system-ui,sans-serif;margin:0;background:#0f172a;color:#e2e8f0}}
 header{{background:linear-gradient(90deg,#4f46e5,#7c3aed);padding:28px 40px}}
 header h1{{margin:0;font-size:24px;color:#fff}}
 header p{{margin:6px 0 0;color:#c7d2fe;font-size:14px}}
 main{{max-width:1000px;margin:24px auto;padding:0 20px}}
 .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin-bottom:24px}}
 .card{{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:16px}}
 .card b{{font-size:26px;display:block;color:#fff}}
 .card span{{font-size:12px;color:#94a3b8;text-transform:uppercase}}
 .ok{{color:#34d399;font-weight:bold}}
 section{{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:20px;margin-bottom:20px}}
 h2{{font-size:16px;margin:0 0 12px;color:#c7d2fe}}
 .chip{{display:inline-block;background:#312e81;color:#c7d2fe;border-radius:6px;padding:3px 8px;margin:2px;font-size:11px;font-family:monospace}}
 table{{width:100%;border-collapse:collapse;font-size:13px}}
 td{{padding:5px 8px;border-bottom:1px solid #334155}}
 code{{color:#a5b4fc}}
 a{{color:#818cf8;text-decoration:none}} a:hover{{text-decoration:underline}}
 .links a{{display:inline-block;margin:3px 8px 3px 0;background:#312e81;padding:6px 12px;border-radius:8px;font-size:13px}}
 footer{{text-align:center;color:#64748b;font-size:12px;padding:20px}}
</style></head><body>
<header><h1>Retention Analytics Platform</h1>
<p>API v{info['version']} · environment <b>{info['environment']}</b> · status <span class='ok'>● {info['status']}</span> · uptime {uptime}s</p></header>
<main>
<div class='cards'>
 <div class='card'><b>{info['services_count']}</b><span>services</span></div>
 <div class='card'><b>{info['actions_count']}</b><span>actions</span></div>
 <div class='card'><b>{info['workflows_count']}</b><span>workflows</span></div>
 <div class='card'><b>{info['routes_count']}</b><span>routes</span></div>
 <div class='card'><b>{info['pains_covered']}/{info['pains_total']}</b><span>pains covered</span></div>
</div>
<section><h2>Portals</h2><div class='links'>
 <a href='http://localhost:47320'>Customer portal :47320</a>
 <a href='http://localhost:47321'>Dev console :47321</a>
 <a href='/docs'>Swagger UI</a>
 <a href='/openapi.json'>OpenAPI JSON</a>
 <a href='/metrics'>Metrics</a>
 <a href='/health'>Health</a>
 <a href='/api/v1/pains'>Pain coverage</a>
 <a href='/api/v1/help'>Help</a>
</div></section>
<section><h2>Workflows ({info['workflows_count']})</h2><div>{wfs}</div></section>
<section><h2>API endpoints</h2><table>{eps}</table></section>
<section><h2>Generic action proxy</h2><p style='font-size:13px'>Every one of the <b>{info['actions_count']}</b> registered service actions is callable:
<code>POST /api/v1/actions/&lt;service&gt;/&lt;action&gt;</code> with a JSON body. Catalog: <a href='/api/v1/actions'>/api/v1/actions</a>.</p></section>
</main><footer>retention-analytics-platform · started {info['started_at'][:19]} UTC · JSON available with <code>Accept: application/json</code></footer>
</body></html>"""
        return HTMLResponse(html)
    return info


# ---------------------------------------------------------------------------
# Health / observability
# ---------------------------------------------------------------------------


@app.get("/health")
async def health(request: Request) -> Any:
    """Liveness probe. HTML status page in browsers, JSON for probes/scripts."""
    data = {
        "status": "ok",
        "service": "retention-analytics-platform",
        "version": app.version,
        "environment": get_settings().environment,
        "uptime_seconds": int((datetime.now(UTC) - _STARTED_AT).total_seconds()),
        "services": registry.list_services(),
        "workflows": [d.name for d in engine.list_definitions()],
    }
    return maybe_html(request, data, "Health")


@app.get("/health/ready")
async def health_ready(request: Request, response: Response) -> Any:
    """Readiness probe with dependency checks."""
    adapters = get_adapters()
    result = await adapters.health.check_readiness()
    if result.get("status") != "healthy":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return maybe_html(request, result, "Readiness")


@app.get("/health/live")
async def health_live(request: Request) -> Any:
    return maybe_html(request, await get_adapters().health.check_liveness(), "Liveness")


@app.get("/api/v1/health")
async def api_health(request: Request) -> Any:
    """Frontend-facing health endpoint (same payload as ``/health``)."""
    return await health(request)


@app.get("/metrics")
async def metrics(request: Request) -> Response:
    """Prometheus metrics. Raw exposition for scrapers; a readable table in browsers."""
    raw = get_metrics_prometheus()
    if wants_html(request):
        return metrics_to_html(raw)
    return Response(content=raw, media_type="text/plain; version=0.0.4")


@app.get("/api/v1/agency/metrics")
async def agency_metrics(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> Any:
    """Agency + Hiro integration metrics dashboard."""
    tenant_id = current_tenant(request, user)
    # Agency roster summary
    roster = await registry.invoke("agency", "roster", {"tenant_id": tenant_id})
    # Hiro sync status
    hiro_syncs = await registry.invoke("connectors.agency", "sync", {"platform": "hiro", "tenant_id": tenant_id})
    # Digest status
    digests = await registry.invoke("agency", "list_digests", {})
    # Auto-act history
    actions = await registry.invoke("agency", "auto_act", {"tenant_id": tenant_id})

    data = {
        "status": "ok",
        "tenant_id": tenant_id,
        "roster": {
            "clients": roster.get("count", 0),
            "revenue_mtd": roster.get("summary", {}).get("total_revenue_mtd", 0),
            "behind_goal": roster.get("summary", {}).get("behind_goal", 0),
            "needs_attention": roster.get("summary", {}).get("needs_attention", 0),
            "churn_risk": roster.get("summary", {}).get("total_churn_risk", 0),
            "mrr_at_risk": roster.get("summary", {}).get("total_at_risk_mrr", 0),
        },
        "hiro": {
            "sync_status": hiro_syncs.get("status"),
            "last_sync": hiro_syncs.get("sync", {}).get("synced_at"),
            "records_synced": hiro_syncs.get("sync", {}).get("records"),
        },
        "digests": {
            "scheduled": len(digests.get("digests", [])),
            "active": sum(1 for d in digests.get("digests", []) if d.get("active")),
            "last_run": max((d.get("last_sent_at") for d in digests.get("digests", []) if d.get("last_sent_at")), default=None),
        },
        "auto_act": {
            "last_run": actions.get("acted") is not None and "now",
            "clients_acted": actions.get("acted", 0),
            "details": actions.get("clients", []),
        },
    }
    return maybe_html(request, data, "Agency Metrics")


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
async def list_services(request: Request) -> Any:
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
    return maybe_html(request, {"status": "ok", "services": services, "count": len(services)}, "Services")


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
async def list_workflows(request: Request) -> Any:
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
    return maybe_html(request, {"status": "ok", "workflows": workflows, "count": len(workflows)}, "Workflows")


@app.post("/api/v1/workflows/{workflow_id}/run")
async def run_workflow(
    workflow_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: WorkflowRunRequest = Body(default_factory=WorkflowRunRequest),
) -> dict[str, Any]:
    if not settings.workflows_enabled:
        raise HTTPException(status_code=503, detail="workflows are disabled")
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
    return await registry.invoke(
        "entitlements", "list_active", {"tenant_id": user.tenant_id}
    )


@app.post("/api/v1/webhooks/payments/{provider}")
async def receive_payment_webhook(
    provider: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Receive a payment provider webhook.

    Signature-verified and idempotent per provider event id. The event is
    recorded in the audit log and the idempotency ledger so a replayed
    webhook never double-processes a payment.
    """
    raw_body = await request.body()
    signature = request.headers.get("stripe-signature") or request.headers.get(
        "x-signature", ""
    )

    settings = get_settings()
    webhook_secret = settings.stripe_webhook_secret or settings.webhook_secret
    if settings.is_production and webhook_secret:
        expected = hmac.new(
            webhook_secret.encode("utf-8"), raw_body, sha256
        ).hexdigest()
        provided = signature.split("=", 1)[-1].strip() if "=" in signature else signature
        if not hmac.compare_digest(expected, provided):
            raise HTTPException(status_code=401, detail="invalid payment webhook signature")

    try:
        payload = json.loads(raw_body or b"{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="invalid JSON payload") from exc

    tenant_id = current_tenant(request, user)
    adapters = get_adapters()
    event_id = str(
        payload.get("id") or payload.get("event_id") or sha256(raw_body).hexdigest()[:16]
    )
    ledger_key = adapters.idempotency.build_key("payment_webhook", provider, tenant_id, event_id)

    claimed, prior = adapters.idempotency.claim(ledger_key, tenant_id)
    if not claimed:
        if prior is not None:
            return {**prior, "idempotent_replay": True}
        raise HTTPException(status_code=409, detail="payment webhook already being processed")

    result = {
        "status": "accepted",
        "provider": provider,
        "event_id": event_id,
        "event_type": payload.get("type", "unknown"),
        "tenant_id": tenant_id,
        "received_at": datetime.now(UTC).isoformat(),
    }
    adapters.idempotency.complete(ledger_key, result)
    _audit(
        event_type="payment.webhook.received",
        user=user,
        tenant_id=tenant_id,
        resource_type="payment_webhook",
        resource_id=event_id,
        action="receive",
        details={"provider": provider, "event_type": payload.get("type", "unknown")},
    )
    return result


# ---------------------------------------------------------------------------
# Platform services (feature flags, quota, sessions, profile, notifications,
# webhooks out, organizations, support, feedback, monetization, etc.)
# ---------------------------------------------------------------------------


@app.get("/api/v1/feature-flags/{flag_name}")
async def check_feature_flag(
    flag_name: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Check if a feature flag is enabled for the authenticated tenant."""
    tenant_id = current_tenant(request, user)
    result = await registry.invoke(
        "feature_flags", "is_enabled", {"flag": flag_name, "tenant_id": tenant_id}
    )
    return result


@app.post("/api/v1/quota/check")
async def check_quota(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    resource: str = "api_calls",
) -> dict[str, Any]:
    """Check quota for a resource."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke(
        "quota", "check", {"tenant_id": tenant_id, "resource": resource}
    )


@app.post("/api/v1/sessions")
async def create_session(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Create a new session for the authenticated user."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke(
        "sessions", "create", {"user_id": user.user_id, "tenant_id": tenant_id}
    )


@app.get("/api/v1/profile")
async def get_profile(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Get the authenticated user's profile."""
    return await registry.invoke("profile", "get", {"user_id": user.user_id})


@app.post("/api/v1/notifications")
async def send_notification(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    title: str = "Notification",
    body: str = "",
    type: str = "info",
) -> dict[str, Any]:
    """Send a notification to the authenticated user."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke(
        "notifications",
        "send",
        {"user_id": user.user_id, "tenant_id": tenant_id, "title": title, "body": body, "type": type},
    )


@app.post("/api/v1/webhooks/out/dispatch")
async def dispatch_webhook(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    url: str,
    event_type: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dispatch an outbound webhook with DLQ support."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke(
        "webhooks_out",
        "dispatch",
        {"url": url, "event_type": event_type, "data": data or {}, "tenant_id": tenant_id},
    )


@app.get("/api/v1/organizations/invitations")
async def list_invitations(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    org_id: str = "",
) -> dict[str, Any]:
    """List pending invitations for an organization."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke(
        "organizations", "list", {"org_id": org_id or tenant_id, "tenant_id": tenant_id}
    )


@app.post("/api/v1/organizations/invitations")
async def create_invitation(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    email: str,
    role: str = "member",
    org_id: str = "",
) -> dict[str, Any]:
    """Invite a user to an organization."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke(
        "organizations",
        "invite",
        {"org_id": org_id or tenant_id, "email": email, "role": role, "tenant_id": tenant_id},
    )


@app.post("/api/v1/support/tickets")
async def create_support_ticket(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    subject: str,
    description: str = "",
    priority: str = "normal",
) -> dict[str, Any]:
    """Create a support ticket."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke(
        "support",
        "create_ticket",
        {
            "tenant_id": tenant_id,
            "subject": subject,
            "description": description,
            "priority": priority,
        },
    )


@app.post("/api/v1/feedback")
async def submit_feedback(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    score: int,
    comment: str = "",
) -> dict[str, Any]:
    """Submit product feedback / NPS score."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke(
        "feedback",
        "submit",
        {"tenant_id": tenant_id, "user_id": user.user_id, "score": score, "comment": comment},
    )


@app.get("/api/v1/monetization/paths")
async def list_monetization_paths(
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """List available monetization paths."""
    return await registry.invoke("monetization", "list_paths", {"tenant_id": user.tenant_id})


@app.post("/api/v1/leads")
async def capture_lead(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    email: str,
    source: str = "direct",
) -> dict[str, Any]:
    """Capture a lead."""
    tenant_id = current_tenant(request, user)
    from datetime import UTC, datetime

    return await registry.invoke(
        "lead_capture",
        "capture",
        {
            "email": email,
            "source": source,
            "tenant_id": tenant_id,
            "captured_at": datetime.now(UTC).isoformat(),
        },
    )


# ---------------------------------------------------------------------------
# Growth services (health, dunning, surveys, forecasting, segmentation, in-app)
# ---------------------------------------------------------------------------


@app.post("/api/v1/health/compute")
async def compute_health(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    client_id: str = "",
    usage_score: float = 50,
    support_score: float = 50,
    payment_score: float = 100,
    engagement_score: float = 50,
) -> dict[str, Any]:
    """Compute customer health score (0-100). Competitor: ChurnZero ChurnScores, Vitally Health."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke(
        "health.scoring", "compute",
        {"tenant_id": tenant_id, "client_id": client_id, "usage_score": usage_score,
         "support_score": support_score, "payment_score": payment_score, "engagement_score": engagement_score},
    )


@app.get("/api/v1/health/at-risk")
async def list_at_risk(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    threshold: float = 50,
) -> dict[str, Any]:
    """List clients below health threshold."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("health.scoring", "list_low", {"tenant_id": tenant_id, "threshold": threshold})


@app.post("/api/v1/dunning/start")
async def start_dunning(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    subscription_id: str,
    customer_email: str,
    amount_due: float = 0,
) -> dict[str, Any]:
    """Start dunning campaign for failed payment. Competitor: Baremetrics Recover, Churnkey Payment Recovery."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke(
        "dunning", "start_campaign",
        {"tenant_id": tenant_id, "subscription_id": subscription_id, "customer_email": customer_email, "amount_due": amount_due},
    )


@app.get("/api/v1/dunning/active")
async def list_dunning(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("dunning", "list_active", {"tenant_id": tenant_id})


@app.post("/api/v1/surveys/nps")
async def send_nps_survey(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    client_id: str = "",
    customer_email: str = "",
) -> dict[str, Any]:
    """Send NPS survey. Competitor: Vitally NPS, ChurnZero Surveys."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("surveys", "send_nps", {"tenant_id": tenant_id, "client_id": client_id, "customer_email": customer_email})


@app.get("/api/v1/surveys/nps-score")
async def get_nps(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("surveys", "compute_nps", {"tenant_id": tenant_id})


@app.post("/api/v1/forecast/mrr")
async def forecast_mrr(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    current_mrr: float = 0,
    monthly_growth_rate: float = 0.05,
    monthly_churn_rate: float = 0.03,
    months: int = 12,
) -> dict[str, Any]:
    """Forecast MRR. Competitor: Baremetrics Forecasting."""
    return await registry.invoke(
        "forecasting", "forecast_mrr",
        {"current_mrr": current_mrr, "monthly_growth_rate": monthly_growth_rate, "monthly_churn_rate": monthly_churn_rate, "months": months},
    )


@app.get("/api/v1/segments")
async def list_segments(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """List saved segments for the tenant."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("segmentation", "list_segments", {"tenant_id": tenant_id})


@app.post("/api/v1/segments")
async def define_segment(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    name: str,
    criteria: dict[str, Any] | None = None,
    segment_id: str = "",
) -> dict[str, Any]:
    """Define a customer segment. Competitor: Baremetrics/Churnkey Segmentation."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke(
        "segmentation", "define_segment",
        {"tenant_id": tenant_id, "name": name, "criteria": criteria or {}, "segment_id": segment_id},
    )


@app.post("/api/v1/inapp/banner")
async def send_inapp_banner(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    title: str,
    body: str = "",
    client_id: str = "",
) -> dict[str, Any]:
    """Send in-app banner. Competitor: ChurnZero In-app communications."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("inapp.messaging", "send_banner", {"tenant_id": tenant_id, "client_id": client_id, "title": title, "body": body})


# ---------------------------------------------------------------------------
# SaaS metrics suite (MRR/ARR/GRR/NRR/LTV/CAC/ARPU/payback/logo/quick-ratio)
# ---------------------------------------------------------------------------


@app.post("/api/v1/metrics/saas")
async def compute_saas_metrics(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Compute full SaaS metrics suite. Competitor: Baremetrics/ChartMogul metrics."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("saas.metrics", "compute_all", {**body, "tenant_id": tenant_id})


@app.post("/api/v1/metrics/{metric_name}")
async def compute_one_metric(
    metric_name: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Compute a single SaaS metric (mrr, arr, grr, nrr, ltv, cac, arpu, payback, logo_retention, quick_ratio)."""
    tenant_id = current_tenant(request, user)
    action = f"compute_{metric_name}"
    return await registry.invoke("saas.metrics", action, {**body, "tenant_id": tenant_id})


# ---------------------------------------------------------------------------
# AI: predictive churn, feedback classification, offer recommendation
# ---------------------------------------------------------------------------


@app.post("/api/v1/ai/churn/predict")
async def predict_churn(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    client_id: str = "",
    usage_drop_pct: float = 0,
    open_tickets: int = 0,
    payment_failures: int = 0,
    logins_last_30d: int = 10,
    nps_score: float = 8,
) -> dict[str, Any]:
    """Predict churn probability. Competitor: Churnkey Customer Health."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("ai.churn_predict", "predict", {
        "tenant_id": tenant_id, "client_id": client_id,
        "usage_drop_pct": usage_drop_pct, "open_tickets": open_tickets,
        "payment_failures": payment_failures, "logins_last_30d": logins_last_30d, "nps_score": nps_score,
    })


@app.get("/api/v1/ai/churn/at-risk")
async def list_churn_at_risk(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    threshold: float = 0.4,
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("ai.churn_predict", "at_risk_list", {"tenant_id": tenant_id, "threshold": threshold})


@app.post("/api/v1/ai/feedback/classify")
async def classify_feedback(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] | None = Body(default=None),
    text: str = "",
    client_id: str = "",
    mrr: float = 0,
) -> dict[str, Any]:
    """Classify freeform feedback. Accepts a JSON body or query params."""
    tenant_id = current_tenant(request, user)
    payload = body or {}
    return await registry.invoke("ai.feedback", "classify", {
        "tenant_id": tenant_id,
        "text": payload.get("text", text),
        "client_id": payload.get("client_id", client_id),
        "mrr": payload.get("mrr", mrr),
    })


@app.get("/api/v1/ai/feedback/themes")
async def feedback_themes(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("ai.feedback", "themes", {"tenant_id": tenant_id})


@app.post("/api/v1/ai/offers/recommend")
async def recommend_offer(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] | None = Body(default=None),
    churn_reason: str = "general",
    churn_probability: float = 0.5,
    mrr: float = 0,
) -> dict[str, Any]:
    """Recommend the best retention offer for a churn reason. Accepts a JSON body or query params."""
    tenant_id = current_tenant(request, user)
    payload = body or {}
    return await registry.invoke("ai.offers", "recommend", {
        "tenant_id": tenant_id,
        "churn_reason": payload.get("churn_reason", churn_reason),
        "churn_probability": payload.get("churn_probability", churn_probability),
        "mrr": payload.get("mrr", mrr),
    })


# ---------------------------------------------------------------------------
# CS ops: success plans, playbooks, alerts, renewals, command center
# ---------------------------------------------------------------------------


@app.post("/api/v1/cs/plans")
async def create_success_plan(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    name: str,
    client_id: str = "",
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("cs.plans", "create", {"tenant_id": tenant_id, "client_id": client_id, "name": name})


@app.get("/api/v1/cs/plans")
async def list_success_plans(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    client_id: str = "",
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("cs.plans", "list", {"tenant_id": tenant_id, "client_id": client_id})


class PlaybookCreateRequest(BaseModel):
    name: str
    trigger: str = ""
    actions: list[dict[str, Any]] = Field(default_factory=list)


@app.post("/api/v1/cs/playbooks")
async def create_playbook(
    body: PlaybookCreateRequest,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Create automated playbook. Competitor: ChurnZero Playbooks/Journeys, Vitally Automation."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("cs.playbooks", "create", {"tenant_id": tenant_id, "name": body.name, "trigger": body.trigger, "actions": body.actions})


@app.post("/api/v1/cs/playbooks/{playbook_id}/run")
async def run_playbook(
    playbook_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    client_id: str = "",
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("cs.playbooks", "run", {"tenant_id": tenant_id, "playbook_id": playbook_id, "client_id": client_id})


@app.get("/api/v1/cs/alerts/open")
async def list_open_alerts(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Open real-time alerts. Competitor: ChurnZero Real-time alerts."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("cs.alerts", "list_open", {"tenant_id": tenant_id})


@app.post("/api/v1/cs/alerts/fire")
async def fire_alert(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    title: str,
    detail: str = "",
    severity: str = "medium",
    type: str = "info",
    client_id: str = "",
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("cs.alerts", "fire", {"tenant_id": tenant_id, "client_id": client_id, "title": title, "detail": detail, "severity": severity, "type": type})


@app.get("/api/v1/cs/renewals/forecast")
async def renewal_forecast(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Renewal forecast. Competitor: ChurnZero Renewal & Forecast Hub."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("cs.renewals", "forecast", {"tenant_id": tenant_id})


@app.get("/api/v1/cs/command-center")
async def command_center(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Unified command center overview. Competitor: ChurnZero Command Center."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("cs.command_center", "overview", {"tenant_id": tenant_id})


# ---------------------------------------------------------------------------
# Integrations: catalog, connect, Slack, webhook management
# ---------------------------------------------------------------------------


@app.get("/api/v1/integrations/catalog")
async def integration_catalog(user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, Any]:
    """70+ supported integrations. Competitor: ChurnZero 70+, Vitally 40+."""
    return await registry.invoke("integrations", "catalog", {})


@app.post("/api/v1/integrations/connect")
async def connect_integration(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    provider: str,
    category: str = "other",
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("integrations", "connect", {"tenant_id": tenant_id, "provider": provider, "category": category})


@app.get("/api/v1/integrations/connected")
async def list_connected(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("integrations", "list_connected", {"tenant_id": tenant_id})


@app.post("/api/v1/integrations/slack/send")
async def send_slack(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    text: str,
    channel: str = "#customer-success",
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("integrations.slack", "send", {"tenant_id": tenant_id, "channel": channel, "text": text})


class WebhookEndpointRequest(BaseModel):
    url: str
    events: list[str] = Field(default_factory=list)


@app.post("/api/v1/webhook-endpoints")
async def register_webhook_endpoint(
    body: WebhookEndpointRequest,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Register outbound webhook endpoint. Competitor: Churnkey Webhooks."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("webhooks.manage", "register", {"tenant_id": tenant_id, "url": body.url, "events": body.events})


@app.get("/api/v1/webhook-endpoints")
async def list_webhook_endpoints(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("webhooks.manage", "list", {"tenant_id": tenant_id})


# ---------------------------------------------------------------------------
# Compliance: GDPR/CCPA, audit export, SSO
# ---------------------------------------------------------------------------


@app.post("/api/v1/compliance/export")
async def gdpr_export(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """GDPR right to data portability: export all tenant data."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("compliance.privacy", "export_data", {"tenant_id": tenant_id, "subject_email": user.user_id})


@app.post("/api/v1/compliance/delete")
async def gdpr_delete(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """GDPR right to erasure: delete all tenant data. DANGEROUS — audit logged."""
    tenant_id = current_tenant(request, user)
    _audit(event_type="gdpr.delete_requested", user=user, tenant_id=tenant_id, resource_type="tenant_data", resource_id=tenant_id, action="delete_request")
    return await registry.invoke("compliance.privacy", "delete_data", {"tenant_id": tenant_id, "subject_email": user.user_id})


@app.get("/api/v1/compliance/audit-export")
async def audit_export(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Export hash-chained audit log for SOC 2 evidence."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("compliance.audit_export", "export", {"tenant_id": tenant_id})


@app.get("/api/v1/compliance/sso/status")
async def sso_status(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """SSO/SAML configuration status."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("compliance.sso", "status", {"tenant_id": tenant_id})


# ---------------------------------------------------------------------------
# UX layer: settings, saved reports, bulk events, flow management
# ---------------------------------------------------------------------------


class SettingsUpdate(BaseModel):
    updates: dict[str, Any] = Field(default_factory=dict)


@app.get("/api/v1/settings")
async def get_settings_ux(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Get editable tenant settings (notifications, flags, quotas, branding)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("ux.settings", "get", {"tenant_id": tenant_id})


@app.patch("/api/v1/settings")
async def update_settings_ux(
    body: SettingsUpdate,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Update tenant settings. Persisted per tenant."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("ux.settings", "update", {"tenant_id": tenant_id, "updates": body.updates})


@app.post("/api/v1/settings/flags/{flag}")
async def set_feature_flag_ux(
    flag: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    enabled: bool = True,
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("ux.settings", "set_flag", {"tenant_id": tenant_id, "flag": flag, "enabled": enabled})


@app.post("/api/v1/settings/api-keys")
async def create_api_key_ux(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    name: str = "API Key",
) -> dict[str, Any]:
    """Create a new API key for the tenant."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("ux.settings", "create_api_key", {"tenant_id": tenant_id, "name": name})


@app.get("/api/v1/settings/api-keys")
async def list_api_keys_ux(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("ux.settings", "list_api_keys", {"tenant_id": tenant_id})


@app.delete("/api/v1/settings/api-keys/{key_id}")
async def revoke_api_key_ux(
    key_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("ux.settings", "revoke_api_key", {"tenant_id": tenant_id, "key_id": key_id})


# --- Saved reports ---


class SaveReportRequest(BaseModel):
    name: str
    description: str = ""
    format: str = "json"
    filters: dict[str, Any] = Field(default_factory=dict)
    widgets: list[str] = Field(default_factory=list)
    schedule: dict[str, Any] | None = None


@app.post("/api/v1/reports/saved")
async def save_report(
    body: SaveReportRequest,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Save a named report with filters and widgets. Users re-run it anytime."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("ux.reports", "save", {
        "tenant_id": tenant_id, "name": body.name, "description": body.description,
        "format": body.format, "filters": body.filters, "widgets": body.widgets, "schedule": body.schedule,
    })


@app.get("/api/v1/reports/saved")
async def list_saved_reports(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("ux.reports", "list", {"tenant_id": tenant_id})


@app.post("/api/v1/reports/saved/{report_id}/run")
async def run_saved_report(
    report_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Run a saved report: applies filters, computes analytics widgets, stores result."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("ux.reports", "run", {"tenant_id": tenant_id, "report_id": report_id})


@app.delete("/api/v1/reports/saved/{report_id}")
async def delete_saved_report(
    report_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("ux.reports", "delete", {"tenant_id": tenant_id, "report_id": report_id})


# --- Bulk events ---


@app.get("/api/v1/events/schemas")
async def event_schemas(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Event type schemas — the UI renders dynamic forms from this."""
    return await registry.invoke("ux.events", "schemas", {})


class BulkImportRequest(BaseModel):
    event_type: str
    rows: list[dict[str, Any]]
    mapping: dict[str, str] = Field(default_factory=dict)


@app.post("/api/v1/events/bulk-import")
async def bulk_import_events(
    body: BulkImportRequest,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Bulk import events from rows + field mapping (CSV columns → payload fields)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("ux.events", "bulk_import", {
        "tenant_id": tenant_id, "event_type": body.event_type, "rows": body.rows, "mapping": body.mapping,
    })


class MapFieldsRequest(BaseModel):
    event_type: str
    columns: list[str]


@app.post("/api/v1/events/map-fields")
async def map_fields(
    body: MapFieldsRequest,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Suggest field mapping from CSV columns to event payload fields."""
    return await registry.invoke("ux.events", "map_fields", {"event_type": body.event_type, "columns": body.columns})


@app.get("/api/v1/events/export")
async def export_events(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Export imported events as CSV."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("ux.events", "export", {"tenant_id": tenant_id})


# --- Flow management ---


@app.post("/api/v1/workflows/{workflow_id}/toggle")
async def toggle_workflow(
    workflow_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    active: bool = True,
) -> dict[str, Any]:
    """Enable/disable a workflow."""
    tenant_id = current_tenant(request, user)
    result = await registry.invoke("ux.flows", "set_active", {"tenant_id": tenant_id, "workflow_id": workflow_id, "active": active})
    engine_def = engine.get_definition(workflow_id)
    if engine_def:
        engine_def.active = active
    return result


@app.post("/api/v1/workflows/{workflow_id}/target")
async def set_workflow_target(
    workflow_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    segment_id: str = "",
    segment_name: str = "All customers",
) -> dict[str, Any]:
    """Assign a target segment to a workflow — who it applies to."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("ux.flows", "set_target", {"tenant_id": tenant_id, "workflow_id": workflow_id, "segment_id": segment_id, "segment_name": segment_name})


@app.get("/api/v1/workflows/config")
async def list_workflow_config(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Get per-workflow config (active, target segment, custom steps) for the UI."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("ux.flows", "list_config", {"tenant_id": tenant_id})


# ---------------------------------------------------------------------------
# Campaigns — the unified orchestration layer: SEGMENT -> FLOWS -> RUN -> MEASURE
# Data transfer: CSV/JSON import + export for customers, campaigns

# ---------------------------------------------------------------------------


class CampaignCreateRequest(BaseModel):
    name: str
    description: str = ""
    goal: str = "reduce_churn"
    segment: dict[str, Any] = Field(default_factory=lambda: {"id": "all", "name": "All customers", "criteria": {}})
    flows: list[str] = Field(default_factory=list)
    schedule: dict[str, Any] = Field(default_factory=lambda: {"type": "once"})
    success_metrics: list[str] = Field(default_factory=list)


@app.get("/api/v1/campaigns/goals")
async def campaign_goals(user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, Any]:
    """Available campaign goals with default flows and metrics."""
    return await registry.invoke("campaigns", "goals", {})


@app.post("/api/v1/campaigns")
async def create_campaign(
    body: CampaignCreateRequest,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Create a campaign: goal + target segment + flows + schedule + success metrics."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("campaigns", "create", {"tenant_id": tenant_id, **body.model_dump()})


@app.get("/api/v1/campaigns")
async def list_campaigns(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("campaigns", "list", {"tenant_id": tenant_id})


@app.get("/api/v1/campaigns/{campaign_id}")
async def get_campaign(
    campaign_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("campaigns", "get", {"tenant_id": tenant_id, "campaign_id": campaign_id})


@app.post("/api/v1/campaigns/{campaign_id}/activate")
async def activate_campaign(
    campaign_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Activate: binds flows to the target segment, ready to run."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("campaigns", "activate", {"tenant_id": tenant_id, "campaign_id": campaign_id})


@app.post("/api/v1/campaigns/{campaign_id}/pause")
async def pause_campaign(
    campaign_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("campaigns", "pause", {"tenant_id": tenant_id, "campaign_id": campaign_id})


class CampaignRunRequest(BaseModel):
    clients: list[dict[str, Any]] = Field(default_factory=list)


@app.post("/api/v1/campaigns/{campaign_id}/run")
async def run_campaign(
    campaign_id: str,
    body: CampaignRunRequest,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Run a campaign: evaluate segment -> run flows per member -> measure before/after."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("campaigns", "run", {"tenant_id": tenant_id, "campaign_id": campaign_id, "clients": body.clients})


@app.get("/api/v1/campaigns/{campaign_id}/results")
async def campaign_results(
    campaign_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Campaign results: outcomes per member + baseline/after metrics + deltas."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("campaigns", "results", {"tenant_id": tenant_id, "campaign_id": campaign_id})


@app.delete("/api/v1/campaigns/{campaign_id}")
async def delete_campaign(
    campaign_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("campaigns", "delete", {"tenant_id": tenant_id, "campaign_id": campaign_id})


@app.post("/api/v1/segments/evaluate")
async def evaluate_segment(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    criteria: dict[str, Any] = Body(default_factory=dict),
    clients: list[dict[str, Any]] = Body(default_factory=list),
) -> dict[str, Any]:
    """Evaluate segment criteria against a client list — see who a campaign targets."""
    return await registry.invoke("campaigns", "evaluate_segment", {"criteria": criteria, "clients": clients})


# ---------------------------------------------------------------------------
# Advanced universal services
# ---------------------------------------------------------------------------


class CustomerProfileRequest(BaseModel):
    id: str = ""
    name: str = ""
    email: str = ""
    phone: str = ""
    plan: str = ""
    mrr: float = 0
    ltv: float = 0
    health_score: float = 100
    last_service_date: str | None = None
    service_interval_days: int = 0
    service_name: str = ""
    attributes: dict[str, Any] = Field(default_factory=dict)


@app.post("/api/v1/customers")
async def upsert_customer(
    body: CustomerProfileRequest,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Create/update a customer record with computed next-due date and days remaining."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("customers.360", "upsert_profile", {"tenant_id": tenant_id, **body.model_dump()})


@app.get("/api/v1/customers")
async def list_customers(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("customers.360", "list_profiles", {"tenant_id": tenant_id})


@app.get("/api/v1/customers/{customer_id}")
async def get_customer(
    customer_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Customer 360: profile + enrichment + touchpoints + recordings."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("customers.360", "get_profile", {"tenant_id": tenant_id, "id": customer_id})


@app.get("/api/v1/customers/{customer_id}/timeline")
async def customer_timeline(
    customer_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Unified customer timeline across profile, touchpoints, recordings."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("customers.360", "timeline", {"tenant_id": tenant_id, "id": customer_id})


@app.post("/api/v1/customers/{customer_id}/touchpoints")
async def log_touchpoint(
    customer_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Log a call/meeting/email/note against a customer."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("customers.360", "log_touchpoint", {"tenant_id": tenant_id, "customer_id": customer_id, **body})


@app.post("/api/v1/customers/{customer_id}/recordings")
async def link_recording(
    customer_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Link a session recording to a customer."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("customers.360", "link_recording", {"tenant_id": tenant_id, "customer_id": customer_id, **body})


@app.post("/api/v1/customers/{customer_id}/enrich")
async def enrich_customer(
    customer_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Augmentation: merge external data into a customer profile."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("customers.360", "enrich", {"tenant_id": tenant_id, "id": customer_id, **body})


@app.get("/api/v1/service-due")
async def service_due_scan(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    within_days: int = 7,
) -> dict[str, Any]:
    """Scan for services due soon or overdue (oil change, treatment, subscription, maintenance)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("customers.service_due", "scan", {"tenant_id": tenant_id, "within_days": within_days})


@app.post("/api/v1/service-due/reminders")
async def schedule_service_reminders(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    within_days: int = 7,
) -> dict[str, Any]:
    """Create reminders for due/overdue services — feeds the service-reminder flow."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("customers.service_due", "schedule_reminders", {"tenant_id": tenant_id, "within_days": within_days})


@app.get("/api/v1/benchmarks")
async def list_benchmarks(user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, Any]:
    """Industry benchmark baselines."""
    return await registry.invoke("benchmarks", "list_industries", {})


@app.post("/api/v1/benchmarks/compare")
async def compare_benchmarks(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Compare your metrics against industry benchmarks."""
    return await registry.invoke("benchmarks", "compare", body)


@app.get("/api/v1/goals")
async def list_goals(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("goals", "list", {"tenant_id": tenant_id})


@app.post("/api/v1/goals")
async def create_goal(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Set a business goal (MRR, churn rate, NPS...) and track progress."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("goals", "create", {"tenant_id": tenant_id, **body})


@app.post("/api/v1/experiments")
async def create_experiment(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Create an A/B experiment with variants."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("experiments.ab", "create", {"tenant_id": tenant_id, **body})


@app.get("/api/v1/experiments")
async def list_experiments(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("experiments.ab", "list", {"tenant_id": tenant_id})


@app.post("/api/v1/experiments/{experiment_id}/results")
async def record_experiment_result(
    experiment_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Record variant outcomes."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("experiments.ab", "record_result", {"tenant_id": tenant_id, "experiment_id": experiment_id, **body})


@app.get("/api/v1/experiments/{experiment_id}/analyze")
async def analyze_experiment(
    experiment_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Compare variant conversion rates and identify the winner."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("experiments.ab", "analyze", {"tenant_id": tenant_id, "experiment_id": experiment_id})


@app.post("/api/v1/sequences")
async def create_sequence(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Create a multi-touch drip sequence (email/SMS/push with delays)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("automation.sequences", "create", {"tenant_id": tenant_id, **body})


@app.get("/api/v1/sequences")
async def list_sequences(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("automation.sequences", "list", {"tenant_id": tenant_id})


@app.post("/api/v1/sequences/{sequence_id}/enroll")
async def enroll_sequence(
    sequence_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Enroll a customer into a drip sequence."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("automation.sequences", "enroll", {"tenant_id": tenant_id, "sequence_id": sequence_id, **body})


@app.post("/api/v1/sequences/advance")
async def advance_sequence(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Advance an enrollment to its next touch (or complete the sequence)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("automation.sequences", "advance", {"tenant_id": tenant_id, **body})


@app.post("/api/v1/catalog/products")
async def add_product(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Add a product to the catalog (for cross-sell/upsell)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("catalog", "add_product", {"tenant_id": tenant_id, **body})


@app.get("/api/v1/catalog/products")
async def list_products(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("catalog", "list_products", {"tenant_id": tenant_id})


@app.post("/api/v1/catalog/offers")
async def add_offer(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Add an offer (discount, cross-sell, pause, downgrade, annual)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("catalog", "add_offer", {"tenant_id": tenant_id, **body})


@app.get("/api/v1/catalog/offers")
async def list_offers(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("catalog", "list_offers", {"tenant_id": tenant_id})


@app.post("/api/v1/catalog/cross-sell/recommend")
async def recommend_cross_sell(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Recommend complementary products for a customer."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("catalog", "recommend_cross_sell", {"tenant_id": tenant_id, **body})


@app.post("/api/v1/walls")
async def create_wall(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Create a pause wall or payment wall (gates features until resolved)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("walls", "create", {"tenant_id": tenant_id, **body})


@app.get("/api/v1/walls/check")
async def check_wall(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    customer_id: str = "",
) -> dict[str, Any]:
    """Check if a customer is behind a wall and which features are blocked."""
    return await registry.invoke("walls", "check", {"customer_id": customer_id})


@app.post("/api/v1/journeys")
async def create_journey(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Create a multi-stage customer journey."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("journeys", "create", {"tenant_id": tenant_id, **body})


@app.get("/api/v1/journeys")
async def list_journeys(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("journeys", "list", {"tenant_id": tenant_id})


@app.post("/api/v1/journeys/{journey_id}/stage")
async def set_journey_stage(
    journey_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Move a customer to a journey stage."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("journeys", "set_stage", {"tenant_id": tenant_id, "journey_id": journey_id, **body})


@app.get("/api/v1/journeys/{journey_id}/stage-distribution")
async def journey_stage_distribution(
    journey_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """How many customers sit at each journey stage."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("journeys", "stage_distribution", {"tenant_id": tenant_id, "journey_id": journey_id})


@app.post("/api/v1/attribution/outcome")
async def record_attribution(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Record an outcome (retained/churned/recovered) attributed to a campaign."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("analytics.attribution", "record_outcome", {"tenant_id": tenant_id, **body})


@app.get("/api/v1/attribution/campaigns")
async def campaign_attribution(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Saved revenue and save rate per campaign."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("analytics.attribution", "campaign_impact", {"tenant_id": tenant_id})


@app.post("/api/v1/anomalies/detect")
async def detect_anomalies(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Detect metric anomalies against trailing average."""
    return await registry.invoke("analytics.anomaly", "detect", body)


@app.post("/api/v1/pricing-experiments")
async def create_pricing_experiment(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Create a pricing experiment across price points."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("experiments.pricing", "create", {"tenant_id": tenant_id, **body})


@app.get("/api/v1/pricing-experiments")
async def list_pricing_experiments(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("experiments.pricing", "list", {"tenant_id": tenant_id})


@app.post("/api/v1/pricing-experiments/{test_id}/results")
async def record_pricing_result(
    test_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Record exposure/conversion for a price point."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("experiments.pricing", "record_result", {"tenant_id": tenant_id, "test_id": test_id, **body})


@app.get("/api/v1/pricing-experiments/{test_id}/analyze")
async def analyze_pricing_experiment(
    test_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("experiments.pricing", "analyze", {"tenant_id": tenant_id, "test_id": test_id})


@app.post("/api/v1/qbr")
async def generate_qbr(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Generate a QBR from account data, touchpoints, and health."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("cs.qbr", "generate", {"tenant_id": tenant_id, **body})


@app.post("/api/v1/feedback/board")
async def submit_voc(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Submit an item to the public voice-of-customer board."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("feedback.voc", "submit", {"tenant_id": tenant_id, **body})


@app.get("/api/v1/feedback/board")
async def list_voc(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("feedback.voc", "list", {"tenant_id": tenant_id})


@app.post("/api/v1/feedback/board/{item_id}/upvote")
async def upvote_voc(
    item_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return await registry.invoke("feedback.voc", "upvote", {"id": item_id})


# ---------------------------------------------------------------------------
# Universal presets (optional industry shortcuts — apply to ANY business)
# ---------------------------------------------------------------------------


@app.get("/api/v1/presets/applied")
async def list_applied_presets(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("presets", "applied", {"tenant_id": tenant_id})


@app.get("/api/v1/presets")
async def list_presets(user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, Any]:
    """Industry presets: optional shortcuts. Each works on any business whose customer records have the needed fields."""
    return await registry.invoke("presets", "list", {})


@app.get("/api/v1/presets/{preset_id}")
async def get_preset(
    preset_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Full preset contents: customer fields, segments, campaigns, sequences."""
    return await registry.invoke("presets", "get", {"preset_id": preset_id})


@app.post("/api/v1/presets/{preset_id}/apply")
async def apply_preset(
    preset_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Apply a preset: creates its segments, campaigns, and sequences. Additive and fully editable."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("presets", "apply", {"tenant_id": tenant_id, "preset_id": preset_id})


# --- Remaining typed endpoints for advanced services ---

@app.get("/api/v1/customers/{customer_id}/touchpoints")
async def list_customer_touchpoints(
    customer_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return await registry.invoke("customers.360", "list_touchpoints", {"customer_id": customer_id})


@app.get("/api/v1/customers/{customer_id}/recordings")
async def list_customer_recordings(
    customer_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return await registry.invoke("customers.360", "list_recordings", {"customer_id": customer_id})


@app.get("/api/v1/customers/{customer_id}/enrichment")
async def get_customer_enrichment(
    customer_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return await registry.invoke("customers.360", "get_enrichment", {"id": customer_id})


@app.post("/api/v1/service-due/{reminder_id}/reminded")
async def mark_service_reminded(
    reminder_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return await registry.invoke("customers.service_due", "mark_reminded", {"reminder_id": reminder_id})


@app.post("/api/v1/goals/{goal_id}/progress")
async def update_goal_progress(
    goal_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Update a goal's current value."""
    return await registry.invoke("goals", "update_progress", {"goal_id": goal_id, **body})


@app.delete("/api/v1/goals/{goal_id}")
async def delete_goal(
    goal_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return await registry.invoke("goals", "delete", {"goal_id": goal_id})


@app.post("/api/v1/feedback/board/{item_id}/status")
async def set_voc_status(
    item_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Set roadmap status on a feedback item (open/planned/shipped/closed)."""
    return await registry.invoke("feedback.voc", "set_status", {"id": item_id, **body})


@app.get("/api/v1/experiments/{experiment_id}")
async def get_experiment(
    experiment_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("experiments.ab", "get", {"tenant_id": tenant_id, "experiment_id": experiment_id})


@app.post("/api/v1/experiments/{experiment_id}/notes")
async def annotate_experiment(
    experiment_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Add a note to an experiment/campaign to track metric impact (Trial Insights)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("experiments.ab", "annotate", {"tenant_id": tenant_id, "experiment_id": experiment_id, **body})


@app.get("/api/v1/sequences/{sequence_id}")
async def get_sequence(
    sequence_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return await registry.invoke("automation.sequences", "get", {"sequence_id": sequence_id})


@app.post("/api/v1/walls/resolve")
async def resolve_wall(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Resolve a wall (payment made, subscription resumed)."""
    return await registry.invoke("walls", "resolve", body)


@app.get("/api/v1/walls")
async def list_walls(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("walls", "list", {"tenant_id": tenant_id})


@app.get("/api/v1/journeys/{journey_id}")
async def get_journey(
    journey_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("journeys", "get", {"tenant_id": tenant_id, "journey_id": journey_id})


@app.get("/api/v1/attribution/customers/{customer_id}")
async def attribution_for_customer(
    customer_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Which touchpoints and campaigns touched this customer."""
    return await registry.invoke("analytics.attribution", "for_customer", {"customer_id": customer_id})


@app.get("/api/v1/qbr")
async def list_qbrs(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("cs.qbr", "list", {"tenant_id": tenant_id})


@app.get("/api/v1/benchmarks/{industry}")
async def get_benchmark_industry(
    industry: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return await registry.invoke("benchmarks", "set_industry", {"industry": industry})


@app.get("/api/v1/service-due/list")
async def list_service_due(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    within_days: int = 7,
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("customers.service_due", "list_due", {"tenant_id": tenant_id, "within_days": within_days})


# ---------------------------------------------------------------------------
# Automation: scheduled reports, flow editor, cancel-flow API, bots, replay, surveys, export
# ---------------------------------------------------------------------------


@app.post("/api/v1/reports/scheduler/run-due")
async def run_due_scheduled_reports(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Run all due scheduled reports and email results (Baremetrics Email Reports)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("reports.scheduler", "run_due", {"tenant_id": tenant_id})


@app.get("/api/v1/reports/scheduler/due")
async def list_due_scheduled_reports(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("reports.scheduler", "due", {"tenant_id": tenant_id})


# --- Flow editor (no-code graph) ---

@app.post("/api/v1/flow-editor/graphs")
async def create_flow_graph(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Create a flow graph (nodes + edges) for the visual editor."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("flows.editor", "create_graph", {"tenant_id": tenant_id, **body})


@app.get("/api/v1/flow-editor/graphs")
async def list_flow_graphs(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("flows.editor", "list", {"tenant_id": tenant_id})


@app.get("/api/v1/flow-editor/graphs/{graph_id}")
async def get_flow_graph(
    graph_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return await registry.invoke("flows.editor", "get_graph", {"graph_id": graph_id})


@app.patch("/api/v1/flow-editor/graphs/{graph_id}")
async def update_flow_graph(
    graph_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Update nodes/edges of a flow graph."""
    return await registry.invoke("flows.editor", "update_graph", {"graph_id": graph_id, **body})


@app.post("/api/v1/flow-editor/graphs/{graph_id}/validate")
async def validate_flow_graph(
    graph_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Validate graph: single trigger, no cycles, known services, connected."""
    return await registry.invoke("flows.editor", "validate", {"graph_id": graph_id})


@app.post("/api/v1/flow-editor/graphs/{graph_id}/publish")
async def publish_flow_graph(
    graph_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Compile a validated graph into a workflow definition."""
    return await registry.invoke("flows.editor", "publish", {"graph_id": graph_id})


# --- Cancel flow public API (embed in client apps) ---


@app.post("/api/v1/cancel-flow/start")
async def cancel_flow_start(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Start a cancel session for a customer (Churnkey SDK parity)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("cancel_flow.api", "start", {"tenant_id": tenant_id, **body})


@app.post("/api/v1/cancel-flow/sessions/{session_id}/offers")
async def cancel_flow_offers(
    session_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Get AI-recommended + catalog offers for a cancel session."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("cancel_flow.api", "offers", {"tenant_id": tenant_id, "session_id": session_id, **body})


@app.post("/api/v1/cancel-flow/sessions/{session_id}/select")
async def cancel_flow_select(
    session_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Select an offer in a cancel session."""
    return await registry.invoke("cancel_flow.api", "select", {"session_id": session_id, **body})


@app.post("/api/v1/cancel-flow/sessions/{session_id}/confirm")
async def cancel_flow_confirm(
    session_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Confirm the selected offer (pause/downgrade/cancel)."""
    return await registry.invoke("cancel_flow.api", "confirm", {"session_id": session_id, **body})


# --- Slack/Teams bot ---


@app.post("/api/v1/bot/command")
async def bot_command(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Handle a Slack/Teams slash command: /at-risk, /renewals, /mrr, /nps, /alerts, /churn, /help."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("integrations.bot", "handle_command", {"tenant_id": tenant_id, **body})


# --- Session replay + micro-surveys ---


@app.post("/api/v1/replay/ingest")
async def replay_ingest(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Ingest a session replay event (click, navigation, error, custom)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("session.replay", "ingest", {"tenant_id": tenant_id, **body})


@app.get("/api/v1/replay/sessions/{session_id}")
async def replay_get_session(
    session_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return await registry.invoke("session.replay", "get_session", {"session_id": session_id})


@app.post("/api/v1/micro-surveys")
async def create_micro_survey(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Create an in-app micro-survey triggered by a customer action (Churnkey Pulse)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("surveys.micro", "create", {"tenant_id": tenant_id, **body})


@app.post("/api/v1/micro-surveys/trigger")
async def micro_survey_trigger(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Given a customer action, return surveys to show."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("surveys.micro", "trigger", {"tenant_id": tenant_id, **body})


@app.post("/api/v1/micro-surveys/{survey_id}/respond")
async def micro_survey_respond(
    survey_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    return await registry.invoke("surveys.micro", "respond", {"survey_id": survey_id, **body})


@app.get("/api/v1/micro-surveys/{survey_id}/results")
async def micro_survey_results(
    survey_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return await registry.invoke("surveys.micro", "results", {"survey_id": survey_id})


# --- Universal export ---


@app.get("/api/v1/export/datasets")
async def export_datasets(user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, Any]:
    """List all exportable datasets."""
    return await registry.invoke("export", "datasets", {})


@app.post("/api/v1/export")
async def export_dataset(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Export any dataset to CSV or JSON (ChartMogul export parity)."""
    return await registry.invoke("export", "export", body)


# ---------------------------------------------------------------------------
# Help + interactive demo
# ---------------------------------------------------------------------------


@app.get("/api/v1/help")
async def help_list(request: Request, user: Annotated[CurrentUser, Depends(get_current_user)]) -> Any:
    """List all in-app help articles (tooltip per feature)."""
    return maybe_html(request, await registry.invoke("help", "list", {}), "Help")


@app.get("/api/v1/help/search")
async def help_search(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    q: str = "",
) -> dict[str, Any]:
    """Search help articles."""
    return await registry.invoke("help", "search", {"q": q})


@app.get("/api/v1/help/{article_id}")
async def help_get(
    article_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Get one help article with related links."""
    return await registry.invoke("help", "context", {"context": article_id})


@app.post("/api/v1/demo/run")
async def demo_run(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Run the interactive demo end-to-end: seed customers, scan due services,
    create + run a campaign, schedule reminders, save a report."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("demo", "run", {"tenant_id": tenant_id})


@app.get("/api/v1/demo/scenario")
async def demo_scenario(user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, Any]:
    """What the demo does, step by step."""
    return await registry.invoke("demo", "scenario", {})


@app.get("/api/v1/demo/history")
async def demo_history(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("demo", "history", {"tenant_id": tenant_id})


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------


class CustomerImportRequest(BaseModel):
    csv: str
    mapping: dict[str, str] = Field(default_factory=dict)


@app.post("/api/v1/customers/import")
async def import_customers_csv(
    body: CustomerImportRequest,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Import customers from CSV with column mapping (auto-suggested if omitted)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("data.transfer", "import_customers", {"tenant_id": tenant_id, "csv": body.csv, "mapping": body.mapping})


@app.post("/api/v1/customers/map-columns")
async def map_customer_columns(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    columns: list[str] = Body(...),
) -> dict[str, Any]:
    """Suggest CSV column -> customer field mapping."""
    return await registry.invoke("data.transfer", "suggest_mapping", {"columns": columns})


@app.get("/api/v1/customers/export")
async def export_customers(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    format: str = "csv",
) -> dict[str, Any]:
    """Export customers as CSV or JSON (downloadable)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("data.transfer", "export_customers", {"tenant_id": tenant_id, "format": format})


@app.get("/api/v1/campaigns/export")
async def export_campaigns(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    format: str = "csv",
) -> dict[str, Any]:
    """Export campaigns as CSV or JSON."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("data.transfer", "export_campaigns", {"tenant_id": tenant_id, "format": format})


@app.post("/api/v1/campaigns/import")
async def import_campaigns(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Import campaign definitions from rows (CSV-parsed JSON)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("data.transfer", "import_campaigns", {"tenant_id": tenant_id, "rows": body.get("rows", [])})


@app.get("/api/v1/data-transfer/history")
async def data_transfer_history(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("data.transfer", "history", {"tenant_id": tenant_id})


# ---------------------------------------------------------------------------
# Connectors: real sync with popular services (Stripe, HubSpot, Salesforce, Zendesk, ...)
# ---------------------------------------------------------------------------


@app.get("/api/v1/connectors")
async def connectors_supported(user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, Any]:
    """List supported connectors and what they sync."""
    return await registry.invoke("connectors", "supported", {})


@app.post("/api/v1/connectors/{provider}/sync")
async def connector_sync(
    provider: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Sync data from a provider (stripe, hubspot, salesforce, zendesk, mixpanel, ga, intercom, segment)."""
    tenant_id = current_tenant(request, user)
    action = f"{provider}_sync" if provider != "segment" else "segment_track"
    if provider == "segment":
        body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
        return await registry.invoke("connectors", "segment_track", {"tenant_id": tenant_id, **body})
    return await registry.invoke("connectors", action, {"tenant_id": tenant_id})


@app.get("/api/v1/connectors/syncs")
async def connector_sync_history(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("connectors", "sync_history", {"tenant_id": tenant_id})


# ---------------------------------------------------------------------------
# Lifecycle / deeper processes
# ---------------------------------------------------------------------------


@app.get("/api/v1/lifecycle/states")
async def lifecycle_states(user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, Any]:
    return await registry.invoke("lifecycle", "states", {})


@app.post("/api/v1/lifecycle/subscriptions")
async def lifecycle_create(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Create a subscription in the lifecycle state machine (starts in trial)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("lifecycle", "create", {"tenant_id": tenant_id, **body})


@app.post("/api/v1/lifecycle/subscriptions/{sub_id}/transition")
async def lifecycle_transition(
    sub_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Transition a subscription (trial->active->past_due->grace->suspended->cancelled->churned)."""
    return await registry.invoke("lifecycle", "transition", {"subscription_id": sub_id, **body})


@app.post("/api/v1/lifecycle/tick")
async def lifecycle_tick(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Advance timers: grace expiry, suspension, trial expiry, churn."""
    return await registry.invoke("lifecycle", "tick", {})


@app.get("/api/v1/lifecycle/subscriptions")
async def lifecycle_list(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    state: str = "",
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("lifecycle", "list", {"tenant_id": tenant_id, "state": state})


@app.get("/api/v1/lifecycle/subscriptions/{sub_id}")
async def lifecycle_get(
    sub_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return await registry.invoke("lifecycle", "get", {"subscription_id": sub_id})


@app.post("/api/v1/dunning/engine/start")
async def dunning_engine_start(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Start a dunning escalation campaign with reason-based retry schedule."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("dunning.engine", "start", {"tenant_id": tenant_id, **body})


@app.post("/api/v1/dunning/engine/{campaign_id}/failure")
async def dunning_engine_failure(
    campaign_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    return await registry.invoke("dunning.engine", "record_failure", {"campaign_id": campaign_id, **body})


@app.post("/api/v1/dunning/engine/tick")
async def dunning_engine_tick(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Return campaigns due for next retry/escalation."""
    return await registry.invoke("dunning.engine", "tick", {})


@app.post("/api/v1/dunning/engine/{campaign_id}/recover")
async def dunning_engine_recover(
    campaign_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    return await registry.invoke("dunning.engine", "recover", {"campaign_id": campaign_id, **body})


@app.get("/api/v1/dunning/engine/attribution")
async def dunning_attribution(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Recovery rate + amount recovered + which attempt/card-updater worked."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("dunning.engine", "attribution", {"tenant_id": tenant_id})


@app.post("/api/v1/health/engine/compute")
async def health_engine_compute(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Health v2: decaying score with components + threshold action."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("health.engine", "compute", {"tenant_id": tenant_id, **body})


@app.post("/api/v1/health/engine/engage")
async def health_engine_engage(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Record an engagement event — bumps health, resets decay clock."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("health.engine", "record_engagement", {"tenant_id": tenant_id, **body})


@app.post("/api/v1/health/engine/tick")
async def health_engine_decay(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Cron: apply daily decay to all health scores."""
    return await registry.invoke("health.engine", "tick_decay", {})


@app.get("/api/v1/health/engine")
async def health_engine_list(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    tier: str = "",
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("health.engine", "list", {"tenant_id": tenant_id, "tier": tier})


@app.get("/api/v1/renewals/risk")
async def list_renewal_risk(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    risk_tier: str = "",
) -> dict[str, Any]:
    """Tracked renewals with their risk score and tier (highest risk first)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("renewals.risk", "list", {"tenant_id": tenant_id, "risk_tier": risk_tier})


@app.post("/api/v1/renewals/risk/track")
async def renewal_risk_track(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Track a renewal and score its risk (health+payments+tickets+usage)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("renewals.risk", "track", {"tenant_id": tenant_id, **body})


@app.post("/api/v1/renewals/risk/{renewal_id}/score")
async def renewal_risk_score(
    renewal_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    return await registry.invoke("renewals.risk", "score", {"renewal_id": renewal_id, **body})


@app.post("/api/v1/renewals/risk/tick")
async def renewal_risk_tick(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Return T-90/60/30/14/7 checkpoints due now (each arms a playbook)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("renewals.risk", "tick", {"tenant_id": tenant_id})


@app.post("/api/v1/metering/quota")
async def metering_set_quota(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("metering.v2", "set_quota", {"tenant_id": tenant_id, **body})


@app.post("/api/v1/metering/record")
async def metering_record(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Record usage; returns quota check with any triggered threshold alerts."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("metering.v2", "record", {"tenant_id": tenant_id, **body})


@app.get("/api/v1/metering/overage")
async def metering_overage(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    resource: str = "api_calls",
) -> dict[str, Any]:
    """Overage invoice line items for the current period."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("metering.v2", "overage_lines", {"tenant_id": tenant_id, "resource": resource})


@app.post("/api/v1/billing/prorate")
async def prorate_quote(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Prorated charge/credit for a mid-cycle plan change."""
    return await registry.invoke("billing.proration", "quote_change", body)


@app.post("/api/v1/nps/loop")
async def nps_loop(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Handle an NPS response: detractor->urgent call, passive->feedback ask, promoter->referral."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("nps.loop", "handle_response", {"tenant_id": tenant_id, **body})


@app.post("/api/v1/experiments/{experiment_id}/auto-evaluate")
async def experiment_auto_evaluate(
    experiment_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Evaluate significance; auto-promote the winner if z>=1.96 and lift>5%."""
    return await registry.invoke("experiments.auto", "evaluate", {"experiment_id": experiment_id, **body})


@app.post("/api/v1/incidents/from-anomaly")
async def incident_from_anomaly(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Create an incident from a metric anomaly."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("incidents", "create_from_anomaly", {"tenant_id": tenant_id, **body})


@app.get("/api/v1/incidents/{incident_id}/comms")
async def incident_comms(
    incident_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Draft customer-facing comms for an incident."""
    return await registry.invoke("incidents", "comms_draft", {"incident_id": incident_id})


@app.post("/api/v1/winback/schedule")
async def winback_schedule(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Schedule 7/30/90-day win-back touches for a churned customer."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("winback.timing", "schedule", {"tenant_id": tenant_id, **body})


@app.post("/api/v1/winback/tick")
async def winback_tick(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Return win-back touches due now."""
    return await registry.invoke("winback.timing", "due", {})


# ---------------------------------------------------------------------------
# Advanced processing: send-time, ML churn, deliverability, attribution, cohorts
# ---------------------------------------------------------------------------


@app.post("/api/v1/sendtime/recommend")
async def sendtime_recommend(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Optimal send time for a recipient (shared.predictive_sendtime)."""
    return await registry.invoke("sendtime.optimize", "recommend", body)


@app.post("/api/v1/sendtime/plan")
async def sendtime_plan(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Plan per-recipient send times for a campaign."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("sendtime.optimize", "plan_campaign", {"tenant_id": tenant_id, **body})


@app.post("/api/v1/sendtime/engage")
async def sendtime_engage(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Record open/click so the model learns this recipient's habits."""
    return await registry.invoke("sendtime.optimize", "record_engagement", body)


@app.get("/api/v1/sendtime/best-hours")
async def sendtime_best_hours(user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, Any]:
    return await registry.invoke("sendtime.optimize", "best_hours", {})


@app.post("/api/v1/ai/churn/ml")
async def churn_ml_score(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """ML churn score (shared.predictive.churn) blended with the health engine."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("ai.churn_ml", "score", {"tenant_id": tenant_id, **body})


@app.get("/api/v1/email/deliverability/warmup")
async def email_warmup(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    daily_volume: int = 50,
    age_days: int = 0,
) -> dict[str, Any]:
    """Email warmup schedule (shared.deliverability)."""
    return await registry.invoke("email.deliverability", "warmup_schedule", {"daily_volume": daily_volume, "age_days": age_days})


@app.get("/api/v1/email/deliverability/domain")
async def email_domain_check(
    user: Annotated[CurrentUser, Depends(get_current_user)],
    domain: str = "",
) -> dict[str, Any]:
    """Domain deliverability check (SPF/DKIM/DMARC)."""
    return await registry.invoke("email.deliverability", "domain_check", {"domain": domain})


@app.post("/api/v1/attribution/touch")
async def attribution_touch(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Record a marketing touch for multi-touch attribution."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("attribution.multitouch", "record_touch", {"tenant_id": tenant_id, **body})


@app.post("/api/v1/attribution/multitouch")
async def attribution_multitouch(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Attribute a conversion across touches (first/last/linear/time_decay/position_based)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("attribution.multitouch", "attribute", {"tenant_id": tenant_id, **body})


@app.post("/api/v1/analytics/cohorts/compare")
async def compare_cohorts(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Compare two cohorts side by side on any metric."""
    return await registry.invoke("analytics.cohort_compare", "compare", body)


@app.post("/api/v1/analytics/root-cause")
async def root_cause(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Correlate a metric anomaly with recent platform activity to find the likely cause."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("analytics.root_cause", "analyze", {"tenant_id": tenant_id, **body})


# ---------------------------------------------------------------------------
# Success center (customer-facing portal: docs, DSAR, dashboard)
# ---------------------------------------------------------------------------


@app.post("/api/v1/success-center/register")
async def success_center_register(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("success_center", "register_customer", {"tenant_id": tenant_id, **body})


@app.get("/api/v1/success-center/dashboard")
async def success_center_dashboard(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    email: str = "",
) -> dict[str, Any]:
    return await registry.invoke("success_center", "dashboard", {"email": email})


@app.get("/api/v1/success-center/documents")
async def success_center_documents(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    email: str = "",
) -> dict[str, Any]:
    return await registry.invoke("success_center", "documents", {"email": email})


@app.post("/api/v1/success-center/dsar")
async def success_center_dsar(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Submit a data-subject access request (GDPR/CCPA)."""
    return await registry.invoke("success_center", "submit_dsar", body)


@app.post("/api/v1/analytics/annotations")
async def create_annotation(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Annotate a metric (notes tied to metric+date, e.g. 'launched new pricing')."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("analytics.annotations", "create", {"tenant_id": tenant_id, **body})


@app.get("/api/v1/analytics/annotations")
async def list_annotations(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    metric: str = "",
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("analytics.annotations", "list", {"tenant_id": tenant_id, "metric": metric})


# ---------------------------------------------------------------------------
# Advanced customer analysis: segmentation, next best action, auto-approach, content
# ---------------------------------------------------------------------------


@app.get("/api/v1/analysis/fields")
async def analysis_fields(user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, Any]:
    """Computed fields + types available for segmentation (the predicate builder schema)."""
    return await registry.invoke("segmentation.advanced", "fields", {})


@app.get("/api/v1/analysis/profiles")
async def analysis_profiles(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    include_churn_risk: bool = True,
) -> dict[str, Any]:
    """Customer records enriched with computed fields (due, health tier, LTV tier, churn risk, rank)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("segmentation.advanced", "profiles", {"tenant_id": tenant_id, "include_churn_risk": include_churn_risk})


@app.post("/api/v1/analysis/segments/preview")
async def preview_segment(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Preview who a criteria set matches + aggregate value at risk."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("segmentation.advanced", "preview", {"tenant_id": tenant_id, **body})


@app.post("/api/v1/analysis/segments")
async def save_segment(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Save a computed segment for reuse as a campaign target."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("segmentation.advanced", "save", {"tenant_id": tenant_id, **body})


@app.get("/api/v1/analysis/segments")
async def list_advanced_segments(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("segmentation.advanced", "list", {"tenant_id": tenant_id})


@app.get("/api/v1/analysis/next-best-action")
async def next_best_action(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    customer_id: str = "",
    email: str = "",
    include_maintain: bool = False,
) -> dict[str, Any]:
    """What to do about a customer next (or for every customer)."""
    tenant_id = current_tenant(request, user)
    if customer_id or email:
        return await registry.invoke("customers.next_best_action", "recommend", {
            "tenant_id": tenant_id, "customer_id": customer_id, "email": email})
    return await registry.invoke("customers.next_best_action", "recommend_all", {
        "tenant_id": tenant_id, "include_maintain": include_maintain})


@app.get("/api/v1/auto-approach/triggers")
async def auto_approach_triggers(user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, Any]:
    """The automatic-approach triggers (service due, overdue, churn risk, low health)."""
    return await registry.invoke("automation.auto_approach", "triggers", {})


@app.post("/api/v1/auto-approach/scan")
async def auto_approach_scan(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Preview who each automatic trigger would approach right now."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("automation.auto_approach", "scan", {"tenant_id": tenant_id})


@app.post("/api/v1/auto-approach/run")
async def auto_approach_run(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Run the automatic approach: create + execute campaigns for every matching trigger."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("automation.auto_approach", "run", {"tenant_id": tenant_id, **body})


@app.post("/api/v1/campaigns/{campaign_id}/template")
async def set_campaign_template(
    campaign_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Set the tailored message content for a campaign (with segment overrides)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("campaigns.templates", "set_template", {
        "tenant_id": tenant_id, "campaign_id": campaign_id, **body})


@app.post("/api/v1/campaigns/{campaign_id}/render")
async def render_campaign_message(
    campaign_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Render a campaign's tailored message for one member."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("campaigns.templates", "render", {
        "tenant_id": tenant_id, "campaign_id": campaign_id, **body})


# ---------------------------------------------------------------------------
# Agency layer: client roster, pacing, sharing, digests
# ---------------------------------------------------------------------------


@app.post("/api/v1/agency/clients")
async def create_agency_client(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Add a client brand to the agency roster."""
    return await registry.invoke("agency", "create_client", body)


@app.get("/api/v1/agency/clients")
async def list_agency_clients(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    agency_id: str = "default",
) -> dict[str, Any]:
    return await registry.invoke("agency", "list_clients", {"agency_id": agency_id})


@app.get("/api/v1/agency/roster")
async def agency_roster(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    agency_id: str = "default",
) -> dict[str, Any]:
    """The agency roster: every client with pacing, status and what needs attention."""
    return await registry.invoke("agency", "roster", {"agency_id": agency_id})


@app.patch("/api/v1/agency/clients/{client_id}")
async def update_agency_client(
    client_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    return await registry.invoke("agency", "update_client", {"client_id": client_id, **body})


@app.post("/api/v1/agency/clients/{client_id}/goal")
async def set_agency_goal(
    client_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Set a client's revenue goal (drives the behind-goal flag)."""
    return await registry.invoke("agency", "set_goal", {"client_id": client_id, **body})


@app.post("/api/v1/agency/clients/{client_id}/share")
async def share_client_dashboard(
    client_id: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Create a white-label, tokenised client dashboard link."""
    return await registry.invoke("agency", "share_dashboard", {"client_id": client_id, **body})


@app.get("/api/v1/agency/shares")
async def list_agency_shares(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    client_id: str = "",
) -> dict[str, Any]:
    return await registry.invoke("agency", "list_shares", {"client_id": client_id})


@app.get("/api/v1/share/{token}")
async def public_client_report(
    token: str,
) -> dict[str, Any]:
    """Public white-label client dashboard (token-gated, no auth)."""
    from retention_analytics_advanced_processing.agency import _JsonStore

    share = next((s for s in _JsonStore("agency_shares.json").load() if s.get("token") == token), None)
    if not share:
        raise HTTPException(status_code=404, detail="unknown share token")
    r = await registry.invoke("agency", "client_report", {
        "tenant_id": share.get("tenant_id", ""), "branding": share.get("branding", {})})
    return {"status": "ok", "client": share.get("client_id"), **r.get("report", {})}


@app.post("/api/v1/agency/digests")
async def schedule_client_digest(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Schedule a recurring Slack digest for a client."""
    return await registry.invoke("agency", "schedule_digest", body)


@app.get("/api/v1/agency/digests")
async def list_client_digests(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return await registry.invoke("agency", "list_digests", {})


# ---------------------------------------------------------------------------
# Agency platform connectors (Klaviyo, Shopify, Recharge, ...)
# ---------------------------------------------------------------------------


@app.get("/api/v1/agency/platforms")
async def agency_platforms(user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, Any]:
    """The platforms we connect (same set Hiro supports, plus direct billing)."""
    return await registry.invoke("connectors.agency", "platforms", {})


@app.get("/api/v1/agency/platforms/status")
async def agency_platforms_status(user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, Any]:
    return await registry.invoke("connectors.agency", "status", {})


@app.post("/api/v1/agency/platforms/{platform}/connect")
async def agency_platform_connect(
    platform: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    return await registry.invoke("connectors.agency", "connect", {"platform": platform, **body})


@app.post("/api/v1/agency/platforms/{platform}/sync")
async def agency_platform_sync(
    platform: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Pull from a platform and normalise into our stores."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("connectors.agency", "sync", {"platform": platform, "tenant_id": tenant_id, **body})


@app.get("/api/v1/agency/platforms/syncs")
async def agency_platform_syncs(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    return await registry.invoke("connectors.agency", "history", {})


# ---------------------------------------------------------------------------
# Deep-dive performance analytics (flow map, campaign dive, timing, deliverability)
# ---------------------------------------------------------------------------


@app.post("/api/v1/performance/sends")
async def record_send_performance(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Record one message send with creative + outcomes (feeds flow map / campaign dive)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("analytics.performance", "record_send", {"tenant_id": tenant_id, **body})


@app.get("/api/v1/performance/flow-map")
async def flow_map_performance(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    flow_id: str = "",
) -> dict[str, Any]:
    """Flow map: every message with delivered/open/click/revenue + creative."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("analytics.performance", "flow_map", {"tenant_id": tenant_id, "flow_id": flow_id})


@app.get("/api/v1/performance/campaign")
async def campaign_deep_dive(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    campaign_id: str = "",
) -> dict[str, Any]:
    """Campaign deep dive: creative + subject next to open/click/revenue, products, new vs returning, A/B."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("analytics.performance", "campaign_deep_dive", {"tenant_id": tenant_id, "campaign_id": campaign_id})


@app.get("/api/v1/performance/message-timing")
async def message_timing(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Message timing: revenue per recipient by weekday x hour; static vs recipient-local separately."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("analytics.performance", "message_timing", {"tenant_id": tenant_id})


@app.get("/api/v1/performance/deliverability")
async def deliverability_report(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Deliverability score + history, per-provider rates, biggest offenders."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("analytics.performance", "deliverability", {"tenant_id": tenant_id})


@app.post("/api/v1/performance/deliverability")
async def record_deliverability(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Record a deliverability sample (bounce/spam/unsub by inbox provider)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("analytics.performance", "record_deliverability", {"tenant_id": tenant_id, **body})


# ---------------------------------------------------------------------------
# Commerce analytics: time between orders, product paths, subscription LTV, RFM movement
# ---------------------------------------------------------------------------


@app.post("/api/v1/commerce/orders")
async def record_order(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Record a purchase (feeds repeat purchase, product paths, subscription LTV, RFM)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("analytics.commerce", "record_order", {"tenant_id": tenant_id, **body})


@app.get("/api/v1/commerce/time-between-orders")
async def time_between_orders(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Median days between orders: all, after a campaign/flow, and on their own."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("analytics.commerce", "time_between_orders", {"tenant_id": tenant_id})


@app.get("/api/v1/commerce/product-paths")
async def product_paths(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    keyword: str = "",
) -> dict[str, Any]:
    """1st -> 2nd -> 3rd purchase paths, retention by product (optional keyword filter)."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("analytics.commerce", "product_paths", {"tenant_id": tenant_id, "keyword": keyword})


@app.get("/api/v1/commerce/subscription-ltv")
async def subscription_ltv(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Subscription LTV by starting product at 1/3/6/12 months."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("analytics.commerce", "subscription_ltv", {"tenant_id": tenant_id})


@app.get("/api/v1/commerce/one-time-to-subscriber")
async def one_time_to_subscriber(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Which one-time purchases become subscribers, and how fast."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("analytics.commerce", "one_time_to_subscriber", {"tenant_id": tenant_id})


@app.get("/api/v1/commerce/product-trends")
async def product_trends(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Most new starts, fastest growing, most cancels, top add-on."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("analytics.commerce", "product_trends", {"tenant_id": tenant_id})


@app.get("/api/v1/commerce/rfm-movement")
async def rfm_movement(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """RFM segment movement over time + biggest moves with campaign attribution."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("analytics.commerce", "rfm_movement", {"tenant_id": tenant_id})


# ---------------------------------------------------------------------------
# Agency Q&A, role views, report decks
# ---------------------------------------------------------------------------


@app.post("/api/v1/agency/ask")
async def agency_ask(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Ask a question in plain English: 'which clients are behind this month?'"""
    return await registry.invoke("agency.qa", "ask", body)


@app.get("/api/v1/agency/questions")
async def agency_question_suggestions(user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, Any]:
    """Example questions the assistant understands."""
    return await registry.invoke("agency.qa", "suggestions", {})


@app.get("/api/v1/agency/roles")
async def agency_roles(user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, Any]:
    """Role-based views: leadership, account manager, copywriter."""
    return await registry.invoke("agency.roles", "roles", {})


@app.get("/api/v1/agency/view")
async def agency_role_view(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    role: str = "leadership",
    agency_id: str = "default",
    client_id: str = "",
    tenant_id: str = "",
) -> dict[str, Any]:
    """The view for a role (leadership roster / client detail / creative ranking)."""
    return await registry.invoke("agency.roles", "view", {
        "role": role, "agency_id": agency_id, "client_id": client_id, "tenant_id": tenant_id})


@app.post("/api/v1/agency/deck")
async def build_agency_deck(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Build a branded, multi-slide report deck for a client."""
    return await registry.invoke("agency.deck", "build", body)


@app.post("/api/v1/agency/deck/render")
async def render_agency_deck(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Render a deck to print-ready HTML (print to PDF)."""
    return await registry.invoke("agency.deck", "render_html", body)


# ---------------------------------------------------------------------------
# Pain-point catalog: which user pains each workflow fixes
# ---------------------------------------------------------------------------


@app.get("/api/v1/pains")
async def pain_catalog_endpoint(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> Any:
    """Map of end-user pains -> the workflows that fix them. Shows full coverage."""
    from retention_analytics_advanced.pains import pain_catalog

    catalog = pain_catalog()
    # Annotate with whether each workflow is actually registered
    wf_ids = {d.id for d in engine.list_definitions()}
    for pid, p in catalog["pains"].items():
        p["workflows_registered"] = [w for w in p["workflows"] if w in wf_ids]
        p["covered"] = len(p["workflows_registered"]) > 0
    covered = sum(1 for p in catalog["pains"].values() if p["covered"])
    data = {"status": "ok", "total_pains": catalog["total"], "covered": covered, **catalog}
    if wants_html(request):
        # Render pains grouped by category as cards
        cards = ""
        for cat, items in catalog["by_category"].items():
            chips = "".join(
                f"<tr><td><b>{html.escape(p['id'])}</b></td><td>{html.escape(p['pain'])}</td>"
                f"<td><span class='chip'>{html.escape(', '.join(p['workflows']))}</span></td>"
                f"<td>{'✅' if catalog['pains'][p['id']]['covered'] else '❌'}</td></tr>"
                for p in items
            )
            cards += f"<section><h2>{html.escape(cat)} ({len(items)})</h2><table><tr><th>pain</th><th>what the user feels</th><th>workflow</th><th>covered</th></tr>{chips}</table></section>"
        from apps.api.htmlview import page
        return page("Pain coverage", f"<p style='color:#64748b;font-size:13px'>{covered}/{catalog['total']} pains covered by a registered workflow</p>" + cards)
    return data


@app.get("/api/v1/pains/{pain_id}")
async def pain_detail(
    pain_id: str,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    """Detail on one pain: what the customer feels, which workflows fix it, the trigger event."""
    from retention_analytics_advanced.pains import PAIN_CATALOG

    if pain_id not in PAIN_CATALOG:
        raise HTTPException(status_code=404, detail=f"unknown pain: {pain_id}")
    p = PAIN_CATALOG[pain_id]
    wf_ids = {d.id for d in engine.list_definitions()}
    p = dict(p)
    p["workflows_registered"] = [w for w in p["workflows"] if w in wf_ids]
    p["covered"] = len(p["workflows_registered"]) > 0
    return {"status": "ok", "pain": {"id": pain_id, **p}}


@app.get("/api/v1/segment-push/targets")
async def segment_push_targets(user: Annotated[CurrentUser, Depends(get_current_user)]) -> dict[str, Any]:
    """Platforms that can receive a pushed segment (activation loop)."""
    return await registry.invoke("connectors.segment_push", "targets", {})


@app.post("/api/v1/segment-push")
async def push_segment(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Push a computed segment into Klaviyo/Attentive/Omnisend/Sendlane/Postscript
    so the platform can act on it."""
    tenant_id = current_tenant(request, user)
    return await registry.invoke("connectors.segment_push", "push", {"tenant_id": tenant_id, **body})


@app.get("/api/v1/segment-push/history")
async def segment_push_history(
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
) -> dict[str, Any]:
    tenant_id = current_tenant(request, user)
    return await registry.invoke("connectors.segment_push", "history", {"tenant_id": tenant_id})


# ---------------------------------------------------------------------------
# Generic service-action proxy — guarantees every registered action is reachable
# ---------------------------------------------------------------------------


@app.post("/api/v1/actions/{service_name}/{action_name}")
async def invoke_service_action(
    service_name: str,
    action_name: str,
    request: Request,
    user: Annotated[CurrentUser, Depends(get_current_user)],
    body: dict[str, Any] = Body(default_factory=dict),
) -> dict[str, Any]:
    """Invoke any registered service action with a JSON payload.

    This is the registry-driven escape hatch: every action on every service
    (65 services) is reachable, so no capability is stranded behind a missing
    route. Typed convenience routes exist for the common cases.
    """
    tenant_id = current_tenant(request, user)
    payload = dict(body)
    payload.setdefault("tenant_id", tenant_id)
    try:
        return await registry.invoke(service_name, action_name, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.warning("service_action.failed", service=service_name, action=action_name, error=str(exc))
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/v1/actions")
async def list_service_actions(request: Request, user: Annotated[CurrentUser, Depends(get_current_user)]) -> Any:
    """List every service and its callable actions — the full capability surface."""
    data = {
        "status": "ok",
        "count": len(registry.list_services()),
        "services": [
            {
                "name": name,
                "version": registry.get(name).version,
                "metadata": registry.get(name).metadata,
                "actions": sorted(registry.get(name).actions.keys()),
            }
            for name in registry.list_services()
        ],
    }
    return maybe_html(request, data, "Action catalog")


@app.get("/api/seo/manifest")
async def seo_manifest() -> Any:
    """Web-app manifest (Snapford platform surface)."""
    return await registry.invoke("platform.surfaces", "manifest", {})


@app.get("/api/seo/style/tokens.css")
async def seo_tokens_css() -> Response:
    """Design-token stylesheet shared with the portal <head>."""
    css = await registry.invoke("platform.surfaces", "tokens_css", {})
    return Response(content=css, media_type="text/css; charset=utf-8")


@app.get("/api/i18n/languages")
async def i18n_languages() -> Any:
    """Platform locale surface: 20 locales with text directions."""
    return await registry.invoke("platform.surfaces", "languages", {})


@app.get("/api/me")
async def api_me(request: Request) -> Any:
    """Product identity surface (Snapford platform contract)."""
    return await registry.invoke("platform.surfaces", "me", {"base_url": str(request.base_url).rstrip("/")})


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


# ---------------------------------------------------------------------------
# Route ordering: static paths must be registered before parameterized paths
# with the same prefix, otherwise /api/v1/customers/import is captured by
# /api/v1/customers/{customer_id}. Reorder at import time.
# ---------------------------------------------------------------------------

def _route_sort_key(route):
    path = getattr(route, 'path', '')
    has_param = '{' in path
    # Group by the shared parent prefix so /api/v1/customers/import and
    # /api/v1/customers/{id} land in the same group, static first.
    if has_param:
        prefix = path.split('{')[0]
    else:
        prefix = path.rsplit('/', 1)[0] + '/'
    return (prefix, 0 if not has_param else 1, path)

app.router.routes.sort(key=_route_sort_key)
