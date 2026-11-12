"""Tests for advanced processing: send-time, ML churn, deliverability, multi-touch
attribution, cohort comparison, root-cause, annotations."""

from __future__ import annotations

import pytest

from retention_analytics_core.service_registry import ServiceRegistry
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

TENANT = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def registry(tmp_path, monkeypatch) -> ServiceRegistry:
    import retention_analytics_core.repository as repo_mod
    import retention_analytics_advanced.customer_intel as ci
    import retention_analytics_advanced_processing.services as sv
    import retention_analytics_advanced_processing.analytics as an
    import retention_analytics_advanced_processing.annotations as ann
    for mod in (repo_mod, ci, sv, an, ann):
        monkeypatch.setattr(mod, "data_root", lambda: tmp_path, raising=False)
    reg = ServiceRegistry()
    for cls in (SendTimeService, MLChurnService, DeliverabilityService, CustomerPortalService,
                MultiTouchAttribution, CohortComparison, RootCauseService, AnnotationService):
        cls(reg).register()
    return reg


@pytest.mark.asyncio
async def test_sendtime_recommend_and_plan(registry: ServiceRegistry) -> None:
    r = await registry.invoke("sendtime.optimize", "recommend", {"email": "a@x.com"})
    assert r["status"] == "ok" and "recommendation" in r
    r = await registry.invoke("sendtime.optimize", "best_hours", {})
    assert r["status"] == "ok"
    r = await registry.invoke("sendtime.optimize", "plan_campaign", {
        "tenant_id": TENANT, "campaign_id": "camp-1",
        "recipients": [{"email": "a@x.com", "customer_id": "c1"}]})
    assert r["status"] == "ok" and len(r["plan"]["planned"]) == 1


@pytest.mark.asyncio
async def test_ml_churn_blends_with_health(registry: ServiceRegistry) -> None:
    r = await registry.invoke("ai.churn_ml", "score", {
        "tenant_id": TENANT, "client_id": "c1", "orders": 2, "order_count": 2,
        "total_spent": 100, "days_since_last_order": 120, "frequency": 2, "monetary": 100})
    assert r["status"] == "ok"
    res = r["result"]
    assert "ml_churn_risk" in res and "blended_risk" in res
    assert res["risk_level"] in ("low", "medium", "high", "critical")


@pytest.mark.asyncio
async def test_deliverability(registry: ServiceRegistry) -> None:
    r = await registry.invoke("email.deliverability", "warmup_schedule", {"daily_volume": 100, "age_days": 3})
    assert r["status"] == "ok" and "schedule" in r


@pytest.mark.asyncio
async def test_multi_touch_attribution_models(registry: ServiceRegistry) -> None:
    for i, ch in enumerate(["email", "ad", "sales"]):
        await registry.invoke("attribution.multitouch", "record_touch", {
            "tenant_id": TENANT, "customer_id": "c1", "channel": ch, "campaign_id": f"camp-{ch}",
            "value": 100, "at": f"2026-11-0{i+1}T10:00:00+00:00"})
    await registry.invoke("attribution.multitouch", "record_touch", {
        "tenant_id": TENANT, "customer_id": "c1", "channel": "email", "campaign_id": "camp-email",
        "value": 100, "at": "2026-11-10T10:00:00+00:00", "converted": True})

    r = await registry.invoke("attribution.multitouch", "attribute", {
        "tenant_id": TENANT, "customer_id": "c1", "model": "last_touch", "conversion_value": 300})
    assert r["status"] == "ok"
    assert max(r["by_channel"].values()) == 300

    r = await registry.invoke("attribution.multitouch", "attribute", {
        "tenant_id": TENANT, "customer_id": "c1", "model": "linear", "conversion_value": 300})
    assert abs(sum(r["by_channel"].values()) - 300) < 0.01

    r = await registry.invoke("attribution.multitouch", "attribute", {
        "tenant_id": TENANT, "customer_id": "c1", "model": "first_touch", "conversion_value": 300})
    assert r["by_channel"].get("email") == 300

    r = await registry.invoke("attribution.multitouch", "attribute", {
        "tenant_id": TENANT, "customer_id": "c1", "model": "bogus"})
    assert r["status"] == "invalid_model"


@pytest.mark.asyncio
async def test_cohort_comparison(registry: ServiceRegistry) -> None:
    r = await registry.invoke("analytics.cohort_compare", "compare", {
        "metric": "retention_rate_30d",
        "cohort_a": {"name": "Q1", "size": 100, "metrics": {"retention_rate_30d": 0.6}},
        "cohort_b": {"name": "Q2", "size": 120, "metrics": {"retention_rate_30d": 0.8}}})
    assert r["winner"] == "B" and r["difference"] == pytest.approx(0.2)
    assert r["relative_diff_pct"] == pytest.approx(33.3, abs=0.2)


@pytest.mark.asyncio
async def test_root_cause(registry: ServiceRegistry) -> None:
    r = await registry.invoke("analytics.root_cause", "analyze", {
        "tenant_id": TENANT, "metric": "churn_rate", "window_hours": 24})
    assert r["status"] == "ok"
    assert "signals" in r and "recommendation" in r


@pytest.mark.asyncio
async def test_annotations(registry: ServiceRegistry) -> None:
    r = await registry.invoke("analytics.annotations", "create", {
        "tenant_id": TENANT, "metric": "retention", "note": "launched new pricing"})
    aid = r["annotation"]["annotation_id"]
    r = await registry.invoke("analytics.annotations", "list", {"tenant_id": TENANT, "metric": "retention"})
    assert r["count"] == 1 and r["annotations"][0]["note"] == "launched new pricing"
    r = await registry.invoke("analytics.annotations", "delete", {"annotation_id": aid})
    assert r["status"] == "deleted"
