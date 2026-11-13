"""Tests for production-readiness Phases 1-8: SaaS metrics, AI, CS ops, integrations, compliance."""

from __future__ import annotations

import uuid

import pytest

from retention_analytics_core.service_registry import ServiceRegistry
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
)
from retention_analytics_compliance.service import AuditExportService, PrivacyService, SSOService

TENANT = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def registry(tmp_path, monkeypatch) -> ServiceRegistry:
    import retention_analytics_core.repository as repo_mod
    monkeypatch.setattr(repo_mod, "data_root", lambda: tmp_path)
    reg = ServiceRegistry()
    for cls in (SaasMetricsService, PredictiveChurnService, FeedbackAIService, OfferRecommendationService,
                SuccessPlanService, PlaybookService, AlertService, RenewalHubService, CommandCenterService,
                IntegrationRegistryService, SlackAlertService, WebhookManagementService,
                PrivacyService, AuditExportService, SSOService):
        cls(reg).register()
    return reg


# Phase 1: SaaS metrics
@pytest.mark.asyncio
async def test_saas_metrics_all(registry: ServiceRegistry) -> None:
    subs = [
        {"status": "active", "amount": 100, "is_new": True},
        {"status": "active", "amount": 200, "expansion": 50},
        {"status": "cancelled", "amount": 50, "churned_this_month": True},
    ]
    r = await registry.invoke("saas.metrics", "compute_all", {
        "tenant_id": TENANT, "subscriptions": subs,
        "starting_mrr": 1000, "churned_mrr": 50, "contraction_mrr": 10, "expansion_mrr": 60,
        "arpu": 50, "monthly_churn_rate": 0.05, "sales_marketing_spend": 5000, "new_customers": 20,
        "active_customers": 20, "cac": 250, "gross_margin": 0.8, "starting_customers": 100, "churned_customers": 5,
        "new_mrr": 100,
    })
    m = r["metrics"]
    assert m["mrr"]["mrr"] == 300
    assert m["arr"]["arr"] == 3600
    assert m["grr"]["grr"] == 94.0  # (1000-50-10)/1000
    assert m["nrr"]["nrr"] == 100.0  # (1000+60-50-10)/1000
    assert m["ltv"]["ltv"] == 1000  # 50/0.05
    assert m["cac"]["cac"] == 250
    assert m["logo_retention"]["rate"] == 95.0
    assert m["quick_ratio"]["growing"] is True


# Phase 2: AI
@pytest.mark.asyncio
async def test_predictive_churn(registry: ServiceRegistry) -> None:
    r = await registry.invoke("ai.churn_predict", "predict", {
        "tenant_id": TENANT, "client_id": "c1",
        "usage_drop_pct": 80, "open_tickets": 4, "payment_failures": 2, "logins_last_30d": 1, "nps_score": 3,
    })
    assert r["prediction"]["churn_probability"] > 0.5
    assert r["prediction"]["risk_level"] in ("high", "critical")

    r = await registry.invoke("ai.churn_predict", "at_risk_list", {"tenant_id": TENANT, "threshold": 0.3})
    assert r["count"] >= 1


@pytest.mark.asyncio
async def test_feedback_classification(registry: ServiceRegistry) -> None:
    r = await registry.invoke("ai.feedback", "classify", {
        "tenant_id": TENANT, "text": "Your pricing is too expensive, I want to cancel", "mrr": 500,
    })
    assert r["classification"]["category"] == "pricing"

    r = await registry.invoke("ai.feedback", "classify", {"tenant_id": TENANT, "text": "The app crashes every time I save"})
    assert r["classification"]["category"] == "bugs"

    await registry.invoke("ai.feedback", "classify", {"tenant_id": TENANT, "text": "Love the new dashboard!", "mrr": 200})
    r = await registry.invoke("ai.feedback", "themes", {"tenant_id": TENANT})
    assert len(r["themes"]) >= 2


@pytest.mark.asyncio
async def test_offer_recommendation(registry: ServiceRegistry) -> None:
    r = await registry.invoke("ai.offers", "recommend", {
        "tenant_id": TENANT, "churn_reason": "pricing", "churn_probability": 0.8, "mrr": 1000,
    })
    assert r["recommendation"]["offer_type"] == "discount"
    assert r["recommendation"]["discount_pct"] > 0

    r = await registry.invoke("ai.offers", "recommend", {"tenant_id": TENANT, "churn_reason": "temporary"})
    assert r["recommendation"]["offer_type"] == "pause"


# Phase 4: CS ops
@pytest.mark.asyncio
async def test_success_plan_lifecycle(registry: ServiceRegistry) -> None:
    r = await registry.invoke("cs.plans", "create", {"tenant_id": TENANT, "client_id": "c1", "name": "Onboarding"})
    pid = r["plan"]["plan_id"]
    await registry.invoke("cs.plans", "add_milestone", {"plan_id": pid, "name": "Kickoff call"})
    await registry.invoke("cs.plans", "add_milestone", {"plan_id": pid, "name": "First report"})
    r = await registry.invoke("cs.plans", "progress", {"plan_id": pid})
    assert r["progress_pct"] == 0


