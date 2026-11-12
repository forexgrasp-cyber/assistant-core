"""Tests for automation services: scheduled reports, flow editor, cancel-flow API,
slack bot, session replay, micro-surveys, universal export."""

from __future__ import annotations

import pytest

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_ux.service import SavedReportService
from retention_analytics_advanced.automation import (
    CancelFlowAPI,
    FlowEditorService,
    MicroSurveyService,
    ScheduledReportService,
    SessionReplayService,
    SlackBotService,
    UniversalExportService,
)

TENANT = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def registry(tmp_path, monkeypatch) -> ServiceRegistry:
    import retention_analytics_core.repository as repo_mod
    import retention_analytics_advanced.customer_intel as ci
    import retention_analytics_advanced.automation as au
    import retention_analytics_ux.service as ux
    for mod in (repo_mod, ci, au, ux):
        monkeypatch.setattr(mod, "data_root", lambda: tmp_path)
    reg = ServiceRegistry()
    SavedReportService(reg).register()
    # Services referenced by flow-editor validation and bot commands
    from retention_analytics_engagement.email.service import EmailService
    from retention_analytics_engagement.sms.service import SmsService
    from retention_analytics_ai.service import PredictiveChurnService
    from retention_analytics_saas_metrics.service import SaasMetricsService
    from retention_analytics_cs_ops.service import AlertService, RenewalHubService
    from retention_analytics_growth.service import SurveyService
    EmailService(reg).register()
    SmsService(reg).register()
    PredictiveChurnService(reg).register()
    SaasMetricsService(reg).register()
    AlertService(reg).register()
    RenewalHubService(reg).register()
    SurveyService(reg).register()
    for cls in (ScheduledReportService, FlowEditorService, CancelFlowAPI, SlackBotService,
                SessionReplayService, MicroSurveyService, UniversalExportService):
        cls(reg).register()
    return reg


@pytest.mark.asyncio
async def test_scheduled_reports(registry: ServiceRegistry) -> None:
    # Create a saved report WITH a schedule
    r = await registry.invoke("ux.reports", "save", {
        "tenant_id": TENANT, "name": "Weekly MRR", "widgets": ["saas"],
        "schedule": {"frequency": "daily", "email_to": "team@co.com"},
    })
    rid = r["report"]["report_id"]
    # No last_run_at -> due immediately
    due = await registry.invoke("reports.scheduler", "due", {"tenant_id": TENANT})
    assert due["due_count"] == 1
    # run_due executes (email send will fail silently in test, but report runs)
    r = await registry.invoke("reports.scheduler", "run_due", {"tenant_id": TENANT})
    assert r["count"] == 1


@pytest.mark.asyncio
async def test_flow_editor_lifecycle(registry: ServiceRegistry) -> None:
    r = await registry.invoke("flows.editor", "create_graph", {
        "tenant_id": TENANT, "name": "My flow", "trigger_event": "client.churn_risk",
        "nodes": [
            {"id": "t", "type": "trigger", "position": {"x": 0, "y": 0}},
            {"id": "s1", "type": "service", "service": "email", "action": "send", "position": {"x": 200, "y": 0}},
        ],
        "edges": [{"from": "t", "to": "s1"}],
    })
    gid = r["graph"]["graph_id"]
    v = await registry.invoke("flows.editor", "validate", {"graph_id": gid})
    assert v["valid"] is True, v["errors"]

    # Invalid: two triggers
    await registry.invoke("flows.editor", "update_graph", {"graph_id": gid, "nodes": [
        {"id": "t", "type": "trigger"}, {"id": "t2", "type": "trigger"}, {"id": "s1", "type": "service", "service": "email", "action": "send"}]})
    v = await registry.invoke("flows.editor", "validate", {"graph_id": gid})
    assert v["valid"] is False

    # Invalid: cycle
    await registry.invoke("flows.editor", "update_graph", {"graph_id": gid, "nodes": [
        {"id": "t", "type": "trigger"}, {"id": "a", "type": "service", "service": "email", "action": "send"}, {"id": "b", "type": "service", "service": "sms", "action": "send"}],
        "edges": [{"from": "t", "to": "a"}, {"from": "a", "to": "b"}, {"from": "b", "to": "a"}]})
    v = await registry.invoke("flows.editor", "validate", {"graph_id": gid})
    assert v["valid"] is False
    assert any("cycle" in e for e in v["errors"])

    # Invalid: unknown service
    await registry.invoke("flows.editor", "update_graph", {"graph_id": gid, "nodes": [
        {"id": "t", "type": "trigger"}, {"id": "s", "type": "service", "service": "nonexistent.svc", "action": "x"}],
        "edges": [{"from": "t", "to": "s"}]})
    v = await registry.invoke("flows.editor", "validate", {"graph_id": gid})
    assert v["valid"] is False
    assert any("unknown service" in e for e in v["errors"])

    # Publish a valid graph
    await registry.invoke("flows.editor", "update_graph", {"graph_id": gid, "nodes": [
        {"id": "t", "type": "trigger"}, {"id": "s", "type": "service", "service": "email", "action": "send"}],
        "edges": [{"from": "t", "to": "s"}]})
    r = await registry.invoke("flows.editor", "publish", {"graph_id": gid})
    assert r["status"] == "published"
    assert len(r["workflow"]["steps"]) == 1


