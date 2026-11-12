"""Tests for data transfer (CSV import/export) and connectors."""

from __future__ import annotations

import pytest

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced.customer_intel import Customer360Service
from retention_analytics_advanced.datatransfer import DataTransferService
from retention_analytics_advanced.connectors import ConnectorService

TENANT = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def registry(tmp_path, monkeypatch) -> ServiceRegistry:
    import retention_analytics_core.repository as repo_mod
    import retention_analytics_advanced.customer_intel as ci
    import retention_analytics_advanced.datatransfer as dt
    import retention_analytics_advanced.connectors as co
    for mod in (repo_mod, ci, dt, co):
        monkeypatch.setattr(mod, "data_root", lambda: tmp_path)
    reg = ServiceRegistry()
    Customer360Service(reg).register()
    DataTransferService(reg).register()
    ConnectorService(reg).register()
    return reg


@pytest.mark.asyncio
async def test_customer_csv_import_export_roundtrip(registry: ServiceRegistry) -> None:
    csv_text = "name,email,plan,mrr,service_name,last_service_date,service_interval_days\nJane,jane@x.com,premium,120,oil change,2026-05-15,180\nBob,bob@x.com,starter,40,tire rotation,2026-10-01,90\n"
    r = await registry.invoke("data.transfer", "import_customers", {"tenant_id": TENANT, "csv": csv_text})
    imp = r["import"]
    assert imp["created"] == 2
    assert imp["mapping"]["email"] == "email"
    assert imp["mapping"]["mrr"] == "mrr"

    # profiles persisted with computed due dates
    r = await registry.invoke("customers.360", "list_profiles", {"tenant_id": TENANT})
    assert r["count"] == 2
    jane = next(p for p in r["profiles"] if p["email"] == "jane@x.com")
    assert jane["service_name"] == "oil change"
    assert jane["days_until_due"] is not None

    # export CSV
    r = await registry.invoke("data.transfer", "export_customers", {"tenant_id": TENANT, "format": "csv"})
    assert r["count"] == 2
    assert "jane@x.com" in r["csv"]
    assert "name" in r["csv"].split("\n")[0]

    # export JSON
    r = await registry.invoke("data.transfer", "export_customers", {"tenant_id": TENANT, "format": "json"})
    assert r["count"] == 2 and r["data"][0]["email"]

    # re-import same CSV -> updates, not duplicates
    r = await registry.invoke("data.transfer", "import_customers", {"tenant_id": TENANT, "csv": csv_text})
    assert r["import"]["updated"] == 2 and r["import"]["created"] == 0


@pytest.mark.asyncio
async def test_mapping_suggestion(registry: ServiceRegistry) -> None:
    r = await registry.invoke("data.transfer", "suggest_mapping", {
        "columns": ["Email Address", "Full Name", "Phone", "Plan Tier", "MRR", "Service Due Date", "Interval", "Random"]})
    m = r["mapping"]
    assert m["Email Address"] == "email"
    assert m["Full Name"] == "name"
    assert m["Phone"] == "phone"
    assert m["Plan Tier"] == "plan"
    assert m["MRR"] == "mrr"
    assert "Random" in r["unmapped"]


@pytest.mark.asyncio
async def test_campaigns_export(registry: ServiceRegistry) -> None:
    # seed a campaign via the store directly
    from retention_analytics_advanced.customer_intel import _JsonStore
    _JsonStore("campaigns.json").upsert("campaign_id", {
        "campaign_id": "camp-1", "tenant_id": TENANT, "name": "X", "goal": "reduce_churn",
        "segment": {"id": "all"}, "flows": ["churn-prevention"], "schedule": {"type": "once"},
        "success_metrics": ["retention"], "status": "draft", "created_at": "2026-01-01", "runs": [], "results": None})
    r = await registry.invoke("data.transfer", "export_campaigns", {"tenant_id": TENANT, "format": "csv"})
    assert r["count"] == 1
    assert "camp-1" in r["csv"] and "churn-prevention" in r["csv"]


@pytest.mark.asyncio
async def test_connectors_supported_and_no_creds(registry: ServiceRegistry, monkeypatch) -> None:
    r = await registry.invoke("connectors", "supported", {})
    assert "stripe" in r["connectors"] and "hubspot" in r["connectors"]

    # without env keys -> graceful no_credentials
    for k in list(__import__("os").environ):
        if k.startswith(("STRIPE_", "HUBSPOT_", "SALESFORCE_", "ZENDESK_", "MIXPANEL_", "GA_", "INTERCOM_", "SEGMENT_")):
            monkeypatch.delenv(k, raising=False)
    r = await registry.invoke("connectors", "stripe_sync", {"tenant_id": TENANT})
    assert r["status"] == "no_credentials"
    r = await registry.invoke("connectors", "hubspot_sync", {"tenant_id": TENANT})
    assert r["status"] == "no_credentials"

    # segment track works without creds (records the forward)
    r = await registry.invoke("connectors", "segment_track", {"tenant_id": TENANT, "event": "Signed Up", "properties": {"plan": "pro"}})
    assert r["status"] == "ok" and r["forwarded"] is True

    # sync history records the segment call
    r = await registry.invoke("connectors", "sync_history", {"tenant_id": TENANT})
    assert len(r["syncs"]) >= 1