@pytest.mark.asyncio
async def test_playbook_run(registry: ServiceRegistry) -> None:
    r = await registry.invoke("cs.playbooks", "create", {
        "tenant_id": TENANT, "name": "Churn save", "trigger": "client.churn_risk",
        "actions": [{"service": "email", "action": "send"}],
    })
    r = await registry.invoke("cs.playbooks", "run", {"playbook_id": r["playbook"]["playbook_id"], "client_id": "c1"})
    assert r["status"] == "ok"
    assert r["run"]["actions_executed"] == 1


@pytest.mark.asyncio
async def test_alerts(registry: ServiceRegistry) -> None:
    r = await registry.invoke("cs.alerts", "fire", {"tenant_id": TENANT, "title": "Usage drop", "severity": "high", "type": "risk"})
    r = await registry.invoke("cs.alerts", "list_open", {"tenant_id": TENANT})
    assert r["count"] >= 1
    await registry.invoke("cs.alerts", "acknowledge", {"alert_id": r["alerts"][0]["alert_id"]})


@pytest.mark.asyncio
async def test_renewal_forecast(registry: ServiceRegistry) -> None:
    # isolated tenant so live-seeded renewals elsewhere can't pollute this assertion
    tenant = f"renewal-test-{uuid.uuid4().hex[:8]}"
    await registry.invoke("cs.renewals", "track", {"tenant_id": tenant, "client_id": "c1", "arr": 12000, "renews_at": "2026-12-01"})
    await registry.invoke("cs.renewals", "track", {"tenant_id": tenant, "client_id": "c2", "arr": 6000, "renews_at": "2026-12-15"})
    r = await registry.invoke("cs.renewals", "forecast", {"tenant_id": tenant})
    assert r["total_arr_up_for_renewal"] == 18000
    r = await registry.invoke("cs.renewals", "list_upcoming", {"tenant_id": tenant, "days": 365})
    assert r["count"] >= 2


@pytest.mark.asyncio
async def test_command_center(registry: ServiceRegistry) -> None:
    await registry.invoke("cs.alerts", "fire", {"tenant_id": TENANT, "title": "test"})
    r = await registry.invoke("cs.command_center", "overview", {"tenant_id": TENANT})
    assert r["overview"]["open_alerts"] >= 1


# Phase 5: Integrations
@pytest.mark.asyncio
async def test_integration_catalog(registry: ServiceRegistry) -> None:
    r = await registry.invoke("integrations", "catalog", {})
    assert r["catalog"]["total"] >= 28
    assert "stripe" in r["catalog"]["billing"]

    r = await registry.invoke("integrations", "connect", {"tenant_id": TENANT, "provider": "stripe", "category": "billing"})
    assert r["status"] == "connected"
    r = await registry.invoke("integrations", "list_connected", {"tenant_id": TENANT})
    assert len(r["connections"]) >= 1


@pytest.mark.asyncio
async def test_slack_and_webhooks(registry: ServiceRegistry) -> None:
    r = await registry.invoke("integrations.slack", "send", {"tenant_id": TENANT, "text": "Alert: client at risk", "channel": "#cs"})
    assert r["status"] == "sent"
    r = await registry.invoke("webhooks.manage", "register", {"tenant_id": TENANT, "url": "https://example.com/hook", "events": ["client.churn_risk"]})
    assert r["status"] == "registered"
    r = await registry.invoke("webhooks.manage", "list", {"tenant_id": TENANT})
    assert len(r["endpoints"]) >= 1


# Phase 8: Compliance
@pytest.mark.asyncio
async def test_gdpr_export_delete(registry: ServiceRegistry, tmp_path) -> None:
    # Seed some data
    r = await registry.invoke("ai.feedback", "classify", {"tenant_id": TENANT, "text": "test feedback"})
    export = await registry.invoke("compliance.privacy", "export_data", {"tenant_id": TENANT, "subject_email": "a@b.com"})
    assert export["status"] == "completed"
    assert "export" in export

    delete = await registry.invoke("compliance.privacy", "delete_data", {"tenant_id": TENANT})
    assert delete["status"] == "completed"


@pytest.mark.asyncio
async def test_sso_and_audit_export(registry: ServiceRegistry) -> None:
    r = await registry.invoke("compliance.sso", "configure", {"tenant_id": TENANT, "provider": "saml", "idp_sso_url": "https://idp.example.com/sso"})
    assert r["status"] == "configured"
    r = await registry.invoke("compliance.sso", "status", {"tenant_id": TENANT})
    assert r["sso_enabled"] is True

    r = await registry.invoke("compliance.audit_export", "export", {"tenant_id": TENANT})
    assert "entries" in r
