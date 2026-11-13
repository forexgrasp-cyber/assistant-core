"""Tests for advanced customer analysis: computed segmentation, next best action,
tailored content, automatic approach."""

from __future__ import annotations

import pytest

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced_processing.analysis import (
    AdvancedSegmentation,
    AutoApproachService,
    NextBestActionService,
    TailoredContentService,
)
from retention_analytics_advanced.customer_intel import Customer360Service

TENANT = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def registry(tmp_path, monkeypatch) -> ServiceRegistry:
    import retention_analytics_core.repository as repo_mod
    import retention_analytics_advanced.customer_intel as ci
    import retention_analytics_advanced_processing.analysis as an
    for mod in (repo_mod, ci, an):
        monkeypatch.setattr(mod, "data_root", lambda: tmp_path, raising=False)
    reg = ServiceRegistry()
    Customer360Service(reg).register()
    from retention_analytics_ux.campaign import CampaignService
    CampaignService(reg).register()
    for cls in (AdvancedSegmentation, NextBestActionService, AutoApproachService, TailoredContentService):
        cls(reg).register()
    return reg


async def _seed(registry: ServiceRegistry) -> None:
    from datetime import UTC, datetime, timedelta
    now = datetime.now(UTC)
    rows = [
        ("Maria", "maria@x.com", "premium", 1200, 5000, 20, 5),    # due in 5d, low health
        ("John", "john@x.com", "growth", 400, 800, 60, 80),          # healthy
        ("Ana", "ana@x.com", "starter", 80, 100, 50, -12),          # overdue
        ("Bob", "bob@x.com", "premium", 3000, 9000, 75, 40),        # big account
    ]
    for name, email, plan, mrr, ltv, health, due in rows:
        last = (now - timedelta(days=(180 - due))).isoformat()
        await registry.invoke("customers.360", "upsert_profile", {
            "tenant_id": TENANT, "id": email.split("@")[0], "name": name, "email": email,
            "plan": plan, "mrr": mrr, "ltv": ltv, "health_score": health,
            "last_service_date": last, "service_interval_days": 180, "service_name": "oil change"})


@pytest.mark.asyncio
async def test_computed_fields_on_profiles(registry: ServiceRegistry) -> None:
    await _seed(registry)
    r = await registry.invoke("segmentation.advanced", "profiles", {"tenant_id": TENANT})
    rows = r["profiles"]
    assert len(rows) == 4
    maria = next(x for x in rows if x["email"] == "maria@x.com")
    assert maria["due_soon"] is True and maria["overdue"] is False
    assert maria["days_until_due"] == 5
    assert maria["mrr_band"] == "enterprise"
    assert maria["ltv_tier"] == "champion"
    assert maria["health_tier"] in ("critical", "at_risk", "watch")
    ana = next(x for x in rows if x["email"] == "ana@x.com")
    assert ana["overdue"] is True
    # value rank: Bob (ltv 9000) is 1
    assert next(x for x in rows if x["email"] == "bob@x.com")["value_rank"] == 1


@pytest.mark.asyncio
async def test_segment_preview_computed_criteria(registry: ServiceRegistry) -> None:
    await _seed(registry)
    r = await registry.invoke("segmentation.advanced", "preview", {
        "tenant_id": TENANT, "criteria": {"due_soon": True}})
    assert r["matched"] == 1
    assert r["aggregate"]["due_soon"] == 1
    assert r["aggregate"]["total_mrr"] == 1200

    r = await registry.invoke("segmentation.advanced", "preview", {
        "tenant_id": TENANT, "criteria": {"overdue": True}})
    assert r["matched"] == 1

    r = await registry.invoke("segmentation.advanced", "preview", {
        "tenant_id": TENANT, "criteria": {"mrr_band": "enterprise"}})
    assert r["matched"] == 2  # Maria 1200 + Bob 3000
    assert r["aggregate"]["total_ltv"] == 14000


@pytest.mark.asyncio
async def test_segment_save_and_list(registry: ServiceRegistry) -> None:
    await _seed(registry)
    r = await registry.invoke("segmentation.advanced", "save", {
        "tenant_id": TENANT, "name": "Due soon", "criteria": {"due_soon": True}})
    sid = r["segment"]["segment_id"]
    r = await registry.invoke("segmentation.advanced", "list", {"tenant_id": TENANT})
    assert r["count"] == 1 and r["segments"][0]["name"] == "Due soon"
    await registry.invoke("segmentation.advanced", "delete", {"segment_id": sid})
    r = await registry.invoke("segmentation.advanced", "list", {"tenant_id": TENANT})
    assert r["count"] == 0


@pytest.mark.asyncio
async def test_next_best_action(registry: ServiceRegistry) -> None:
    await _seed(registry)
    r = await registry.invoke("customers.next_best_action", "recommend", {
        "tenant_id": TENANT, "customer_id": "ana"})
    assert r["recommendation"]["action"] == "service_recovery"
    assert r["recommendation"]["priority"] == 1
    assert "12 days ago" in r["recommendation"]["reason"]

    r = await registry.invoke("customers.next_best_action", "recommend", {
        "tenant_id": TENANT, "customer_id": "maria"})
    assert r["recommendation"]["action"] in ("service_reminder", "save_offer")

    r = await registry.invoke("customers.next_best_action", "recommend_all", {"tenant_id": TENANT})
    assert r["count"] >= 2
    assert r["recommendations"][0]["priority"] <= r["recommendations"][-1]["priority"]


@pytest.mark.asyncio
async def test_tailored_content_rendering(registry: ServiceRegistry) -> None:
    await registry.invoke("campaigns.templates", "set_template", {
        "tenant_id": TENANT, "campaign_id": "camp-1", "name": "Reminder", "channel": "email",
        "subject": "Hi {{first_name}} — your {{service_name}} is due",
        "body": "Your {{service_name}} is due on {{next_due_date}} ({{days_until_due}} days). Book: {{booking_url}}",
        "segment_overrides": {"vip": {"subject": "VIP: {{first_name}}", "body": "Exclusive access, {{first_name}}."}},
    })
    r = await registry.invoke("campaigns.templates", "render", {
        "tenant_id": TENANT, "campaign_id": "camp-1",
        "member": {"name": "Maria Garcia", "service_name": "oil change", "next_due_date": "2026-12-01", "days_until_due": 5}})
    assert r["subject"] == "Hi Maria — your oil change is due"
    assert "2026-12-01" in r["body"] and "5 days" in r["body"]
    assert r["used_override"] is False

    r = await registry.invoke("campaigns.templates", "render", {
        "tenant_id": TENANT, "campaign_id": "camp-1", "segment_id": "vip",
        "member": {"name": "Bob Chen"}})
    assert r["subject"] == "VIP: Bob" and r["used_override"] is True


@pytest.mark.asyncio
async def test_auto_approach_scan_and_run(registry: ServiceRegistry) -> None:
    await _seed(registry)
    r = await registry.invoke("automation.auto_approach", "scan", {"tenant_id": TENANT})
    assert r["total_customers"] == 4
    assert r["triggers"]["service_due"]["count"] == 1
    assert r["triggers"]["service_overdue"]["count"] == 1

    r = await registry.invoke("automation.auto_approach", "run", {"tenant_id": TENANT, "dry_run": True})
    assert r["campaigns_created"] >= 1
    assert all(x["dry_run"] for x in r["results"])

    r = await registry.invoke("automation.auto_approach", "run", {"tenant_id": TENANT})
    assert r["campaigns_created"] >= 1
    assert any(x["matched"] >= 1 for x in r["results"])
