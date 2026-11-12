"""Tests for competitor-parity workflows and growth services.

Covers the 15 workflows and 6 services added from competitor research
(Baremetrics, Churnkey, ChurnZero, Vitally).
"""

from __future__ import annotations

import uuid

import pytest

from apps.api.workflows_seed import build_workflows, workflow_event_bindings
from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_core.workflows.engine import WorkflowEngine
from retention_analytics_engagement.email.service import EmailService
from retention_analytics_engagement.sms.service import SmsService
from retention_analytics_ecommerce.core.service import EcommerceCoreService
from retention_analytics_ecommerce.subscriptions.service import SubscriptionService
from retention_analytics_growth.service import (
    DunningService,
    ForecastingService,
    HealthScoringService,
    InAppMessagingService,
    SegmentationService,
    SurveyService,
)
from retention_analytics_templates.service import TemplateService
from retention_analytics_analytics_core.metric_service import MetricService

TENANT = "00000000-0000-0000-0000-000000000001"

COMPETITOR_WORKFLOWS = [
    "dunning-campaign", "cancel-flow", "subscription-pause", "annual-upsell",
    "expansion-opportunity", "reactivation", "nps-survey", "health-score-alert",
    "feature-adoption", "renewal-reminder", "trial-conversion", "downgrade-save",
    "referral-ask", "onboarding-milestone", "usage-drop-alert",
]


@pytest.fixture
def registry() -> ServiceRegistry:
    return ServiceRegistry()


@pytest.fixture
def engine(registry: ServiceRegistry) -> WorkflowEngine:
    for svc in (EmailService(registry), SmsService(registry), SubscriptionService(registry),
                EcommerceCoreService(registry), MetricService(registry)):
        try:
            svc.register()
        except ValueError:
            pass
    TemplateService(registry)
    for svc in (HealthScoringService(registry), DunningService(registry), SurveyService(registry),
                ForecastingService(registry), SegmentationService(registry), InAppMessagingService(registry)):
        svc.register()
    return WorkflowEngine(registry)


def test_all_workflows_registered() -> None:
    wfs = build_workflows()
    ids = [w.id for w in wfs]
    assert len(wfs) == 37, f"expected 37 workflows, got {len(wfs)}: {ids}"
    for wid in COMPETITOR_WORKFLOWS:
        assert wid in ids, f"missing competitor workflow: {wid}"
    # Universal service-lifecycle workflows
    for wid in ["service-due-reminder", "service-overdue", "cross-sell", "drip-sequence", "low-effort-score"]:
        assert wid in ids, f"missing universal workflow: {wid}"
    # Pain-point workflows
    for wid in ["login-lockout", "error-apology", "support-ack", "support-resolved-followup",
                "price-change-notice", "invoice-delivery", "quota-warning", "never-logged-in",
                "stuck-onboarding", "back-in-stock", "price-drop-alert", "security-alert", "invite-activation"]:
        assert wid in ids, f"missing pain-point workflow: {wid}"


def test_all_event_bindings_present() -> None:
    bindings = workflow_event_bindings()
    expected_events = [
        "payment.failed", "cancel.flow_started", "subscription.paused",
        "upsell.annual_eligible", "account.seat_overage", "client.reactivated",
        "survey.nps_due", "health.score_low", "feature.unused",
        "subscription.renewal_due", "trial.ending", "subscription.downgraded",
        "referral.eligible", "onboarding.milestone", "usage.dropped",
    ]
    for ev in expected_events:
        assert ev in bindings, f"missing event binding: {ev}"


@pytest.mark.asyncio
@pytest.mark.parametrize("wf_id", COMPETITOR_WORKFLOWS)
async def test_competitor_workflow_runs(registry: ServiceRegistry, engine: WorkflowEngine, wf_id: str) -> None:
    for w in build_workflows():
        engine.register_definition(w)
    run = await engine.run(
        wf_id, TENANT,
        initial_context={"email": "test@competitor.com", "phone": "+15550000000", "client_id": "c1",
                          "subscription_id": "sub-1", "cart_id": "cart-1", "campaign_id": "dun-1",
                          "amount_due": 99, "score": 30, "usage_score": 20, "days_left": 7},
    )
    assert run.status == "completed", f"workflow {wf_id} failed: {run.error}"


