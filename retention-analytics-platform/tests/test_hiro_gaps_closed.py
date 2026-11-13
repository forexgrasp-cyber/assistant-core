"""Tests for the 7 remaining Hiro gaps: time-between-orders, product paths,
subscription LTV + one-time->subscriber + product trends, RFM movement,
report deck, role views, natural-language Q&A."""

from __future__ import annotations

import pytest

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced_processing.commerce import CommerceAnalytics
from retention_analytics_advanced_processing.agency import AgencyService
from retention_analytics_advanced_processing.performance import PerformanceAnalytics
from retention_analytics_advanced_processing.agency_reports import (
    AgencyQAService,
    ReportDeckService,
    RoleViewService,
)

TENANT = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def registry(tmp_path, monkeypatch) -> ServiceRegistry:
    import retention_analytics_core.repository as repo_mod
    import retention_analytics_advanced.customer_intel as ci
    import retention_analytics_advanced_processing.commerce as co
    import retention_analytics_advanced_processing.agency as ag
    import retention_analytics_advanced_processing.agency_reports as ar
    for mod in (repo_mod, ci, co, ag, ar):
        monkeypatch.setattr(mod, "data_root", lambda: tmp_path, raising=False)
    reg = ServiceRegistry()
    AgencyService(reg).register()
    CommerceAnalytics(reg).register()
    PerformanceAnalytics(reg).register()
    AgencyQAService(reg).register()
    RoleViewService(reg).register()
    ReportDeckService(reg).register()
    return reg


