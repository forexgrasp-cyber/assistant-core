"""Snapford platform conformance surfaces for the retention product.

Implements the four endpoints the shared design-conformance auditor checks
(shared/webui/design_conformance.py):
  - GET /api/seo/manifest         PWA/web-app manifest
  - GET /api/seo/style/tokens.css design-token stylesheet (linked from HTML)
  - GET /api/i18n/languages       20 platform locales with text directions
  - GET /api/me                   product identity surface

Locales come from shared.i18n (PLATFORM_LOCALES / locale_info / dir_for) so
the product speaks exactly the platform's locale set.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import structlog

from retention_analytics_core.service_registry import ServiceRegistry

logger = structlog.get_logger(__name__)

PRODUCT_ID = "retention"
PRODUCT_NAME = "Snapford Retention"
PRODUCT_SUBDOMAIN = "retention"
APEX_DOMAIN = "snapford.com"


class PlatformSurfaceService:
    """Serves the platform-required identity, locale, manifest and token surfaces."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def register(self) -> None:
        reg = self.registry.register("platform.surfaces", version="1.0.0", metadata={"domain": "platform", "type": "seo"})
        reg.actions["manifest"] = self._manifest
        reg.actions["tokens_css"] = self._tokens
        reg.actions["languages"] = self._languages
        reg.actions["me"] = self._me

    # ---------------------------------------------------------------- i18n
    def _locale_rows(self) -> list[dict[str, Any]]:
        try:
            from shared.i18n.locales import PLATFORM_LOCALES, dir_for, locale_info
        except Exception:
            return [{"code": "en", "name": "English", "native": "English", "dir": "ltr"}]
        rows = []
        for code in PLATFORM_LOCALES:
            try:
                info = locale_info(code)
                native = getattr(info, "native", code)
                name = getattr(info, "name", code)
            except Exception:
                native = name = code
            try:
                d = dir_for(code)
            except Exception:
                d = "ltr"
            rows.append({"code": code, "name": name, "native": native, "dir": d})
        return rows

    async def _languages(self, p: dict[str, Any]) -> dict[str, Any]:
        rows = self._locale_rows()
        return {
            "status": "ok",
            "count": len(rows),
            "default": "en",
            "dir": "ltr",
            "languages": rows,
            "locales": rows,
        }

    # ---------------------------------------------------------------- seo
    async def _manifest(self, p: dict[str, Any]) -> dict[str, Any]:
        """PWA/web-app manifest.

        URLs are RELATIVE so they resolve against the origin that serves the
        manifest (the portal in dev, the apex in prod). Chrome ignores
        cross-origin manifest URLs, so absolute URLs break the install prompt.
        """
        return {
            "name": PRODUCT_NAME,
            "short_name": "Snapford Retention",
            "description": "Retention analytics: campaigns, flows, churn prediction, dunning and NPS.",
            "id": "/",
            "start_url": "/",
            "scope": "/",
            "display": "standalone",
            "orientation": "portrait-primary",
            "background_color": "#0f172a",
            "theme_color": "#4f46e5",
            "lang": "en",
            "dir": "ltr",
            "categories": ["business", "productivity", "analytics"],
            "icons": [
                {"src": "/brand/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
                {"src": "/brand/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
            ],
            "shortcuts": [
                {"name": "Campaigns", "url": "/campaigns"},
                {"name": "Customers", "url": "/customers"},
                {"name": "Analytics", "url": "/analytics"},
            ],
        }

    async def _tokens(self, p: dict[str, Any]) -> str:
        """Design-token stylesheet. Injected into the portal <head> so both
        surfaces share one token source."""
        return """/* Snapford design tokens — retention platform */
:root {
  --sf-bg: #f8fafc;
  --sf-surface: #ffffff;
  --sf-surface-2: #f1f5f9;
  --sf-border: #e2e8f0;
  --sf-text: #0f172a;
  --sf-text-2: #64748b;
  --sf-accent: #4f46e5;
  --sf-accent-soft: #eef2ff;
  --sf-success: #059669;
  --sf-warning: #d97706;
  --sf-danger: #dc2626;
  --sf-radius: 10px;
  --sf-radius-sm: 6px;
  --sf-shadow: 0 1px 2px rgba(15, 23, 42, 0.06), 0 1px 3px rgba(15, 23, 42, 0.1);
  --sf-font: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  --sf-mono: ui-monospace, SFMono-Regular, Menlo, monospace;
  --sf-space-1: 4px;
  --sf-space-2: 8px;
  --sf-space-3: 12px;
  --sf-space-4: 16px;
  --sf-space-6: 24px;
  --sf-space-8: 32px;
}
html.dark {
  --sf-bg: #0b1220;
  --sf-surface: #131c2e;
  --sf-surface-2: #1b2740;
  --sf-border: #243049;
  --sf-text: #e2e8f0;
  --sf-text-2: #94a3b8;
  --sf-accent: #818cf8;
  --sf-accent-soft: #312e81;
}
"""

    # ---------------------------------------------------------------- identity
    async def _me(self, p: dict[str, Any]) -> dict[str, Any]:
        """Product identity surface (same contract as the product /api/*/me)."""
        return {
            "product": PRODUCT_ID,
            "name": PRODUCT_NAME,
            "subdomain": PRODUCT_SUBDOMAIN,
            "apex": APEX_DOMAIN,
            "url": f"https://{PRODUCT_SUBDOMAIN}.{APEX_DOMAIN}",
            "status": "live",
            "repo": "forexgrasp-cyber/retention-analytics-platform",
            "pricing_path": f"/products/{PRODUCT_ID}",
            "services": len(self.registry.list_services()),
            "workflows": len([d for d in self.registry.list_definitions()]) if hasattr(self.registry, "list_definitions") else 0,
            "locales": len(self._locale_rows()),
            "generated_at": datetime.now(UTC).isoformat(),
        }


__all__ = ["PlatformSurfaceService", "PRODUCT_ID", "PRODUCT_NAME"]
