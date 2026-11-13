"""Guards for the portal asset/manifest bugs (fixed 2026-11-13).

1. anim.js is generated as inline <script> blocks; loading it via <script src>
   made the browser parse tags as JS -> "Unexpected token '<'". AnimBoot now
   strips the wrappers before injecting.
2. The manifest must use same-origin relative URLs or Chrome ignores them.
3. The manifest's icon/shortcut targets must actually exist.
"""

from __future__ import annotations

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[1]
PORTAL = ROOT / "apps" / "web-customer"


def test_anim_boot_strips_script_wrappers() -> None:
    """AnimBoot must strip <script> tags from anim.js before injecting it."""
    src = (PORTAL / "components" / "AnimBoot.tsx").read_text(encoding="utf-8")
    assert "replace(/<\\/?script" in src or "replace(/<" in src, "anim.js is not stripped"
    assert "load(\"/anim/anim.js\")" not in src, "anim.js must not be loaded via <script src>"


def test_anim_js_strips_to_valid_js() -> None:
    raw = (PORTAL / "public" / "anim" / "anim.js").read_text(encoding="utf-8", errors="replace")
    js = re.sub(r"</?script[^>]*>", "", raw, flags=re.I)
    assert "<script" not in js.lower()
    assert js.count("{") == js.count("}"), "stripped anim.js has unbalanced braces"
    assert js.strip(), "anim.js is empty after stripping"


def test_manifest_icons_exist() -> None:
    brand = PORTAL / "public" / "brand"
    for name in ("icon-192.png", "icon-512.png"):
        path = brand / name
        assert path.exists(), f"manifest icon missing: {path}"
        assert path.stat().st_size > 100


def test_manifest_shortcut_targets_are_portal_pages() -> None:
    app = PORTAL / "app"
    for page in ("campaigns", "customers", "analytics"):
        assert (app / page / "page.tsx").exists(), f"manifest shortcut target missing: /{page}"


def test_renewal_risk_list_endpoint_exists() -> None:
    """GET /api/v1/renewals/risk is called by the Success Ops page."""
    from fastapi.testclient import TestClient
    from apps.api.main import app

    c = TestClient(app)
    r = c.get("/api/v1/renewals/risk", headers={"Authorization": "Bearer dev-token"})
    assert r.status_code == 200
    assert "renewals" in r.json()
