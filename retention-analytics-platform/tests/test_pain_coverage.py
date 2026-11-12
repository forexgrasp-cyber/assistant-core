"""Tests for the pain-point catalog and pain-point workflows."""

from __future__ import annotations

import pytest

from apps.api.workflows_seed import build_workflows, workflow_event_bindings
from retention_analytics_advanced.pains import PAIN_CATALOG, pain_catalog

PAIN_WORKFLOWS = [
    "login-lockout", "error-apology", "support-ack", "support-resolved-followup",
    "price-change-notice", "invoice-delivery", "quota-warning", "never-logged-in",
    "stuck-onboarding", "back-in-stock", "price-drop-alert", "security-alert", "invite-activation",
]


def test_pain_catalog_covers_all_workflows() -> None:
    wf_ids = {w.id for w in build_workflows()}
    catalog = pain_catalog()
    assert catalog["total"] >= 24
    # every pain maps to at least one workflow that exists
    uncovered = []
    for pid, p in catalog["pains"].items():
        if not any(w in wf_ids for w in p["workflows"]):
            uncovered.append(pid)
    assert not uncovered, f"pains without a registered workflow: {uncovered}"


def test_pain_workflows_exist_and_bound() -> None:
    wf_ids = {w.id for w in build_workflows()}
    bindings = workflow_event_bindings()
    for wid in PAIN_WORKFLOWS:
        assert wid in wf_ids, f"missing workflow {wid}"
    # every pain workflow has an event binding
    bound_events = set(bindings.keys())
    pain_events = {"auth.login_failed", "app.error_occurred", "support.ticket_opened",
                   "support.ticket_resolved", "billing.price_changed", "billing.invoice_created",
                   "usage.quota_near_limit", "onboarding.no_login", "onboarding.stuck",
                   "inventory.back_in_stock", "pricing.price_dropped", "security.suspicious_login",
                   "team.invite_sent"}
    missing = pain_events - bound_events
    assert not missing, f"pain events without bindings: {missing}"


def test_pain_categories_complete() -> None:
    catalog = pain_catalog()
    for cat in catalog["categories"]:
        assert cat in catalog["by_category"]
        assert len(catalog["by_category"][cat]) > 0, f"category {cat} is empty"


def test_each_pain_has_customer_gets() -> None:
    for pid, p in PAIN_CATALOG.items():
        assert p.get("customer_gets"), f"pain {pid} has no customer_gets"
        assert p.get("event"), f"pain {pid} has no event"
        assert p.get("workflows"), f"pain {pid} has no workflows"
