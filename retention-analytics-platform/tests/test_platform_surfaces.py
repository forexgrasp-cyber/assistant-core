"""Tests for the Snapford platform conformance surfaces."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

HEADERS = {"Authorization": "Bearer dev-token"}


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_api_me_identity(client: TestClient) -> None:
    r = client.get("/api/me", headers=HEADERS)
    assert r.status_code == 200
    d = r.json()
    assert d["product"] == "retention"
    assert d["subdomain"] == "retention"
    assert d["apex"] == "snapford.com"
    assert d["url"] == "https://retention.snapford.com"
    assert d["status"] == "live"
    assert d["pricing_path"] == "/products/retention"
    assert d["services"] >= 90


def test_i18n_languages_surface(client: TestClient) -> None:
    r = client.get("/api/i18n/languages", headers=HEADERS)
    assert r.status_code == 200
    d = r.json()
    # The shared conformance gate requires >= 20 locales with text directions.
    assert d["count"] >= 20
    assert d["default"] == "en"
    codes = {l["code"] for l in d["languages"]}
    for expected in ("en", "de", "es", "fr", "zh", "ar", "fa", "ru", "ja"):
        assert expected in codes
    rtl = {l["code"] for l in d["languages"] if l["dir"] == "rtl"}
    assert "ar" in rtl and "fa" in rtl
    for lang in d["languages"]:
        assert lang["dir"] in ("ltr", "rtl")
        assert lang["native"]


def test_seo_manifest(client: TestClient) -> None:
    r = client.get("/api/seo/manifest", headers=HEADERS)
    assert r.status_code == 200
    d = r.json()
    assert d["name"]
    assert d["display"] in ("standalone", "fullscreen", "minimal-ui")
    assert d["icons"]
    assert d["theme_color"].startswith("#")
    # Chrome rejects cross-origin manifest URLs, so the manifest must use
    # same-origin relative paths.
    assert d["start_url"] == "/"
    assert d["id"] == "/"
    assert d["scope"] == "/"
    for sc in d["shortcuts"]:
        assert sc["url"].startswith("/")
        assert not sc["url"].startswith("http")
    for icon in d["icons"]:
        assert icon["src"].startswith("/")


def test_tokens_css(client: TestClient) -> None:
    r = client.get("/api/seo/style/tokens.css", headers=HEADERS)
    assert r.status_code == 200
    assert "text/css" in r.headers["content-type"]
    body = r.text
    assert ":root {" in body
    assert "--sf-accent:" in body
    assert "html.dark" in body


def test_contract_surfaces_all_200(client: TestClient) -> None:
    """The six surfaces the shared design-conformance auditor fetches."""
    for path in ("/robots.txt", "/sitemap.xml", "/api/seo/manifest",
                 "/api/seo/style/tokens.css", "/api/i18n/languages", "/api/me"):
        r = client.get(path, headers=HEADERS)
        assert r.status_code == 200, f"{path} -> {r.status_code}"
    robots = client.get("/robots.txt", headers=HEADERS).text
    assert "User-agent" in robots
    sitemap = client.get("/sitemap.xml", headers=HEADERS).text
    assert "<loc>" in sitemap