async def _orders(registry: ServiceRegistry) -> None:
    from datetime import UTC, datetime, timedelta
    now = datetime.now(UTC)
    rows = [
        # Alice: one-time first, then subscription 40 days later, then a reorder 20 days after that
        ("alice@x.com", "o1", 100, [{"name": "Sampler Trio", "units": 1, "revenue": 100, "type": "one_time"}], "", "", False, "", 90),
        ("alice@x.com", "o2", 60, [{"name": "House Blend", "units": 1, "revenue": 60, "type": "subscription"}], "", "", True, "House Blend", 50),
        ("alice@x.com", "o3", 60, [{"name": "House Blend", "units": 1, "revenue": 60, "type": "subscription"}], "camp-1", "", True, "House Blend", 30),
        # Bob: one-time only, then organic reorder 200 days later
        ("bob@x.com", "o4", 50, [{"name": "Cold Brew Pack", "units": 1, "revenue": 50, "type": "one_time"}], "", "", False, "", 240),
        ("bob@x.com", "o5", 70, [{"name": "Cold Brew Pack", "units": 1, "revenue": 70, "type": "one_time"}], "", "", False, "", 40),
        # Cara: one-time then subscription after 41 days
        ("cara@x.com", "o6", 80, [{"name": "Single Origin Box", "units": 1, "revenue": 80, "type": "one_time"}], "", "", False, "", 80),
        ("cara@x.com", "o7", 55, [{"name": "Single Origin Box", "units": 1, "revenue": 55, "type": "subscription"}], "", "", True, "Single Origin Box", 39),
    ]
    for email, oid, amount, products, camp, flow, is_sub, sub_product, days_ago in rows:
        placed = (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()
        await registry.invoke("analytics.commerce", "record_order", {
            "tenant_id": TENANT, "order_id": oid, "customer_email": email, "amount": amount,
            "products": products, "campaign_id": camp, "flow_id": flow,
            "is_subscription": is_sub, "subscription_product": sub_product, "placed_at": placed})


# ------------------------------------------------------- gap 1: time between
@pytest.mark.asyncio
async def test_time_between_orders(registry: ServiceRegistry) -> None:
    await _orders(registry)
    r = await registry.invoke("analytics.commerce", "time_between_orders", {"tenant_id": TENANT})
    # alice 3 orders -> 2 gaps, bob 2 -> 1, cara 2 -> 1 = 4
    assert r["all_reorders"] == 4
    assert r["returning_customers"] == 3
    assert r["median_gap_days"] > 0
    # alice's second order came after a campaign -> attributed bucket has 1
    assert r["after_campaign"]["reorders"] == 1
    assert r["on_their_own"]["reorders"] == 3
    assert sum(b["count"] for b in r["buckets"]) == 4


# -------------------------------------------------------- gap 2: product paths
@pytest.mark.asyncio
async def test_product_paths(registry: ServiceRegistry) -> None:
    await _orders(registry)
    r = await registry.invoke("analytics.commerce", "product_paths", {"tenant_id": TENANT})
    assert r["customers"] == 3
    assert any("Sampler Trio" in p["path"] for p in r["paths"])
    # first-purchase products only
    names = {p["product"] for p in r["by_product"]}
    assert "Sampler Trio" in names and "Cold Brew Pack" in names
    # Cold Brew Pack: bob bought it twice -> 1 repeat buyer
    cold = next(p for p in r["by_product"] if p["product"] == "Cold Brew Pack")
    assert cold["repeat_buyers"] == 1
    assert cold["repeat_rate"] > 0
    # Sampler Trio was bought once -> no repeats
    sampler = next(p for p in r["by_product"] if p["product"] == "Sampler Trio")
    assert sampler["repeat_buyers"] == 0
    # keyword filter
    r = await registry.invoke("analytics.commerce", "product_paths", {"tenant_id": TENANT, "keyword": "cold"})
    assert {p["product"] for p in r["by_product"]} == {"Cold Brew Pack"}


# ---------------------------- gap 3: sub LTV / one-time->sub / product trends
@pytest.mark.asyncio
async def test_subscription_ltv_and_conversion(registry: ServiceRegistry) -> None:
    await _orders(registry)
    r = await registry.invoke("analytics.commerce", "subscription_ltv", {"tenant_id": TENANT})
    assert r["total_subscription_starts"] == 3
    by_product = {p["product"]: p for p in r["by_product"]}
    assert "House Blend" in by_product
    assert len(by_product["House Blend"]["ltv"]) == 4  # 1/3/6/12 months

    r = await registry.invoke("analytics.commerce", "one_time_to_subscriber", {"tenant_id": TENANT})
    assert r["one_time_buyers"] == 3
    assert r["converted"] == 2
    assert r["conversion_rate"] > 0
    assert r["avg_days_to_subscribe"] is not None

    r = await registry.invoke("analytics.commerce", "product_trends", {"tenant_id": TENANT})
    assert "most_new_starts" in r and "fastest_growing" in r
    assert "most_cancels" in r and "top_add_on" in r


# ------------------------------------------------------- gap 4: RFM movement
@pytest.mark.asyncio
async def test_rfm_movement(registry: ServiceRegistry) -> None:
    await _orders(registry)
    r = await registry.invoke("analytics.commerce", "rfm_movement", {"tenant_id": TENANT})
    assert len(r["segments"]) == 5
    for row in r["segments"]:
        assert "customers" in row and "net_change" in row
    assert "biggest_moves" in r
    assert "attributed_share" in r


# --------------------------------------------------------- gap 5: report deck
@pytest.mark.asyncio
async def test_report_deck(registry: ServiceRegistry) -> None:
    await registry.invoke("agency", "create_client", {
        "agency_id": "ag", "tenant_id": TENANT, "name": "Trendi Apparel",
        "monthly_target": 465000, "primary_color": "#ff0000"})
    r = await registry.invoke("agency", "roster", {"agency_id": "ag"})
    cid = r["clients"][0]["client_id"]
    r = await registry.invoke("agency.deck", "build", {"client_id": cid, "agency_id": "ag", "period": "September"})
    deck = r["deck"]
    assert len(deck["slides"]) == 5
    assert deck["slides"][0]["kind"] == "title"
    r = await registry.invoke("agency.deck", "render_html", {"deck": deck})
    html = r["html"]
    assert "Trendi Apparel" in html
    assert "#ff0000" in html  # agency brand colour applied
    assert "page-break-after" in html  # print-to-PDF ready
    assert r["slides"] == 5


# --------------------------------------------------------- gap 6: role views
@pytest.mark.asyncio
async def test_role_views(registry: ServiceRegistry) -> None:
    await registry.invoke("agency", "create_client", {
        "agency_id": "ag", "tenant_id": TENANT, "name": "Trendi Apparel", "monthly_target": 465000})
    r = await registry.invoke("agency.roles", "roles", {})
    assert set(r["roles"]) == {"leadership", "account_manager", "copywriter"}

    r = await registry.invoke("agency.roles", "view", {"role": "leadership", "agency_id": "ag"})
    assert r["role"] == "leadership"
    assert "behind_goal" in r["headline"] and "revenue_mtd" in r["headline"]
    assert len(r["clients"]) == 1

    roster = await registry.invoke("agency", "roster", {"agency_id": "ag"})
    cid = roster["clients"][0]["client_id"]
    r = await registry.invoke("agency.roles", "view", {"role": "account_manager", "agency_id": "ag", "client_id": cid})
    assert r["role"] == "account_manager"
    assert r["client"]["name"] == "Trendi Apparel"

    r = await registry.invoke("agency.roles", "view", {"role": "copywriter", "tenant_id": TENANT})
    assert r["role"] == "copywriter"
    assert "best_slot" in r["headline"]


# ------------------------------------------------------------- gap 7: NL Q&A
@pytest.mark.asyncio
async def test_agency_qa(registry: ServiceRegistry) -> None:
    await registry.invoke("agency", "create_client", {
        "agency_id": "ag", "tenant_id": TENANT, "name": "Trendi Apparel", "monthly_target": 465000})
    r = await registry.invoke("agency.qa", "suggestions", {})
    assert len(r["questions"]) >= 5

    r = await registry.invoke("agency.qa", "ask", {"agency_id": "ag", "question": "Which clients are behind this month?"})
    assert r["intent"] == "clients_behind"
    assert "behind goal" in r["answer"].lower()

    r = await registry.invoke("agency.qa", "ask", {"agency_id": "ag", "question": "What is our total revenue?"})
    assert r["intent"] == "revenue_overview"
    assert "revenue" in r["answer"].lower()

    r = await registry.invoke("agency.qa", "ask", {"agency_id": "ag", "question": "any churn risk?"})
    assert r["intent"] == "churn_risk"

    r = await registry.invoke("agency.qa", "ask", {"agency_id": "ag", "question": "show me the roster"})
    assert r["intent"] == "roster"
