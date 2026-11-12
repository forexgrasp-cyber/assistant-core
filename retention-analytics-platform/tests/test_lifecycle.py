"""Tests for the deeper lifecycle processes: state machine, dunning engine,
health v2, renewal risk, metering/overage, proration, NPS loop, auto-promote,
incidents, win-back timing."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_lifecycle.state_machine import LifecycleService, STATES
from retention_analytics_lifecycle.dunning import DunningEngine, ESCALATION, RETRY_DELAYS
from retention_analytics_lifecycle.health import HealthEngine, THRESHOLDS
from retention_analytics_lifecycle.renewals import RenewalRiskService, CHECKPOINTS
from retention_analytics_lifecycle.billing import MeteringService, ProrationService
from retention_analytics_lifecycle.loops import (
    ExperimentAutoPromoteService,
    IncidentService,
    NPSLoopService,
    WinbackTimingService,
    WINBACK_SCHEDULE,
)

TENANT = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def registry(tmp_path, monkeypatch) -> ServiceRegistry:
    import retention_analytics_core.repository as repo_mod
    import retention_analytics_advanced.customer_intel as ci
    import retention_analytics_lifecycle.state_machine as sm
    import retention_analytics_lifecycle.dunning as du
    import retention_analytics_lifecycle.health as he
    import retention_analytics_lifecycle.renewals as re_
    import retention_analytics_lifecycle.billing as bi
    import retention_analytics_lifecycle.loops as lo
    for mod in (repo_mod, ci, sm, du, he, re_, bi, lo):
        monkeypatch.setattr(mod, "data_root", lambda: tmp_path, raising=False)
    reg = ServiceRegistry()
    for cls in (LifecycleService, DunningEngine, HealthEngine, RenewalRiskService,
                MeteringService, ProrationService, NPSLoopService,
                ExperimentAutoPromoteService, IncidentService, WinbackTimingService):
        cls(reg).register()
    return reg


# --- Lifecycle state machine ---

@pytest.mark.asyncio
async def test_lifecycle_full_journey(registry: ServiceRegistry) -> None:
    r = await registry.invoke("lifecycle", "create", {"tenant_id": TENANT, "subscription_id": "s1", "plan": "pro", "amount": 100})
    assert r["subscription"]["state"] == "trial"
    # trial -> active -> past_due -> grace -> suspended -> cancelled -> churned
    for to, reason in [("active", "card charged"), ("past_due", "payment failed"),
                       ("grace", "grace period"), ("suspended", "grace expired"),
                       ("cancelled", "user cancelled"), ("churned", "30d")]:
        r = await registry.invoke("lifecycle", "transition", {"subscription_id": "s1", "to": to, "reason": reason})
        assert r["status"] == "ok", r
        assert r["to"] == to
    r = await registry.invoke("lifecycle", "get", {"subscription_id": "s1"})
    assert r["subscription"]["state"] == "churned"
    assert len(r["subscription"]["history"]) == 7


@pytest.mark.asyncio
async def test_lifecycle_rejects_invalid_transition(registry: ServiceRegistry) -> None:
    await registry.invoke("lifecycle", "create", {"tenant_id": TENANT, "subscription_id": "s2"})
    # trial -> suspended is invalid
    r = await registry.invoke("lifecycle", "transition", {"subscription_id": "s2", "to": "suspended"})
    assert r["status"] == "invalid_transition"
    assert "active" in r["allowed"] or "cancelled" in r["allowed"]
    # invalid state name
    r = await registry.invoke("lifecycle", "transition", {"subscription_id": "s2", "to": "bogus"})
    assert r["status"] == "invalid_state"


@pytest.mark.asyncio
async def test_lifecycle_reactivation(registry: ServiceRegistry) -> None:
    await registry.invoke("lifecycle", "create", {"tenant_id": TENANT, "subscription_id": "s3"})
    await registry.invoke("lifecycle", "transition", {"subscription_id": "s3", "to": "active"})
    await registry.invoke("lifecycle", "transition", {"subscription_id": "s3", "to": "cancelled"})
    r = await registry.invoke("lifecycle", "transition", {"subscription_id": "s3", "to": "active", "reason": "reactivated"})
    assert r["status"] == "ok" and r["event"] == "client.reactivated"


@pytest.mark.asyncio
async def test_lifecycle_tick_expires_trial(registry: ServiceRegistry) -> None:
    past = (datetime.now(UTC) - timedelta(days=1)).isoformat()
    await registry.invoke("lifecycle", "create", {"tenant_id": TENANT, "subscription_id": "s4", "state": "trial", "trial_ends_at": past})
    r = await registry.invoke("lifecycle", "tick", {})
    assert r["ticked"] >= 1
    g = await registry.invoke("lifecycle", "get", {"subscription_id": "s4"})
    assert g["subscription"]["state"] in ("active", "churned")


# --- Dunning engine ---

@pytest.mark.asyncio
async def test_dunning_escalation_and_attribution(registry: ServiceRegistry) -> None:
    r = await registry.invoke("dunning.engine", "start", {
        "tenant_id": TENANT, "subscription_id": "s1", "customer_email": "a@x.com",
        "customer_phone": "+1", "amount_due": 99, "failure_reason": "insufficient_funds"})
    cid = r["campaign"]["campaign_id"]
    assert r["campaign"]["retry_schedule"] == RETRY_DELAYS["insufficient_funds"]
    assert r["campaign"]["card_updater_enrolled"] is True
    # record 2 failures -> escalation advances
    await registry.invoke("dunning.engine", "record_failure", {"campaign_id": cid, "reason": "insufficient_funds"})
    r = await registry.invoke("dunning.engine", "record_failure", {"campaign_id": cid, "reason": "insufficient_funds"})
    assert r["attempt"]["attempt"] == 2
    # recover attributed to attempt 2
    r = await registry.invoke("dunning.engine", "recover", {"campaign_id": cid, "card_updater": True})
    assert r["recovered_by_attempt"] == 2 and r["amount_recovered"] == 99
    # attribution
    r = await registry.invoke("dunning.engine", "attribution", {"tenant_id": TENANT})
    assert r["recovered"] == 1 and r["recovery_rate"] == 100.0 and r["by_card_updater"] == 1


# --- Health v2 ---

@pytest.mark.asyncio
async def test_health_decay_and_recovery(registry: ServiceRegistry) -> None:
    r = await registry.invoke("health.engine", "compute", {
        "tenant_id": TENANT, "client_id": "c1", "usage_score": 20, "engagement_score": 10,
        "open_tickets": 4, "payment_failures": 2})
    assert r["result"]["score"] < 70
    assert r["result"]["action"] in ("watch", "playbook", "alert", "critical")
    # engage -> score recovers
    r = await registry.invoke("health.engine", "record_engagement", {"tenant_id": TENANT, "client_id": "c1"})
    assert r["score"] > 0
    # thresholds endpoint
    r = await registry.invoke("health.engine", "thresholds", {})
    assert len(r["thresholds"]) == 4


# --- Renewal risk ---

@pytest.mark.asyncio
async def test_renewal_risk_pipeline(registry: ServiceRegistry) -> None:
    renews = (datetime.now(UTC) + timedelta(days=45)).isoformat()
    r = await registry.invoke("renewals.risk", "track", {
        "tenant_id": TENANT, "customer_id": "c1", "subscription_id": "s1", "arr": 12000,
        "renews_at": renews, "health": 40, "payment_failures": 1, "open_tickets": 2, "usage_trend": -20})
    rid = r["renewal_id"]
    r = await registry.invoke("renewals.risk", "score", {"renewal_id": rid, "health": 40, "payment_failures": 1, "open_tickets": 2, "usage_trend": -20})
    assert r["risk_tier"] in ("high", "critical")
    assert r["playbook"] in ("churn-save", "executive-save")
    # at 45 days left, the 90 and 60 checkpoints are due (already passed); 30/14/7 are future
    r = await registry.invoke("renewals.risk", "tick", {"tenant_id": TENANT})
    cps = [d["checkpoint"] for d in r["due"]]
    assert 90 in cps and 60 in cps and 30 not in cps and 14 not in cps and 7 not in cps
    # after they fire, a re-tick does not repeat them
    r = await registry.invoke("renewals.risk", "tick", {"tenant_id": TENANT})
    assert r["count"] == 0


# --- Metering + proration ---

@pytest.mark.asyncio
async def test_metering_thresholds_and_overage(registry: ServiceRegistry) -> None:
    await registry.invoke("metering.v2", "set_quota", {
        "tenant_id": TENANT, "resource": "api_calls", "limit": 100, "overage_price": 0.5, "hard_cap": True})
    for _ in range(85):
        await registry.invoke("metering.v2", "record", {"tenant_id": TENANT, "resource": "api_calls", "amount": 1})
    r = await registry.invoke("metering.v2", "record", {"tenant_id": TENANT, "resource": "api_calls", "amount": 30})
    check = r["check"]
    assert check["pct"] > 100
    assert 80 in check["alerts_triggered"] and 100 in check["alerts_triggered"]
    assert check["hard_capped"] is True
    r = await registry.invoke("metering.v2", "overage_lines", {"tenant_id": TENANT, "resource": "api_calls"})
    assert r["lines"][0]["overage_units"] == pytest.approx(15, abs=0.5)
    assert r["total"] == pytest.approx(7.5, abs=0.5)


@pytest.mark.asyncio
async def test_proration_upgrade_and_downgrade(registry: ServiceRegistry) -> None:
    start = (datetime.now(UTC) - timedelta(days=15)).isoformat()
    end = (datetime.now(UTC) + timedelta(days=15)).isoformat()
    r = await registry.invoke("billing.proration", "quote_change", {
        "current_price": 100, "new_price": 200, "period_start": start, "period_end": end})
    q = r["quote"]
    assert q["direction"] == "charge" and q["net_delta"] > 0
    r = await registry.invoke("billing.proration", "quote_change", {
        "current_price": 200, "new_price": 100, "period_start": start, "period_end": end})
    assert r["quote"]["direction"] == "credit" and r["quote"]["net_delta"] < 0


# --- Loops ---

@pytest.mark.asyncio
async def test_nps_loop_all_kinds(registry: ServiceRegistry) -> None:
    r = await registry.invoke("nps.loop", "handle_response", {"tenant_id": TENANT, "client_id": "c1", "score": 3, "comment": "angry"})
    assert r["kind"] == "detractor" and r["action"]["priority"] == "urgent"
    r = await registry.invoke("nps.loop", "handle_response", {"tenant_id": TENANT, "client_id": "c2", "score": 7})
    assert r["kind"] == "passive"
    r = await registry.invoke("nps.loop", "handle_response", {"tenant_id": TENANT, "client_id": "c3", "score": 10})
    assert r["kind"] == "promoter" and r["action"]["type"] == "referral_ask"


@pytest.mark.asyncio
async def test_experiment_auto_promote(registry: ServiceRegistry) -> None:
    # B clearly better and significant
    r = await registry.invoke("experiments.auto", "evaluate", {
        "experiment_id": "exp1",
        "results": {"A": {"sent": 1000, "converted": 50}, "B": {"sent": 1000, "converted": 120}}})
    assert r["significant"] is True and r["winner"] == "B" and r["decision"]["action"] == "promote"
    # not significant
    r = await registry.invoke("experiments.auto", "evaluate", {
        "experiment_id": "exp2",
        "results": {"A": {"sent": 10, "converted": 1}, "B": {"sent": 10, "converted": 2}}})
    assert r["significant"] is False and r["decision"] is None


@pytest.mark.asyncio
async def test_incident_from_anomaly_with_comms(registry: ServiceRegistry) -> None:
    r = await registry.invoke("incidents", "create_from_anomaly", {
        "tenant_id": TENANT, "metric": "churn_rate",
        "anomaly": {"severity": "critical", "direction": "spike", "deviation_pct": 85}})
    iid = r["incident"]["incident_id"]
    assert r["incident"]["status"] == "open"
    r = await registry.invoke("incidents", "comms_draft", {"incident_id": iid})
    assert "Update on churn_rate" in r["draft"]
    r = await registry.invoke("incidents", "update_status", {"incident_id": iid, "status": "mitigated"})
    assert r["incident"]["status"] == "mitigated"


@pytest.mark.asyncio
async def test_winback_730_90(registry: ServiceRegistry) -> None:
    past = (datetime.now(UTC) - timedelta(days=40)).isoformat()
    r = await registry.invoke("winback.timing", "schedule", {
        "tenant_id": TENANT, "customer_id": "c1", "email": "c1@x.com", "churned_at": past})
    assert [t["day"] for t in r["winback"]["touches"]] == WINBACK_SCHEDULE
    r = await registry.invoke("winback.timing", "due", {})
    days = [d["day"] for d in r["due"]]
    assert 7 in days and 30 in days and 90 not in days  # 90d not yet due at 40d
