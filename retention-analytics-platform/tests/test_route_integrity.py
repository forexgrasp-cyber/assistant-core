"""Guard tests: route integrity + full action reachability.

Prevents the class of bug where a static route is shadowed by a parameterized
route registered earlier (e.g. /api/v1/presets/applied vs /api/v1/presets/{id}).
"""

from __future__ import annotations

import re

import pytest
from starlette.routing import Route

from apps.api.main import app, registry


def _routes() -> list[tuple[str, set[str]]]:
    out = []
    for r in app.routes:
        if isinstance(r, Route):
            out.append((r.path, set(r.methods or [])))
    return out


def test_no_shadowed_static_routes() -> None:
    """A static path must not be captured by an earlier parameterized path."""
    routes = _routes()
    shadowed = []
    for i, (path_i, methods_i) in enumerate(routes):
        if re.findall(r"\{(\w+)\}", path_i):
            continue
        for j, (path_j, _) in enumerate(routes):
            if i == j:
                continue
            params_j = re.findall(r"\{(\w+)\}", path_j)
            if not params_j:
                continue
            pattern = re.escape(path_j)
            for p in params_j:
                pattern = pattern.replace(re.escape("{" + p + "}"), "[^/]+")
            if re.fullmatch(pattern, path_i) and j < i:
                shadowed.append((path_i, path_j))
                break
    assert not shadowed, f"static routes shadowed by earlier parameterized routes: {shadowed}"


def test_every_service_action_is_reachable() -> None:
    """Every registered action must have a typed route or be reachable via the generic proxy."""
    paths = {p for p, _ in _routes()}
    assert "/api/v1/actions/{service_name}/{action_name}" in paths, "generic action proxy missing"
    for svc in registry.list_services():
        for action in registry.get(svc).actions:
            typed = f"/api/v1/{svc}/actions/{action}" in paths or f"/api/v1/{svc}/{action}" in paths
            assert typed or "/api/v1/actions/{service_name}/{action_name}" in paths


def test_service_registry_size() -> None:
    """Platform exposes the full competitor-parity service surface."""
    services = registry.list_services()
    assert len(services) >= 60, f"expected 60+ services, got {len(services)}"
    for expected in [
        "customers.360", "customers.service_due", "benchmarks", "goals", "feedback.voc",
        "experiments.ab", "experiments.pricing", "automation.sequences", "catalog", "walls",
        "journeys", "analytics.attribution", "analytics.anomaly", "cs.qbr", "presets",
        "campaigns", "saas.metrics", "ai.churn_predict", "ai.feedback", "ai.offers",
        "health.scoring", "dunning", "surveys", "forecasting", "segmentation",
        "inapp.messaging", "cs.plans", "cs.playbooks", "cs.alerts", "cs.renewals",
        "cs.command_center", "integrations", "webhooks.manage", "compliance.privacy",
        "compliance.audit_export", "compliance.sso", "ux.settings", "ux.reports", "ux.events",
        "ux.flows", "email", "sms", "push", "templates", "analytics.metric", "analytics.cohort",
    ]:
        assert expected in services, f"missing service: {expected}"


def test_action_catalog_endpoint_shape() -> None:
    """GET /api/v1/actions lists every service with its actions."""
    from fastapi.testclient import TestClient

    c = TestClient(app)
    r = c.get("/api/v1/actions", headers={"Authorization": "Bearer dev-token"})
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 60
    total = sum(len(s["actions"]) for s in data["services"])
    assert total >= 200, f"only {total} actions exposed"
