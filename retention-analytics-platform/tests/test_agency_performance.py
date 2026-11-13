"""Tests for the agency layer and the deep-dive performance analytics."""

from __future__ import annotations

import pytest

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced_processing.agency import AgencyService
from retention_analytics_advanced_processing.agency_connectors import AgencyConnectorService, PLATFORMS
from retention_analytics_advanced_processing.performance import PerformanceAnalytics

TENANT = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def registry(tmp_path, monkeypatch) -> ServiceRegistry:
    import retention_analytics_core.repository as repo_mod
    import retention_analytics_advanced.customer_intel as ci
    import retention_analytics_advanced_processing.agency as ag
    import retention_analytics_advanced_processing.agency_connectors as ac
    import retention_analytics_advanced_processing.performance as pf
    for mod in (repo_mod, ci, ag, ac, pf):
        monkeypatch.setattr(mod, "data_root", lambda: tmp_path, raising=False)
    reg = ServiceRegistry()
    AgencyService(reg).register()
    AgencyConnectorService(reg).register()
    PerformanceAnalytics(reg).register()
    return reg


# ------------------------------------------------------------------ agency

@pytest.mark.asyncio
async def test_agency_client_crud_and_roster(registry: ServiceRegistry) -> None:
    r = await registry.invoke("agency", "create_client", {
        "agency_id": "ag1", "tenant_id": TENANT, "name": "Trendi Apparel",
        "monthly_target": 465000, "goal_metric": "revenue"})
    cid = r["client"]["client_id"]
    assert r["client"]["branding"]["company_name"] == "Trendi Apparel"
    assert r["client"]["goal"]["monthly_target"] == 465000

    await registry.invoke("agency", "create_client", {
        "agency_id": "ag1", "tenant_id": TENANT, "name": "Clear Skincare", "monthly_target": 250000})

    r = await registry.invoke("agency", "list_clients", {"agency_id": "ag1"})
    assert r["count"] == 2

    r = await registry.invoke("agency", "roster", {"agency_id": "ag1"})
    assert r["count"] == 2
    assert r["summary"]["behind_goal"] >= 0
    # pacing is month progress; goal_pct depends on revenue (none yet -> 0%)
    row = r["clients"][0]
    assert "pacing_pct" in row and 0 <= row["pacing_pct"] <= 100
    assert row["status"] in ("on_track", "behind_goal", "revenue_down", "deliverability", "churn_risk")

    r = await registry.invoke("agency", "update_client", {"client_id": cid, "branding": {"company_name": "Trendi"}})
    assert r["client"]["branding"]["company_name"] == "Trendi"

    r = await registry.invoke("agency", "set_goal", {"client_id": cid, "metric": "revenue", "monthly_target": 500000})
    assert r["goal"]["monthly_target"] == 500000

    r = await registry.invoke("agency", "delete_client", {"client_id": cid})
    assert r["status"] == "deleted"
    r = await registry.invoke("agency", "list_clients", {"agency_id": "ag1"})
    assert r["count"] == 1


@pytest.mark.asyncio
async def test_agency_share_and_digest(registry: ServiceRegistry) -> None:
    r = await registry.invoke("agency", "create_client", {
        "agency_id": "ag1", "tenant_id": TENANT, "name": "Shared Co"})
    cid = r["client"]["client_id"]
    r = await registry.invoke("agency", "share_dashboard", {"client_id": cid})
    assert r["share"]["token"] and r["share"]["url"].startswith("/share/")
    assert r["share"]["branding"]["company_name"] == "Shared Co"

    r = await registry.invoke("agency", "list_shares", {"client_id": cid})
    assert r["count"] == 1

    r = await registry.invoke("agency", "client_report", {"tenant_id": TENANT, "branding": {"company_name": "Shared Co"}})
    assert r["report"]["branding"]["company_name"] == "Shared Co"

    r = await registry.invoke("agency", "schedule_digest", {
        "client_id": cid, "agency_id": "ag1", "frequency": "weekly", "channel": "#trendi"})
    assert r["digest"]["frequency"] == "weekly"
    r = await registry.invoke("agency", "list_digests", {})
    assert len(r["digests"]) == 1


# -------------------------------------------------------------- connectors

@pytest.mark.asyncio
async def test_agency_platforms_catalog(registry: ServiceRegistry) -> None:
    r = await registry.invoke("connectors.agency", "platforms", {})
    names = {p["platform"] for p in r["platforms"]}
    # The platforms Hiro supports for agencies
    for expected in ("klaviyo", "attentive", "postscript", "omnisend", "sendlane", "shopify",
                      "recharge", "skio", "loop", "stayai", "ordergroove", "alia"):
        assert expected in names, f"missing platform: {expected}"
    assert "stripe" in names
    assert r["by_category"]["email_sms"]
    assert r["by_category"]["store"]
    assert r["by_category"]["subscriptions"]
    assert r["by_category"]["popups"]


