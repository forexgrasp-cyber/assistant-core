"""Tests for the campaign orchestration layer: segment -> flows -> run -> measure."""

from __future__ import annotations

import pytest

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_ux.campaign import CAMPAIGN_GOALS, CampaignService, evaluate_segment

TENANT = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def registry(tmp_path, monkeypatch) -> ServiceRegistry:
    import retention_analytics_core.repository as repo_mod
    import retention_analytics_ux.campaign as camp_mod
    monkeypatch.setattr(repo_mod, "data_root", lambda: tmp_path)
    monkeypatch.setattr(camp_mod, "data_root", lambda: tmp_path)
    reg = ServiceRegistry()
    CampaignService(reg).register()
    return reg


def test_evaluate_segment_criteria() -> None:
    clients = [
        {"id": "c1", "health_score": 30, "plan": "growth"},
        {"id": "c2", "health_score": 80, "plan": "starter"},
        {"id": "c3", "health_score": 45, "plan": "growth"},
    ]
    matched = evaluate_segment({"health_score": {"lt": 50}, "plan": "growth"}, clients)
    assert len(matched) == 2
    assert {c["id"] for c in matched} == {"c1", "c3"}

    matched = evaluate_segment({"plan": {"in": ["growth", "enterprise"]}}, clients)
    assert len(matched) == 2


def test_campaign_goals_have_defaults() -> None:
    for goal_id, g in CAMPAIGN_GOALS.items():
        assert g["default_flows"], f"{goal_id} has no default flows"
        assert g["default_metrics"], f"{goal_id} has no default metrics"
    assert "reduce_churn" in CAMPAIGN_GOALS
    assert "recover_payments" in CAMPAIGN_GOALS


@pytest.mark.asyncio
async def test_campaign_lifecycle(registry: ServiceRegistry) -> None:
    # Create
    r = await registry.invoke("campaigns", "create", {
        "tenant_id": TENANT, "name": "Q4 churn save", "goal": "reduce_churn",
        "segment": {"id": "at-risk", "name": "At-risk", "criteria": {"health_score": {"lt": 50}}},
    })
    cid = r["campaign"]["campaign_id"]
    assert r["campaign"]["status"] == "draft"
    assert "churn-prevention" in r["campaign"]["flows"]  # from goal defaults

    # List
    r = await registry.invoke("campaigns", "list", {"tenant_id": TENANT})
    assert r["count"] == 1

    # Activate
    r = await registry.invoke("campaigns", "activate", {"tenant_id": TENANT, "campaign_id": cid})
    assert r["status"] == "active"

    # Run with clients — segment filters to at-risk only
    r = await registry.invoke("campaigns", "run", {
        "tenant_id": TENANT, "campaign_id": cid,
        "clients": [
            {"id": "c1", "client_email": "a@x.com", "health_score": 30},
            {"id": "c2", "client_email": "b@x.com", "health_score": 80},
            {"id": "c3", "client_email": "c@x.com", "health_score": 40},
        ],
    })
    assert r["status"] == "ok"
    # Only c1 and c3 match (health < 50)
    assert r["results"]["segment_size"] == 2
    assert r["results"]["outcomes_count"] == 2 * len(r["results"]["flows_run"])
    assert "baseline" in r["results"] and "after" in r["results"] and "deltas" in r["results"]

    # Results
    r = await registry.invoke("campaigns", "results", {"tenant_id": TENANT, "campaign_id": cid})
    assert r["results"]["segment_size"] == 2
    assert len(r["runs"]) >= 1

    # Pause + delete
    await registry.invoke("campaigns", "pause", {"tenant_id": TENANT, "campaign_id": cid})
    r = await registry.invoke("campaigns", "get", {"tenant_id": TENANT, "campaign_id": cid})
    assert r["campaign"]["status"] == "paused"
    r = await registry.invoke("campaigns", "delete", {"tenant_id": TENANT, "campaign_id": cid})
    assert r["status"] == "deleted"


@pytest.mark.asyncio
async def test_segment_evaluation_endpoint(registry: ServiceRegistry) -> None:
    r = await registry.invoke("campaigns", "evaluate_segment", {
        "criteria": {"mrr": {"gt": 100}},
        "clients": [{"id": "a", "mrr": 500}, {"id": "b", "mrr": 50}],
    })
    assert r["matched"] == 1
    assert r["members"][0]["id"] == "a"
