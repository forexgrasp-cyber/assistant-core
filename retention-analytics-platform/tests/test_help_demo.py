"""Tests for help system and interactive demo."""

from __future__ import annotations

import pytest

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced.help_demo import HelpService, DemoService
from retention_analytics_advanced.customer_intel import Customer360Service, ServiceDueService
from retention_analytics_ux.campaign import CampaignService
from retention_analytics_ux.service import SavedReportService

TENANT = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def registry(tmp_path, monkeypatch) -> ServiceRegistry:
    import retention_analytics_core.repository as repo_mod
    import retention_analytics_advanced.customer_intel as ci
    import retention_analytics_advanced.help_demo as hd
    import retention_analytics_ux.campaign as camp
    import retention_analytics_ux.service as ux
    for mod in (repo_mod, ci, hd, camp, ux):
        monkeypatch.setattr(mod, "data_root", lambda: tmp_path)
    reg = ServiceRegistry()
    for cls in (HelpService, DemoService, Customer360Service, ServiceDueService, CampaignService, SavedReportService):
        cls(reg).register()
    return reg


@pytest.mark.asyncio
async def test_help_list_and_search(registry: ServiceRegistry) -> None:
    r = await registry.invoke("help", "list", {})
    assert r["count"] >= 9
    assert any(a["id"] == "campaigns" for a in r["articles"])

    r = await registry.invoke("help", "search", {"q": "churn"})
    assert len(r["results"]) >= 1

    r = await registry.invoke("help", "context", {"context": "campaigns"})
    assert r["article"]["title"] == "Campaigns"
    assert len(r["related"]) >= 2


@pytest.mark.asyncio
async def test_demo_runs_end_to_end(registry: ServiceRegistry) -> None:
    r = await registry.invoke("demo", "run", {"tenant_id": TENANT})
    assert r["status"] == "ok"
    s = r["summary"]
    assert s["customers_seeded"] == 6
    assert s["due_soon"] >= 1
    assert s["overdue"] >= 1
    assert s["campaign_segment_size"] >= 1
    assert s["reminders_scheduled"] >= 1
    assert s["report_id"]
    # every step logged
    assert len(r["steps"]) == 6

    r = await registry.invoke("demo", "history", {"tenant_id": TENANT})
    assert len(r["runs"]) == 1


@pytest.mark.asyncio
async def test_demo_scenario(registry: ServiceRegistry) -> None:
    r = await registry.invoke("demo", "scenario", {})
    assert len(r["scenario"]["steps"]) == 6
