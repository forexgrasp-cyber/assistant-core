"""Tests for the ai-assistant wrapper.

The wrapper owns: tenant resolution, capability gating, entitlement
admin routes and the static frontend mounts. Everything it depends on
lives in ``shared-canonical-services``.

Run:  python -m pytest tests -q
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """TestClient that runs the app lifespan (demo tenant entitlements load)."""
    from app.main import app

    with TestClient(app) as c:
        yield c


# ── health / discovery ────────────────────────────────────────────────


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert body["service"] == "ai-assistant"


def test_agents_listed(client):
    r = client.get("/api/v1/agents")
    assert r.status_code == 200
    slugs = {a["slug"] for a in r.json()}
    # The three canonical agent types plus the vertical specs.
    assert {"receptionist", "jarvis", "language-tutor"} <= slugs
    assert "callagent" in slugs  # alias of receptionist


def test_bundles_listed(client):
    r = client.get("/api/v1/bundles")
    assert r.status_code == 200
    bundles = set(r.json())
    assert {"callagent_starter", "tutor_free", "jarvis_personal", "hvac_starter"} <= bundles


# ── entitlement reporting ─────────────────────────────────────────────


def test_combo_tenant_has_all_capabilities(client):
    r = client.get("/api/v1/entitlements/me")
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == "tenant-combo"
    assert body["capability_count"] > 0
    assert len(body["products"]) > 1


def test_vertical_tenant_is_scoped_to_its_bundle(client):
    r = client.get("/api/v1/entitlements/me?tenant=hvac")
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == "tenant-hvac"
    products = {p["id"] for p in body["products"]}
    assert "hvac_starter" in products
    assert "tutor_free" not in products


def test_check_capability_endpoint(client):
    # The tutor's free bundle buys SPEECH (TTS + STT for pronunciation
    # scoring) but not TELEPHONY: inbound/outbound calls are a separate
    # capability that also needs a phone provider.
    r = client.get("/api/v1/entitlements/check/communication.voice.tts?tenant=tutor")
    assert r.status_code == 200
    assert r.json()["enabled"] is True

    r = client.get("/api/v1/entitlements/check/communication.voice?tenant=tutor")
    assert r.json()["enabled"] is False

    # HVAC is a voice receptionist vertical, so it HAS voice — but it has
    # no email provider (that only arrives with HVAC_PRO).
    r = client.get("/api/v1/entitlements/check/communication.voice?tenant=hvac")
    assert r.json()["enabled"] is True

    r = client.get("/api/v1/entitlements/check/integration.email_provider?tenant=hvac")
    assert r.json()["enabled"] is False

    r = client.get("/api/v1/entitlements/check/vertical.tutor?tenant=hvac")
    assert r.json()["enabled"] is False


def test_check_unknown_capability_is_404(client):
    r = client.get("/api/v1/entitlements/check/not.a.capability")
    assert r.status_code == 404


# ── capability gating ─────────────────────────────────────────────────


def test_tutor_route_blocked_for_hvac_tenant(client):
    r = client.get("/api/v1/tutor/curriculum?tenant=hvac")
    assert r.status_code == 403
    detail = r.json()["detail"]
    assert detail["capability"] == "vertical.tutor"
    assert detail["tenant"] == "tenant-hvac"


def test_tutor_route_allowed_for_tutor_tenant(client):
    r = client.get("/api/v1/tutor/curriculum?tenant=tutor")
    assert r.status_code == 200
    assert r.json()["tenant_id"] == "tenant-tutor"


def test_tutor_route_allowed_for_combo_tenant(client):
    r = client.get("/api/v1/tutor/curriculum")
    assert r.status_code == 200
    assert r.json()["tenant_id"] == "tenant-combo"


def test_jarvis_email_blocked_for_hvac_tenant(client):
    r = client.get("/api/v1/jarvis/email?tenant=hvac")
    assert r.status_code == 403
    assert r.json()["detail"]["capability"] == "integration.email_provider"


def test_voice_route_allowed_for_callagent_tenant(client):
    r = client.get("/api/v1/callagent/calls?tenant=callagent")
    assert r.status_code == 200
    assert r.json()["tenant_id"] == "tenant-callagent"


# ── admin grant / revoke ──────────────────────────────────────────────


def test_grant_then_revoke_roundtrip(client):
    grant = client.post(
        "/api/v1/admin/entitlements/grant"
        "?tenant_id=tenant-hvac&capability=integration.email_provider"
    )
    assert grant.status_code == 200
    assert grant.json()["success"] is True

    assert client.get("/api/v1/jarvis/email?tenant=hvac").status_code == 200

    revoke = client.post(
        "/api/v1/admin/entitlements/revoke"
        "?tenant_id=tenant-hvac&capability=integration.email_provider"
    )
    assert revoke.status_code == 200
    assert revoke.json()["success"] is True

    assert client.get("/api/v1/jarvis/email?tenant=hvac").status_code == 403


def test_grant_unknown_capability_is_400(client):
    r = client.post(
        "/api/v1/admin/entitlements/grant?tenant_id=tenant-hvac&capability=nope.nope"
    )
    assert r.status_code == 400


# ── tenant resolution ─────────────────────────────────────────────────


def test_tenant_from_header(client):
    r = client.get("/api/v1/entitlements/me", headers={"X-Tenant-ID": "tenant-tutor"})
    assert r.json()["tenant_id"] == "tenant-tutor"


def test_tenant_from_query_param(client):
    r = client.get("/api/v1/entitlements/me?tenant=jarvis")
    assert r.json()["tenant_id"] == "tenant-jarvis"


def test_tenant_from_subdomain(client):
    r = client.get("/api/v1/entitlements/me", headers={"Host": "acme.ai.snapford.com"})
    assert r.json()["tenant_id"] == "tenant-acme"


def test_reserved_subdomain_falls_back_to_default(client):
    r = client.get("/api/v1/entitlements/me", headers={"Host": "app.ai.snapford.com"})
    assert r.json()["tenant_id"] == "tenant-combo"


# ── frontend ──────────────────────────────────────────────────────────


def test_landing_page(client):
    r = client.get("/landing")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert len(r.content) > 1000


def test_root_serves_landing(client):
    assert client.get("/").status_code == 200


def test_dashboard(client):
    r = client.get("/dashboard")
    assert r.status_code == 200
    assert len(r.content) > 1000


def test_static_assets_mounted(client):
    r = client.get("/static/landing_page.html")
    assert r.status_code == 200
