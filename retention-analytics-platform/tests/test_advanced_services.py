"""Tests for advanced universal services: customer 360, service-due, benchmarks,
goals, VoC, A/B testing, sequences, catalog, walls, journeys, attribution,
anomaly detection, pricing experiments, QBR, presets."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced.customer_intel import (
    BenchmarksService,
    Customer360Service,
    GoalsService,
    ServiceDueService,
    VoiceOfCustomerService,
    compute_due,
)
from retention_analytics_advanced.experiments import (
    ABTestingService,
    AnomalyDetectionService,
    AttributionService,
    CatalogService,
    JourneyService,
    PricingExperimentService,
    QBRService,
    SequenceService,
    WallsService,
)
from retention_analytics_advanced.presets import PRESETS, PresetCatalogService

TENANT = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def registry(tmp_path, monkeypatch) -> ServiceRegistry:
    import retention_analytics_core.repository as repo_mod
    import retention_analytics_advanced.customer_intel as ci
    import retention_analytics_advanced.experiments as ex
    import retention_analytics_advanced.presets as pr
    for mod in (repo_mod, ci, ex, pr):
        monkeypatch.setattr(mod, "data_root", lambda: tmp_path)
    reg = ServiceRegistry()
    # Presets create segments + campaigns, so those services must exist
    from retention_analytics_growth.service import SegmentationService
    from retention_analytics_ux.campaign import CampaignService
    for cls in (Customer360Service, ServiceDueService, BenchmarksService, GoalsService,
                VoiceOfCustomerService, ABTestingService, SequenceService, CatalogService,
                WallsService, JourneyService, AttributionService, AnomalyDetectionService,
                PricingExperimentService, QBRService, PresetCatalogService,
                SegmentationService, CampaignService):
        cls(reg).register()
    return reg


def test_compute_due() -> None:
    last = (datetime.now(UTC) - timedelta(days=175)).isoformat()
    nxt, days = compute_due(last, 180)
    assert nxt is not None
    assert days == 5  # 175 days ago + 180 = 5 days out
    assert compute_due(None, 30) == (None, None)


@pytest.mark.asyncio
async def test_customer_360(registry: ServiceRegistry) -> None:
    last = (datetime.now(UTC) - timedelta(days=20)).isoformat()
    r = await registry.invoke("customers.360", "upsert_profile", {
        "tenant_id": TENANT, "id": "cust-1", "name": "Jane", "email": "jane@x.com",
        "plan": "growth", "mrr": 500, "last_service_date": last,
        "service_interval_days": 30, "service_name": "oil change",
    })
    prof = r["profile"]
    assert prof["days_until_due"] == 10
    assert prof["next_due_date"] is not None

    await registry.invoke("customers.360", "log_touchpoint", {
        "tenant_id": TENANT, "customer_id": "cust-1", "type": "call", "summary": "QBR"})
    await registry.invoke("customers.360", "link_recording", {
        "tenant_id": TENANT, "customer_id": "cust-1", "url": "https://rec/1", "duration_seconds": 120})
    await registry.invoke("customers.360", "enrich", {
        "tenant_id": TENANT, "id": "cust-1", "industry": "automotive", "company_name": "Jane Auto"})

    r = await registry.invoke("customers.360", "get_profile", {"id": "cust-1"})
    assert r["profile"]["enrichment"]["industry"] == "automotive"
    assert len(r["profile"]["touchpoints"]) == 1
    assert len(r["profile"]["recordings"]) == 1

    r = await registry.invoke("customers.360", "timeline", {"id": "cust-1"})
    assert r["count"] >= 3


@pytest.mark.asyncio
async def test_service_due_detection(registry: ServiceRegistry) -> None:
    due_soon = (datetime.now(UTC) - timedelta(days=25)).isoformat()  # 30d interval -> 5 days out
    overdue = (datetime.now(UTC) - timedelta(days=45)).isoformat()  # -> 15 days overdue
    await registry.invoke("customers.360", "upsert_profile", {
        "tenant_id": TENANT, "id": "c1", "email": "a@x.com", "last_service_date": due_soon, "service_interval_days": 30})
    await registry.invoke("customers.360", "upsert_profile", {
        "tenant_id": TENANT, "id": "c2", "email": "b@x.com", "last_service_date": overdue, "service_interval_days": 30})

    r = await registry.invoke("customers.service_due", "scan", {"tenant_id": TENANT, "within_days": 7})
    assert r["due_soon_count"] == 1
    assert r["overdue_count"] == 1

    r = await registry.invoke("customers.service_due", "schedule_reminders", {"tenant_id": TENANT, "within_days": 7})
    assert r["count"] == 2
    states = {rem["state"] for rem in r["reminders"]}
    assert states == {"due_soon", "overdue"}


@pytest.mark.asyncio
async def test_benchmarks(registry: ServiceRegistry) -> None:
    r = await registry.invoke("benchmarks", "compare", {
        "industry": "saas", "metrics": {"churn_rate": 0.02, "mrr_growth_rate": 0.05, "ltv_cac_ratio": 2.0}})
    rows = {r_["metric"]: r_ for r_ in r["comparison"]}
    assert rows["churn_rate"]["verdict"] == "better"  # 2% < 3.5% benchmark
    assert rows["mrr_growth_rate"]["verdict"] == "worse"  # 5% < 12%
    assert rows["ltv_cac_ratio"]["verdict"] == "worse"


@pytest.mark.asyncio
async def test_goals(registry: ServiceRegistry) -> None:
    r = await registry.invoke("goals", "create", {
        "tenant_id": TENANT, "name": "Reach 100k MRR", "metric": "mrr", "target": 100000, "current": 50000})
    gid = r["goal"]["goal_id"]
    r = await registry.invoke("goals", "list", {"tenant_id": TENANT})
    assert r["goals"][0]["progress_pct"] == 50.0
    assert r["goals"][0]["on_track"] is True
    await registry.invoke("goals", "update_progress", {"goal_id": gid, "current": 90000})
    r = await registry.invoke("goals", "list", {"tenant_id": TENANT})
    assert r["goals"][0]["progress_pct"] == 90.0


@pytest.mark.asyncio
async def test_voc_board(registry: ServiceRegistry) -> None:
    r = await registry.invoke("feedback.voc", "submit", {"tenant_id": TENANT, "title": "Dark mode", "body": "Please"})
    iid = r["item"]["id"]
    await registry.invoke("feedback.voc", "upvote", {"id": iid})
    await registry.invoke("feedback.voc", "upvote", {"id": iid})
    r = await registry.invoke("feedback.voc", "list", {"tenant_id": TENANT})
    assert r["items"][0]["votes"] == 2
    await registry.invoke("feedback.voc", "set_status", {"id": iid, "status": "planned"})
    r = await registry.invoke("feedback.voc", "list", {"tenant_id": TENANT})
    assert r["items"][0]["status"] == "planned"


@pytest.mark.asyncio
async def test_ab_testing(registry: ServiceRegistry) -> None:
    r = await registry.invoke("experiments.ab", "create", {
        "tenant_id": TENANT, "name": "Subject line test",
        "variants": [{"id": "A", "name": "control"}, {"id": "B", "name": "variant"}], "metric": "open_rate"})
    eid = r["experiment"]["experiment_id"]
    await registry.invoke("experiments.ab", "record_result", {"experiment_id": eid, "variant_id": "A", "sent": 100, "converted": 10})
    await registry.invoke("experiments.ab", "record_result", {"experiment_id": eid, "variant_id": "B", "sent": 100, "converted": 25})
    r = await registry.invoke("experiments.ab", "analyze", {"experiment_id": eid})
    assert r["variants"][0]["variant_id"] == "B"
    assert r["variants"][0]["conversion_rate"] == 25.0
    assert r["lift_pct"] == 150.0
    await registry.invoke("experiments.ab", "annotate", {"experiment_id": eid, "note": "Shipped B"})
    r = await registry.invoke("experiments.ab", "get", {"experiment_id": eid})
    assert len(r["experiment"]["notes"]) == 1


@pytest.mark.asyncio
async def test_sequences(registry: ServiceRegistry) -> None:
    r = await registry.invoke("automation.sequences", "create", {
        "tenant_id": TENANT, "name": "3-touch",
        "steps": [{"delay_days": 0, "channel": "email"}, {"delay_days": 3, "channel": "sms"}]})
    sid = r["sequence"]["sequence_id"]
    r = await registry.invoke("automation.sequences", "enroll", {"sequence_id": sid, "customer_id": "c1"})
    enr = r["enrollment"]["enrollment_id"]
    r = await registry.invoke("automation.sequences", "advance", {"enrollment_id": enr})
    assert r["enrollment"]["current_step"] == 1
    r = await registry.invoke("automation.sequences", "advance", {"enrollment_id": enr})
    assert r["enrollment"]["status"] == "completed"


@pytest.mark.asyncio
async def test_catalog_and_cross_sell(registry: ServiceRegistry) -> None:
    await registry.invoke("catalog", "add_product", {
        "tenant_id": TENANT, "name": "Premium Plan", "price": 99, "category": "growth", "tags": ["premium"]})
    await registry.invoke("catalog", "add_product", {
        "tenant_id": TENANT, "name": "Add-on Pack", "price": 20, "category": "starter", "tags": ["addons"]})
    listed = await registry.invoke("catalog", "list_products", {"tenant_id": TENANT})
    assert len(listed["products"]) == 2, f"products not persisted: {listed}"
    r = await registry.invoke("catalog", "recommend_cross_sell", {
        "tenant_id": TENANT, "customer": {"plan": "growth", "tags": ["premium"], "products": []}})
    assert len(r["recommendations"]) >= 1, f"no recommendations: {r}"
    # Premium Plan matches both plan category (0.4) and tag (0.3) -> highest score
    assert r["recommendations"][0]["product"]["name"] == "Premium Plan"

    # Already-owned products are excluded
    premium_id = next(p["product_id"] for p in listed["products"] if p["name"] == "Premium Plan")
    r = await registry.invoke("catalog", "recommend_cross_sell", {
        "tenant_id": TENANT, "customer": {"plan": "growth", "tags": ["premium"], "products": [premium_id]}})
    owned_names = [rec["product"]["name"] for rec in r["recommendations"]]
    assert "Premium Plan" not in owned_names


@pytest.mark.asyncio
async def test_walls(registry: ServiceRegistry) -> None:
    r = await registry.invoke("walls", "create", {
        "tenant_id": TENANT, "customer_id": "c1", "type": "payment", "amount_due": 99,
        "gated_features": ["reports", "exports"], "message": "Update your card to continue"})
    wid = r["wall"]["wall_id"]
    r = await registry.invoke("walls", "check", {"customer_id": "c1"})
    assert r["walled"] is True
    assert "reports" in r["gated_features"]
    await registry.invoke("walls", "resolve", {"wall_id": wid, "resolution": "card updated"})
    r = await registry.invoke("walls", "check", {"customer_id": "c1"})
    assert r["walled"] is False


@pytest.mark.asyncio
async def test_journey_stages(registry: ServiceRegistry) -> None:
    r = await registry.invoke("journeys", "create", {"tenant_id": TENANT, "name": "Onboarding"})
    jid = r["journey"]["journey_id"]
    await registry.invoke("journeys", "set_stage", {"journey_id": jid, "customer_id": "c1", "stage": "adoption"})
    await registry.invoke("journeys", "set_stage", {"journey_id": jid, "customer_id": "c2", "stage": "renewal"})
    r = await registry.invoke("journeys", "stage_distribution", {"journey_id": jid})
    assert r["total"] == 2
    assert r["distribution"]["adoption"] == 1


@pytest.mark.asyncio
async def test_attribution(registry: ServiceRegistry) -> None:
    await registry.invoke("analytics.attribution", "record_outcome", {
        "tenant_id": TENANT, "customer_id": "c1", "campaign_id": "camp-1", "outcome": "retained", "value": 500})
    await registry.invoke("analytics.attribution", "record_outcome", {
        "tenant_id": TENANT, "customer_id": "c2", "campaign_id": "camp-1", "outcome": "churned"})
    r = await registry.invoke("analytics.attribution", "campaign_impact", {"tenant_id": TENANT})
    row = r["campaigns"][0]
    assert row["campaign_id"] == "camp-1"
    assert row["value_saved"] == 500
    assert row["save_rate"] == 50.0


@pytest.mark.asyncio
async def test_anomaly_detection(registry: ServiceRegistry) -> None:
    r = await registry.invoke("analytics.anomaly", "detect", {
        "series": [100, 102, 98, 101, 100, 99, 101, 160], "metric": "churn_rate", "threshold_pct": 20})
    assert r["count"] >= 1
    assert any(a["direction"] == "spike" for a in r["anomalies"])


@pytest.mark.asyncio
async def test_pricing_experiment(registry: ServiceRegistry) -> None:
    r = await registry.invoke("experiments.pricing", "create", {
        "tenant_id": TENANT, "name": "Price test", "price_points": [49, 99]})
    tid = r["test"]["test_id"]
    await registry.invoke("experiments.pricing", "record_result", {"test_id": tid, "price_point": 49, "exposed": 100, "converted": 10})
    await registry.invoke("experiments.pricing", "record_result", {"test_id": tid, "price_point": 99, "exposed": 100, "converted": 20})
    r = await registry.invoke("experiments.pricing", "analyze", {"test_id": tid})
    assert r["best_price"]["price"] == 99.0
    assert r["best_price"]["revenue_per_exposed"] == 19.8


@pytest.mark.asyncio
async def test_qbr_generation(registry: ServiceRegistry) -> None:
    await registry.invoke("customers.360", "upsert_profile", {
        "tenant_id": TENANT, "id": "cust-1", "name": "Jane", "plan": "growth", "mrr": 500, "health_score": 45})
    await registry.invoke("customers.360", "log_touchpoint", {"tenant_id": TENANT, "customer_id": "cust-1", "type": "call"})
    r = await registry.invoke("cs.qbr", "generate", {"tenant_id": TENANT, "customer_id": "cust-1", "period": "Q4"})
    headings = [s["heading"] for s in r["qbr"]["sections"]]
    assert "Account overview" in headings
    assert "Risks" in headings


def test_presets_are_universal_and_complete() -> None:
    assert len(PRESETS) >= 6
    for pid, preset in PRESETS.items():
        assert preset.get("customer_fields"), f"{pid} has no customer fields"
        assert preset.get("segments"), f"{pid} has no segments"
        assert preset.get("campaigns"), f"{pid} has no campaigns"
        for c in preset["campaigns"]:
            assert c.get("flows"), f"{pid} campaign {c.get('name')} has no flows"
            assert c.get("metrics"), f"{pid} campaign {c.get('name')} has no metrics"


@pytest.mark.asyncio
async def test_preset_apply_creates_objects(registry: ServiceRegistry) -> None:
    r = await registry.invoke("presets", "apply", {"tenant_id": TENANT, "preset_id": "automotive"})
    app = r["application"]
    assert app["campaigns_created"] >= 2
    assert app["sequences_created"] >= 1
    assert app["customer_fields"]["service_interval_days"] == "number"
    r = await registry.invoke("presets", "applied", {"tenant_id": TENANT})
    assert len(r["applications"]) == 1
