"""Tests for the segment push-back (activation loop to Klaviyo & friends)."""

from __future__ import annotations

import pytest

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced_processing.segment_push import PUSH_TARGETS, SegmentPushService
from retention_analytics_advanced_processing.analysis import AdvancedSegmentation
from retention_analytics_advanced.customer_intel import Customer360Service

TENANT = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def registry(tmp_path, monkeypatch) -> ServiceRegistry:
    import retention_analytics_core.repository as repo_mod
    import retention_analytics_advanced.customer_intel as ci
    import retention_analytics_advanced_processing.segment_push as sp
    for mod in (repo_mod, ci, sp):
        monkeypatch.setattr(mod, "data_root", lambda: tmp_path, raising=False)
    reg = ServiceRegistry()
    Customer360Service(reg).register()
    AdvancedSegmentation(reg).register()
    SegmentPushService(reg).register()
    return reg


@pytest.mark.asyncio
async def test_push_targets(registry: ServiceRegistry) -> None:
    r = await registry.invoke("connectors.segment_push", "targets", {})
    names = {t["platform"] for t in r["targets"]}
    for expected in ("klaviyo", "attentive", "omnisend", "sendlane", "postscript"):
        assert expected in names
    assert len(r["targets"]) == len(PUSH_TARGETS)


@pytest.mark.asyncio
async def test_push_requires_credentials(registry: ServiceRegistry, monkeypatch) -> None:
    for k in list(__import__("os").environ):
        if k.startswith(("KLAVIYO_", "ATTENTIVE_", "OMNISEND_", "SENDLANE_", "POSTSCRIPT_")):
            monkeypatch.delenv(k, raising=False)
    r = await registry.invoke("connectors.segment_push", "push", {"platform": "klaviyo", "tenant_id": TENANT})
    assert r["status"] == "no_credentials"
    assert "KLAVIYO_PRIVATE_API_KEY" in r["missing_keys"]


@pytest.mark.asyncio
async def test_push_unknown_platform(registry: ServiceRegistry) -> None:
    r = await registry.invoke("connectors.segment_push", "push", {"platform": "nope"})
    assert r["status"] == "unknown_platform"


@pytest.mark.asyncio
async def test_push_resolves_segment_members(registry: ServiceRegistry, monkeypatch) -> None:
    """With a key configured, the push resolves the segment and calls the platform API."""
    monkeypatch.setenv("KLAVIYO_PRIVATE_API_KEY", "pk_test_123")
    await registry.invoke("customers.360", "upsert_profile", {
        "tenant_id": TENANT, "id": "c1", "name": "Jane", "email": "jane@x.com",
        "plan": "growth", "mrr": 100, "health_score": 30})

    calls = []

    class FakeClient:
        async def post(self, url, headers=None, json=None):
            calls.append((url, json))
            if "lists" in url:
                return {"data": {"id": "list-123"}}
            return {"data": {"id": "job-456"}}

    import shared.http_client.resilient_http_client as rhc
    monkeypatch.setattr(rhc, "ResilientHTTPClient", lambda *a, **k: FakeClient())

    r = await registry.invoke("connectors.segment_push", "push", {
        "platform": "klaviyo", "tenant_id": TENANT,
        "criteria": {"health_tier": ["critical", "at_risk", "watch"]}, "name": "At-risk"})
    assert r["status"] == "ok"
    push = r["push"]
    assert push["members"] == 1
    assert push["result"]["list_id"] == "list-123"
    assert push["result"]["profiles_pushed"] == 1
    # the profile payload carries the computed fields
    assert calls, "no API call made"
    assert calls[0][0].endswith("/lists/")

    hist = await registry.invoke("connectors.segment_push", "history", {"tenant_id": TENANT})
    assert hist["count"] == 1
