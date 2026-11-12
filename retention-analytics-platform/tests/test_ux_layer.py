"""Tests for the UX layer: settings, saved reports, bulk events, flow management."""

from __future__ import annotations

import pytest

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_ux.service import (
    BulkEventService,
    FlowManagementService,
    SavedReportService,
    TenantSettingsService,
    EVENT_SCHEMAS,
)

TENANT = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def registry(tmp_path, monkeypatch) -> ServiceRegistry:
    import retention_analytics_core.repository as repo_mod
    monkeypatch.setattr(repo_mod, "data_root", lambda: tmp_path)
    reg = ServiceRegistry()
    for cls in (TenantSettingsService, SavedReportService, BulkEventService, FlowManagementService):
        cls(reg).register()
    return reg


@pytest.mark.asyncio
async def test_settings_crud(registry: ServiceRegistry) -> None:
    r = await registry.invoke("ux.settings", "get", {"tenant_id": TENANT})
    assert r["settings"]["notifications"]["email"] is True

    r = await registry.invoke("ux.settings", "update", {"tenant_id": TENANT, "updates": {"notifications": {"sms": True}, "data_retention_days": 90}})
    assert r["settings"]["notifications"]["sms"] is True
    assert r["settings"]["data_retention_days"] == 90
    assert r["settings"]["notifications"]["email"] is True  # preserved

    r = await registry.invoke("ux.settings", "set_flag", {"tenant_id": TENANT, "flag": "ai_features", "enabled": False})
    assert r["enabled"] is False
    r = await registry.invoke("ux.settings", "get", {"tenant_id": TENANT})
    assert r["settings"]["feature_flags"]["ai_features"] is False


@pytest.mark.asyncio
async def test_api_keys(registry: ServiceRegistry) -> None:
    r = await registry.invoke("ux.settings", "create_api_key", {"tenant_id": TENANT, "name": "Prod"})
    assert r["key"].startswith("ra_live_")
    r = await registry.invoke("ux.settings", "list_api_keys", {"tenant_id": TENANT})
    assert len(r["keys"]) == 1
    assert "full_key" not in r["keys"][0]  # not exposed in list
    r = await registry.invoke("ux.settings", "revoke_api_key", {"tenant_id": TENANT, "key_id": r["keys"][0]["key_id"]})
    assert r["status"] == "revoked"


@pytest.mark.asyncio
async def test_saved_reports(registry: ServiceRegistry) -> None:
    r = await registry.invoke("ux.reports", "save", {
        "tenant_id": TENANT, "name": "Q4 Review", "format": "pdf",
        "filters": {"time_range": "90d", "segment": "at-risk"},
        "widgets": ["retention", "saas"], "schedule": {"frequency": "weekly"},
    })
    rid = r["report"]["report_id"]
    assert r["report"]["filters"]["time_range"] == "90d"

    r = await registry.invoke("ux.reports", "list", {"tenant_id": TENANT})
    assert r["count"] == 1

    r = await registry.invoke("ux.reports", "run", {"tenant_id": TENANT, "report_id": rid})
    assert r["status"] == "ok"
    assert "ran_at" in r["result"]

    r = await registry.invoke("ux.reports", "delete", {"tenant_id": TENANT, "report_id": rid})
    assert r["status"] == "deleted"
    r = await registry.invoke("ux.reports", "list", {"tenant_id": TENANT})
    assert r["count"] == 0


@pytest.mark.asyncio
async def test_event_schemas_and_mapping(registry: ServiceRegistry) -> None:
    r = await registry.invoke("ux.events", "schemas", {})
    assert "client.created" in r["schemas"]
    assert any(f["field"] == "client_email" for f in r["schemas"]["client.created"])

    # Field mapping suggestion
    r = await registry.invoke("ux.events", "map_fields", {
        "event_type": "client.created",
        "columns": ["Email Address", "Full Name", "Phone Number", "Random Col"],
    })
    assert r["mapping"].get("Email Address") == "client_email"
    assert r["mapping"].get("Full Name") == "name"
    assert "Random Col" in r["unmapped"] or r["mapping"].get("Random Col", "") == ""


@pytest.mark.asyncio
async def test_bulk_import(registry: ServiceRegistry) -> None:
    rows = [
        {"email": "a@x.com", "name": "A"},
        {"email": "b@x.com", "name": "B"},
    ]
    r = await registry.invoke("ux.events", "bulk_import", {
        "tenant_id": TENANT, "event_type": "client.created",
        "rows": rows, "mapping": {"email": "client_email", "name": "name"},
    })
    assert r["import"]["imported"] == 2
    assert r["import"]["rows_total"] == 2

    r = await registry.invoke("ux.events", "export", {"tenant_id": TENANT})
    assert r["count"] >= 1


@pytest.mark.asyncio
async def test_flow_management(registry: ServiceRegistry) -> None:
    r = await registry.invoke("ux.flows", "set_active", {"tenant_id": TENANT, "workflow_id": "churn-prevention", "active": False})
    assert r["active"] is False

    r = await registry.invoke("ux.flows", "set_target", {"tenant_id": TENANT, "workflow_id": "churn-prevention", "segment_id": "seg-1", "segment_name": "At-risk SaaS"})
    assert r["target"] == "At-risk SaaS"

    r = await registry.invoke("ux.flows", "list_config", {"tenant_id": TENANT})
    assert r["config"]["churn-prevention"]["active"] is False
    assert r["config"]["churn-prevention"]["target_segment"]["name"] == "At-risk SaaS"


def test_event_schemas_cover_competitor_events() -> None:
    expected = ["client.created", "client.churn_risk", "order.abandoned_cart", "order.placed",
                "subscription.cancelled", "subscription.past_due", "payment.failed", "survey.nps_due", "usage.dropped"]
    for ev in expected:
        assert ev in EVENT_SCHEMAS, f"missing schema for {ev}"
        assert len(EVENT_SCHEMAS[ev]) >= 2, f"schema for {ev} too thin"
