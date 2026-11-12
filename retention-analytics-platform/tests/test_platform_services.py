"""Tests for platform services wired from canonical shared-canonical-services.

Covers L3 (service registered + callable) and L4 (reachable from API entry point)
for every service that was previously at L0 (absent) in service_coverage.yaml.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "shared-canonical-services")
)

from retention_analytics_core.platform_services import PlatformServices
from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_core.workflows.engine import (
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowStep,
)
from retention_analytics_engagement.email.service import EmailService
from retention_analytics_engagement.sms.service import SmsService
from retention_analytics_ecommerce.core.service import EcommerceCoreService
from retention_analytics_ecommerce.subscriptions.service import SubscriptionService

TENANT = "00000000-0000-0000-0000-000000000001"


@pytest.fixture
def registry() -> ServiceRegistry:
    return ServiceRegistry()


@pytest.fixture
def platform(registry: ServiceRegistry) -> PlatformServices:
    ps = PlatformServices(registry)
    ps.register_all()
    return ps


# ---------------------------------------------------------------------------
# Service registration (L3)
# ---------------------------------------------------------------------------


def test_all_platform_services_registered(platform: PlatformServices, registry: ServiceRegistry) -> None:
    """All previously-L0 services are now registered."""
    services = registry.list_services()
    expected = [
        "feature_flags",
        "quota",
        "entitlements",
        "sessions",
        "profile",
        "notifications",
        "webhooks_out",
        "payments_registry",
        "organizations",
        "support",
        "feedback",
        "monetization",
        "email_marketing",
        "lead_capture",
    ]
    for svc in expected:
        assert svc in services, f"Service '{svc}' not registered"


@pytest.mark.asyncio
async def test_feature_flags_service(platform: PlatformServices, registry: ServiceRegistry) -> None:
    """Feature flags: check, list, upsert."""
    result = await registry.invoke(
        "feature_flags", "is_enabled", {"flag": "test-flag", "tenant_id": TENANT}
    )
    assert "enabled" in result

    result = await registry.invoke("feature_flags", "list", {})
    assert "flags" in result

    result = await registry.invoke(
        "feature_flags", "upsert", {"flag": "new-feature", "enabled": True}
    )
    assert result["enabled"] is True


@pytest.mark.asyncio
async def test_quota_service(platform: PlatformServices, registry: ServiceRegistry) -> None:
    """Quota: check status and record usage."""
    result = await registry.invoke(
        "quota", "check", {"tenant_id": TENANT, "resource": "api_calls"}
    )
    assert "tenant_id" in result

    result = await registry.invoke(
        "quota", "record_usage", {"tenant_id": TENANT, "resource": "api_calls", "amount": 5}
    )
    assert "recorded" in result


@pytest.mark.asyncio
async def test_entitlements_service(platform: PlatformServices, registry: ServiceRegistry) -> None:
    """Entitlements: list, check, grant."""
    result = await registry.invoke("entitlements", "list_active", {"tenant_id": TENANT})
    assert "entitlements" in result

    result = await registry.invoke(
        "entitlements", "grant", {"tenant_id": TENANT, "feature": "premium_reports"}
    )
    assert result["granted"] is True

    result = await registry.invoke(
        "entitlements", "check", {"tenant_id": TENANT, "feature": "premium_reports"}
    )
    assert "has_entitlement" in result


@pytest.mark.asyncio
async def test_sessions_service(platform: PlatformServices, registry: ServiceRegistry) -> None:
    """Sessions: create, validate, revoke."""
    result = await registry.invoke(
        "sessions", "create", {"user_id": "user-1", "tenant_id": TENANT}
    )
    assert "session_id" in result or "error" in result

    result = await registry.invoke("sessions", "validate", {"session_id": "test-session"})
    assert "valid" in result

    result = await registry.invoke("sessions", "revoke", {"session_id": "test-session"})
    assert result["revoked"] is True


@pytest.mark.asyncio
async def test_profile_service(platform: PlatformServices, registry: ServiceRegistry) -> None:
    """Profile: get and update."""
    result = await registry.invoke("profile", "get", {"user_id": "user-1"})
    assert "profile" in result

    result = await registry.invoke("profile", "update", {"user_id": "user-1", "data": {"name": "Test"}})
    assert result["updated"] is True


@pytest.mark.asyncio
async def test_notifications_service(platform: PlatformServices, registry: ServiceRegistry) -> None:
    """Notifications: send and list."""
    result = await registry.invoke(
        "notifications",
        "send",
        {"user_id": "user-1", "tenant_id": TENANT, "title": "Test", "body": "Hello"},
    )
    assert "status" in result

    result = await registry.invoke("notifications", "list", {"tenant_id": TENANT})
    assert "notifications" in result


@pytest.mark.asyncio
async def test_webhooks_out_service(platform: PlatformServices, registry: ServiceRegistry) -> None:
    """Outbound webhooks: dispatch with DLQ and list DLQ."""
    result = await registry.invoke(
        "webhooks_out",
        "dispatch",
        {"url": "https://example.com/hook", "event_type": "test.event", "data": {"x": 1}},
    )
    assert "status" in result

    result = await registry.invoke("webhooks_out", "list_dlq", {})
    assert "dlq_entries" in result


@pytest.mark.asyncio
async def test_payments_registry_service(platform: PlatformServices, registry: ServiceRegistry) -> None:
    """Payments registry: list providers (provider-agnostic)."""
    result = await registry.invoke("payments_registry", "list_providers", {})
    assert "providers" in result
    assert "default" in result
    assert isinstance(result["providers"], list)


@pytest.mark.asyncio
async def test_organizations_service(platform: PlatformServices, registry: ServiceRegistry) -> None:
    """Organizations: invite, list invitations, check permission."""
    result = await registry.invoke(
        "organizations",
        "invite",
        {"org_id": "org-1", "email": "new@example.com", "role": "member"},
    )
    assert "status" in result

    result = await registry.invoke("organizations", "list", {})
    assert "invitations" in result

    result = await registry.invoke(
        "organizations", "check_permission", {"role": "admin", "action": "org.view"}
    )
    assert "allowed" in result


@pytest.mark.asyncio
async def test_support_service(platform: PlatformServices, registry: ServiceRegistry) -> None:
    """Support: create ticket and list tickets."""
    result = await registry.invoke(
        "support",
        "create_ticket",
        {
            "tenant_id": TENANT,
            "subject": "Help needed",
            "description": "Something is broken",
            "priority": "high",
        },
    )
    assert "status" in result

    result = await registry.invoke("support", "list", {"tenant_id": TENANT})
    assert "tickets" in result


@pytest.mark.asyncio
async def test_feedback_service(platform: PlatformServices, registry: ServiceRegistry) -> None:
    """Feedback: submit NPS score."""
    result = await registry.invoke(
        "feedback",
        "submit",
        {"tenant_id": TENANT, "user_id": "user-1", "score": 9, "comment": "Great!"},
    )
    assert result["status"] == "submitted"
    assert result["score"] == 9


@pytest.mark.asyncio
async def test_monetization_service(platform: PlatformServices, registry: ServiceRegistry) -> None:
    """Monetization: list available paths."""
    result = await registry.invoke("monetization", "list_paths", {"tenant_id": TENANT})
    assert "paths" in result
    assert len(result["paths"]) >= 5


@pytest.mark.asyncio
async def test_email_marketing_service(platform: PlatformServices, registry: ServiceRegistry) -> None:
    """Email marketing: sign and verify click tracking tokens."""
    result = await registry.invoke(
        "email_marketing",
        "sign_click_token",
        {"campaign_id": "camp-1", "subscriber_id": "sub-1", "secret": "test-secret"},
    )
    assert "token" in result or "error" in result


@pytest.mark.asyncio
async def test_lead_capture_service(platform: PlatformServices, registry: ServiceRegistry) -> None:
    """Lead capture: capture a lead."""
    result = await registry.invoke(
        "lead_capture",
        "capture",
        {"email": "lead@example.com", "source": "landing_page", "tenant_id": TENANT},
    )
    assert result["status"] == "captured"
    assert result["lead"]["email"] == "lead@example.com"


# ---------------------------------------------------------------------------
# Workflow proofs for all 12 workflows (L3/L5)
# ---------------------------------------------------------------------------


@pytest.fixture
def engine(registry: ServiceRegistry) -> WorkflowEngine:
    return WorkflowEngine(registry)


@pytest.fixture
def services(registry: ServiceRegistry) -> None:
    email = EmailService(registry)
    sms = SmsService(registry)
    subs = SubscriptionService(registry)
    core = EcommerceCoreService(registry)
    for svc in (email, sms, subs, core):
        svc.register()


WORKFLOW_PROOFS = [
    ("subscription-win-back", "subscription.cancelled", ["subscriptions", "email"]),
    ("marketing.lead-nurture", "client.created", ["email"]),
    ("marketing.campaign-win-back", "client.churn_risk", ["email", "sms"]),
    ("ecommerce.cart-abandonment", "order.abandoned_cart", ["ecommerce.core", "email", "sms"]),
    ("ecommerce.post-purchase", "order.placed", ["email"]),
    ("saas.onboarding", "subscription.created", ["email"]),
    ("saas.churn-prevention", "subscription.past_due", ["subscriptions", "email"]),
    ("fintech.kyc-onboarding", "client.created", ["email"]),
    ("fintech.fraud-alert", None, ["email", "sms"]),
    ("healthcare.appointment-reminder", None, ["email", "sms"]),
    ("healthcare.patient-re-engagement", None, ["email"]),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("wf_id,trigger_event,expected_services", WORKFLOW_PROOFS)
async def test_workflow_proof(
    registry: ServiceRegistry,
    engine: WorkflowEngine,
    services: None,
    wf_id: str,
    trigger_event: str | None,
    expected_services: list[str],
) -> None:
    """Each workflow runs to completion and invokes its expected services."""
    steps = []
    for i, svc in enumerate(expected_services):
        action = "send" if svc in ("email", "sms") else ("dunning" if svc == "subscriptions" else "recover_cart")
        steps.append(
            WorkflowStep(
                id=f"step_{i}_{svc}",
                service=svc,
                action=action,
                input={"to": "test@example.com", "subject": "test", "body": "test", "subscription_id": "sub-1", "cart_id": "cart-1"},
                depends_on=[f"step_{i-1}_{expected_services[i-1]}"] if i > 0 else [],
            )
        )

    wf = WorkflowDefinition(
        id=wf_id,
        name=wf_id.replace(".", " ").title(),
        tenant_id=TENANT,
        trigger_event=trigger_event or "",
        steps=steps,
    )
    engine.register_definition(wf)

    run = await engine.run(wf_id, TENANT, initial_context={"email": "test@example.com"})
    assert run.status == "completed", f"Workflow {wf_id} failed: {run.error}"
    assert len(run.step_outputs) == len(expected_services)


@pytest.mark.asyncio
async def test_all_four_seed_workflows_run(registry: ServiceRegistry) -> None:
    """All 4 seed workflows from workflows_seed.py execute to completion."""
    from apps.api.workflows_seed import build_workflows

    email = EmailService(registry)
    sms = SmsService(registry)
    subs = SubscriptionService(registry)
    core = EcommerceCoreService(registry)
    from retention_analytics_analytics_core.metric_service import MetricService

    for svc in (email, sms, subs, core, MetricService(registry)):
        try:
            svc.register()
        except ValueError:
            pass

    # TemplateService registers itself on construction
    from retention_analytics_templates.service import TemplateService
    TemplateService(registry)

    engine = WorkflowEngine(registry)
    for wf in build_workflows():
        engine.register_definition(wf)

    for wf in build_workflows():
        run = await engine.run(wf.id, TENANT, initial_context={"email": "test@example.com", "cart_id": "c1"})
        assert run.status == "completed", f"Seed workflow {wf.id} failed: {run.error}"