@pytest.mark.asyncio
async def test_connector_requires_credentials(registry: ServiceRegistry, monkeypatch) -> None:
    for k in list(__import__("os").environ):
        if k.startswith(("KLAVIYO_", "SHOPIFY_", "RECHARGE_", "STRIPE_")):
            monkeypatch.delenv(k, raising=False)
    r = await registry.invoke("connectors.agency", "connect", {"platform": "klaviyo"})
    assert r["status"] == "no_credentials" and "KLAVIYO_PRIVATE_API_KEY" in r["missing_keys"]
    r = await registry.invoke("connectors.agency", "sync", {"platform": "klaviyo", "tenant_id": TENANT})
    assert r["status"] == "no_credentials"
    r = await registry.invoke("connectors.agency", "sync", {"platform": "bogus"})
    assert r["status"] == "unknown_platform"


@pytest.mark.asyncio
async def test_connector_connect_with_key(registry: ServiceRegistry, monkeypatch) -> None:
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_test_123")
    r = await registry.invoke("connectors.agency", "connect", {"platform": "klaviyo", "client_id": "c1"})
    assert r["status"] == "connected"
    r = await registry.invoke("connectors.agency", "platforms", {})
    klaviyo = next(p for p in r["platforms"] if p["platform"] == "klaviyo")
    assert klaviyo["configured"] is True


# ------------------------------------------------------------- performance

@pytest.mark.asyncio
async def test_flow_map_and_campaign_dive(registry: ServiceRegistry) -> None:
    for i, (day, hour) in enumerate([(2, 9), (3, 10), (3, 21)]):
        await registry.invoke("analytics.performance", "record_send", {
            "tenant_id": TENANT, "flow_id": "churn-prevention", "message_id": f"m{i}",
            "campaign_id": "camp-1", "subject": f"Subject {i}", "channel": "email",
            "send_mode": "static", "sent_at": f"2026-11-0{day + 1}T{hour:02d}:00:00+00:00",
            "sent": 1000, "delivered": 980, "opened": 500, "clicked": 60,
            "revenue": 1000 + i * 500, "products": [{"name": "Sweater", "units": 10, "revenue": 100}],
            "first_time_buyers": 30, "returning_buyers": 20, "variant": "A" if i == 0 else "B"})

    r = await registry.invoke("analytics.performance", "flow_map", {"tenant_id": TENANT})
    assert r["message_count"] == 3
    assert r["totals"]["sent"] == 3000
    assert r["totals"]["revenue"] == 4500
    assert r["messages"][0]["open_rate"] == 50.0

    r = await registry.invoke("analytics.performance", "campaign_deep_dive", {"tenant_id": TENANT})
    assert r["send_count"] == 3
    assert r["products"][0]["name"] == "Sweater"
    assert r["buyers"]["first_time"] == 90
    assert len(r["variants"]) == 2


@pytest.mark.asyncio
async def test_message_timing_static_vs_local(registry: ServiceRegistry) -> None:
    await registry.invoke("analytics.performance", "record_send", {
        "tenant_id": TENANT, "message_id": "s1", "subject": "Best subject",
        "send_mode": "static", "sent_at": "2026-11-05T09:00:00+00:00",
        "sent": 100, "opened": 60, "revenue": 500})
    await registry.invoke("analytics.performance", "record_send", {
        "tenant_id": TENANT, "message_id": "l1", "subject": "Local subject",
        "send_mode": "recipient_local", "sent_at": "2026-11-06T21:00:00+00:00",
        "sent": 100, "opened": 10, "revenue": 50})

    r = await registry.invoke("analytics.performance", "message_timing", {"tenant_id": TENANT})
    assert "static" in r["modes"] and "recipient_local" in r["modes"]
    assert r["modes"]["static"]["best_slot"]["revenue_per_recipient"] == 5.0
    assert r["modes"]["recipient_local"]["best_slot"]["revenue_per_recipient"] == 0.5
    assert r["subjects_ranked"][0]["subject"] == "Best subject"
    assert r["subjects_ranked"][0]["open_rate"] == 60.0


@pytest.mark.asyncio
async def test_deliverability_by_provider(registry: ServiceRegistry) -> None:
    await registry.invoke("analytics.performance", "record_deliverability", {
        "tenant_id": TENANT, "provider": "Gmail", "sent": 1000, "delivered": 990, "bounced": 3, "spam": 1, "unsubscribed": 2})
    await registry.invoke("analytics.performance", "record_deliverability", {
        "tenant_id": TENANT, "provider": "Outlook", "sent": 500, "delivered": 470, "bounced": 25, "spam": 4, "unsubscribed": 9,
        "source_name": "Last Call · Summer"})
    r = await registry.invoke("analytics.performance", "deliverability", {"tenant_id": TENANT})
    providers = {p["provider"]: p for p in r["providers"]}
    assert providers["Gmail"]["bounce_rate"] == 0.3
    assert providers["Outlook"]["bounce_rate"] == 5.0
    assert r["biggest_offender"]["provider"] == "Outlook"
    assert 0 <= r["score"] <= 100
