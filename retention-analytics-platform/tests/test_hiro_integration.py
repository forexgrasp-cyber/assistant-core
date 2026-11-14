"""Integration tests for Hiro Analytics bridge."""

from __future__ import annotations

import pytest

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced_processing.agency import AgencyService
from retention_analytics_advanced_processing.agency_connectors import AgencyConnectorService, PLATFORMS
from retention_analytics_advanced_processing.commerce import CommerceAnalytics
from apps.mcp_server.main import mcp
from shared.integrations.hiro_client import HiroClient, HIRO_DEFAULT_API_BASE, HIRO_DEFAULT_MCP_URL

TENANT = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def registry(tmp_path, monkeypatch) -> ServiceRegistry:
    import retention_analytics_core.repository as repo_mod
    import retention_analytics_advanced.customer_intel as ci
    import retention_analytics_advanced_processing.agency as ag
    import retention_analytics_advanced_processing.agency_connectors as ac
    import retention_analytics_advanced_processing.commerce as cm
    for mod in (repo_mod, ci, ag, ac, cm):
        monkeypatch.setattr(mod, "data_root", lambda: tmp_path, raising=False)
    reg = ServiceRegistry()
    AgencyService(reg).register()
    AgencyConnectorService(reg).register()
    CommerceAnalytics(reg).register()
    return reg


# ------------------------------------------------------------------ HiroClient
def test_hiro_client_defaults() -> None:
    client = HiroClient()
    assert client.api_base == HIRO_DEFAULT_API_BASE
    assert client.mcp_url == HIRO_DEFAULT_MCP_URL


def test_hiro_client_fail_closed(monkeypatch) -> None:
    monkeypatch.delenv("HIRO_API_KEY", raising=False)
    monkeypatch.delenv("HIRO_DRY_RUN", raising=False)
    client = HiroClient()
    import asyncio
    result = asyncio.run(client.platforms())
    assert result["status"] == "no_credentials"


def test_hiro_client_dry_run(monkeypatch) -> None:
    monkeypatch.setenv("HIRO_DRY_RUN", "1")
    client = HiroClient()
    import asyncio
    result = asyncio.run(client.platforms())
    assert result["status"] == "dry_run"
    assert result["method"] == "GET"
    assert HIRO_DEFAULT_API_BASE in result["url"]


def test_hiro_client_custom_params() -> None:
    client = HiroClient(api_key="test-key", api_base="https://custom.api/v1", mcp_url="https://custom.mcp")
    assert client.api_base == "https://custom.api/v1"
    assert client.mcp_url == "https://custom.mcp"


def test_hiro_client_injectable_http() -> None:
    class FakeHttp:
        async def request(self, method, url, headers=None, json=None, params=None, timeout=None):
            return {"status": "ok", "method": method, "url": url, "headers": headers, "json": json, "params": params}
    client = HiroClient(api_key="test", http=FakeHttp(), dry_run=False)
    import asyncio
    result = asyncio.run(client.platforms())
    assert result["status"] == "ok"
    assert result["method"] == "GET"
    assert "Authorization" in result["headers"]


# ------------------------------------------------------------------ agency_connectors hiro
def test_platforms_includes_hiro(registry: ServiceRegistry) -> None:
    assert "hiro" in PLATFORMS
    assert PLATFORMS["hiro"]["category"] == "analytics_source"
    assert "HIRO_API_KEY" in PLATFORMS["hiro"]["keys"]


@pytest.mark.asyncio
async def test_hiro_connector_requires_credentials(registry: ServiceRegistry, monkeypatch) -> None:
    monkeypatch.delenv("HIRO_API_KEY", raising=False)
    r = await registry.invoke("connectors.agency", "connect", {"platform": "hiro"})
    assert r["status"] == "no_credentials"
    assert "HIRO_API_KEY" in r["missing_keys"]


@pytest.mark.asyncio
async def test_hiro_connector_connect_with_key(registry: ServiceRegistry, monkeypatch) -> None:
    monkeypatch.setenv("HIRO_API_KEY", "test-key")
    r = await registry.invoke("connectors.agency", "connect", {"platform": "hiro", "client_id": "c1", "tenant_id": TENANT})
    assert r["status"] == "connected"
    assert r["connection"]["platform"] == "hiro"
    assert r["connection"]["category"] == "analytics_source"


# ------------------------------------------------------------------ commerce.revenue_summary
@pytest.mark.asyncio
async def test_commerce_revenue_summary_empty(registry: ServiceRegistry) -> None:
    r = await registry.invoke("analytics.commerce", "revenue_summary", {"tenant_id": TENANT})
    assert r["status"] == "ok"
    assert r["orders"] == 0
    assert r["revenue_total"] == 0.0
    assert r["revenue_mtd"] == 0.0
    assert r["attributed_share_pct"] == 0.0


@pytest.mark.asyncio
async def test_commerce_revenue_summary_with_orders(registry: ServiceRegistry) -> None:
    # Record a mix of orders
    await registry.invoke("analytics.commerce", "record_order", {
        "tenant_id": TENANT, "customer_email": "a@b.com", "amount": 100,
        "campaign_id": "camp-1", "placed_at": "2026-11-01T10:00:00+00:00"})
    await registry.invoke("analytics.commerce", "record_order", {
        "tenant_id": TENANT, "customer_email": "a@b.com", "amount": 200,
        "is_subscription": True, "subscription_product": "Premium", "placed_at": "2026-11-10T10:00:00+00:00"})
    await registry.invoke("analytics.commerce", "record_order", {
        "tenant_id": TENANT, "customer_email": "c@d.com", "amount": 50,
        "placed_at": "2026-10-15T10:00:00+00:00"})  # organic, previous month

    r = await registry.invoke("analytics.commerce", "revenue_summary", {"tenant_id": TENANT})
    assert r["status"] == "ok"
    assert r["orders"] == 3
    assert r["revenue_total"] == 350.0
    assert r["attributed_revenue"] == 100.0
    assert r["organic_revenue"] == 250.0
    assert r["subscription_revenue"] == 200.0
    assert r["one_time_revenue"] == 150.0
    assert r["attributed_share_pct"] == round(100 / 350 * 100, 1)


# ------------------------------------------------------------------ agency revenue_mtd wiring
@pytest.mark.asyncio
async def test_agency_client_metrics_uses_revenue_summary(registry: ServiceRegistry, monkeypatch) -> None:
    monkeypatch.setenv("HIRO_API_KEY", "test")
    await registry.invoke("agency", "create_client", {
        "agency_id": "ag1", "tenant_id": TENANT, "name": "Test Co",
        "monthly_target": 10000, "goal_metric": "revenue"})
    # Record an order to generate revenue
    await registry.invoke("analytics.commerce", "record_order", {
        "tenant_id": TENANT, "customer_email": "x@y.com", "amount": 5000,
        "campaign_id": "camp-1", "placed_at": "2026-11-05T10:00:00+00:00"})
    r = await registry.invoke("agency", "roster", {"agency_id": "ag1"})
    client = r["clients"][0]
    assert client["revenue_mtd"] == 5000.0
    assert client["goal_pct"] == 50.0


# ------------------------------------------------------------------ MCP tools
@pytest.mark.asyncio
async def test_mcp_tools_exist() -> None:
    tools = await mcp.list_tools()
    tool_names = {t.name for t in tools}
    assert "ask_hiro" in tool_names
    assert "hiro_roster" in tool_names
    assert "get_roster_summary" in tool_names


__all__ = []