@pytest.mark.asyncio
async def test_cancel_flow_api(registry: ServiceRegistry) -> None:
    r = await registry.invoke("cancel_flow.api", "start", {
        "tenant_id": TENANT, "customer_id": "c1", "subscription_id": "sub-1", "reason": "pricing"})
    sid = r["session"]["session_id"]
    r = await registry.invoke("cancel_flow.api", "offers", {"session_id": sid, "tenant_id": TENANT, "mrr": 500})
    assert "default_options" in r
    assert len(r["default_options"]) == 3
    await registry.invoke("cancel_flow.api", "select", {"session_id": sid, "offer": {"type": "pause"}})
    r = await registry.invoke("cancel_flow.api", "confirm", {"session_id": sid})
    assert r["outcome"] == "pause"


@pytest.mark.asyncio
async def test_slack_bot_commands(registry: ServiceRegistry) -> None:
    r = await registry.invoke("integrations.bot", "handle_command", {"tenant_id": TENANT, "text": "/help"})
    assert "at-risk" in r["response"]
    r = await registry.invoke("integrations.bot", "handle_command", {"tenant_id": TENANT, "text": "/at-risk 0.5"})
    assert "at-risk" in r["response"]
    r = await registry.invoke("integrations.bot", "handle_command", {"tenant_id": TENANT, "text": "/unknown"})
    assert "Unknown" in r["response"]


@pytest.mark.asyncio
async def test_session_replay(registry: ServiceRegistry) -> None:
    for i in range(5):
        await registry.invoke("session.replay", "ingest", {
            "tenant_id": TENANT, "session_id": "sess-1", "customer_id": "c1",
            "type": "click", "target": f"btn-{i}", "ts": f"2026-11-12T10:0{i}:00+00:00"})
    r = await registry.invoke("session.replay", "get_session", {"session_id": "sess-1"})
    assert r["count"] == 5
    assert r["events"][0]["target"] == "btn-0"


@pytest.mark.asyncio
async def test_micro_surveys(registry: ServiceRegistry) -> None:
    r = await registry.invoke("surveys.micro", "create", {
        "tenant_id": TENANT, "trigger_action": "checkout_completed", "question": "How easy was checkout?",
        "type": "ces", "show_after_events": 1})
    sid = r["survey"]["survey_id"]
    # Trigger: no events yet -> nothing
    r = await registry.invoke("surveys.micro", "trigger", {"tenant_id": TENANT, "customer_id": "c1", "action": "checkout_completed"})
    assert r["count"] == 0
    # Log the action event
    await registry.invoke("session.replay", "ingest", {"tenant_id": TENANT, "session_id": "s1", "customer_id": "c1", "type": "custom", "value": "checkout_completed"})
    r = await registry.invoke("surveys.micro", "trigger", {"tenant_id": TENANT, "customer_id": "c1", "action": "checkout_completed"})
    assert r["count"] == 1
    await registry.invoke("surveys.micro", "respond", {"survey_id": sid, "customer_id": "c1", "score": 5})
    r = await registry.invoke("surveys.micro", "results", {"survey_id": sid})
    assert r["responses"] == 1
    assert r["avg_score"] == 5.0


@pytest.mark.asyncio
async def test_universal_export(registry: ServiceRegistry) -> None:
    r = await registry.invoke("export", "datasets", {})
    assert "customers" in r["datasets"]
    # create a goal then export it
    from retention_analytics_advanced.customer_intel import GoalsService
    GoalsService(registry).register()
    await registry.invoke("goals", "create", {"tenant_id": TENANT, "name": "X", "metric": "mrr", "target": 100})
    r = await registry.invoke("export", "export", {"dataset": "goals", "format": "csv"})
    assert r["count"] == 1
    assert "name" in r["csv"]
    r = await registry.invoke("export", "export", {"dataset": "goals", "format": "json"})
    assert r["count"] == 1 and r["data"][0]["name"] == "X"