@pytest.mark.asyncio
async def test_health_scoring(registry: ServiceRegistry) -> None:
    HealthScoringService(registry).register()
    r = await registry.invoke("health.scoring", "compute", {
        "tenant_id": TENANT, "client_id": "c1",
        "usage_score": 20, "support_score": 30, "payment_score": 100, "engagement_score": 10,
    })
    assert r["result"]["score"] < 50
    assert r["result"]["tier"] in ("at_risk", "critical")

    r = await registry.invoke("health.scoring", "list_low", {"tenant_id": TENANT, "threshold": 50})
    assert r["count"] >= 1


@pytest.mark.asyncio
async def test_dunning_campaign(registry: ServiceRegistry) -> None:
    DunningService(registry).register()
    r = await registry.invoke("dunning", "start_campaign", {
        "tenant_id": TENANT, "subscription_id": "sub-1", "customer_email": "a@b.com", "amount_due": 99,
    })
    assert r["status"] == "started"
    assert r["retry_schedule_days"] == [1, 3, 5, 7, 10]

    r = await registry.invoke("dunning", "schedule_retry", {"campaign_id": r["campaign"]["campaign_id"], "attempt": 3})
    assert "next_retry_at" in r
    assert r["channel"] == "email+sms"

    r = await registry.invoke("dunning", "list_active", {"tenant_id": TENANT})
    assert r["count"] >= 1


@pytest.mark.asyncio
async def test_survey_nps(registry: ServiceRegistry, tmp_path, monkeypatch) -> None:
    import retention_analytics_core.repository as repo_mod
    monkeypatch.setattr(repo_mod, "data_root", lambda: tmp_path)
    SurveyService(registry).register()
    tenant = f"nps-test-{uuid.uuid4().hex[:8]}"
    r1 = await registry.invoke("surveys", "send_nps", {"tenant_id": tenant, "client_id": "c1", "customer_email": "a@b.com"})
    r2 = await registry.invoke("surveys", "send_nps", {"tenant_id": tenant, "client_id": "c2", "customer_email": "b@c.com"})

    await registry.invoke("surveys", "record_response", {"survey_id": r1["survey"]["survey_id"], "score": 10, "comment": "Love it"})
    await registry.invoke("surveys", "record_response", {"survey_id": r2["survey"]["survey_id"], "score": 5})

    r = await registry.invoke("surveys", "compute_nps", {"tenant_id": tenant})
    assert r["nps"] is not None
    assert r["responses"] == 2
    assert r["nps"] == 0.0  # 1 promoter, 1 detractor


@pytest.mark.asyncio
async def test_forecasting(registry: ServiceRegistry) -> None:
    ForecastingService(registry).register()
    r = await registry.invoke("forecasting", "forecast_mrr", {
        "current_mrr": 10000, "monthly_growth_rate": 0.10, "monthly_churn_rate": 0.03, "months": 12,
    })
    assert len(r["forecast"]) == 12
    assert r["projected_mrr_12m"] > 10000


@pytest.mark.asyncio
async def test_segmentation(registry: ServiceRegistry) -> None:
    SegmentationService(registry).register()
    r = await registry.invoke("segmentation", "define_segment", {
        "tenant_id": TENANT, "name": "At-risk SaaS", "criteria": {"health_score": "<50", "plan": "growth"},
    })
    assert r["status"] == "defined"
    r = await registry.invoke("segmentation", "list_segments", {"tenant_id": TENANT})
    assert len(r["segments"]) >= 1


@pytest.mark.asyncio
async def test_inapp_messaging(registry: ServiceRegistry) -> None:
    InAppMessagingService(registry).register()
    r = await registry.invoke("inapp.messaging", "send_banner", {
        "tenant_id": TENANT, "client_id": "c1", "title": "New feature", "body": "Try it now",
    })
    assert r["status"] == "sent"
    r = await registry.invoke("inapp.messaging", "start_walkthrough", {
        "tenant_id": TENANT, "client_id": "c1", "steps": ["Step 1", "Step 2"],
    })
    assert r["status"] == "started"
