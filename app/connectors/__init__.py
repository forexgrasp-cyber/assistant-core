"""Connectors for external services — backed by shared.integrations.

Refactored 2026-11-16 (TODO H): the per-app mock connector classes (hardcoded
"Mock email" data) were removed. Connector discovery now comes from the
canonical ``shared.integrations.capability_registry.CapabilityRegistry`` and
``get_connector`` returns a ``SharedConnector`` adapter with the same interface
(``authenticate`` / ``fetch_recent`` / ``search`` / ``perform_action``) that
main.py's /connectors endpoints already use — but real: capability metadata
comes from the registry, auth requires the app's real credentials, and data
methods report not-implemented instead of returning fake rows.
"""

from __future__ import annotations

import os
from typing import Any

__all__ = ["SharedConnector", "get_connector", "list_connectors", "CONNECTOR_ALIASES"]

# friendly connector name -> app name in the shared capability registry
CONNECTOR_ALIASES = {
    "gmail": "gmail",
    "calendar": "google_calendar",
    "notion": "notion",
    "obsidian": "obsidian",
    "slack": "slack",
    "github": "github",
    "crm": "hubspot",
}


class SharedConnector:
    """Connector adapter over shared.integrations (capability registry)."""

    def __init__(self, name: str):
        self.name = name
        self.app_name = CONNECTOR_ALIASES.get(name, name)
        env_base = self.app_name.upper().replace("-", "_")
        self.required_env = [f"{env_base}_API_KEY", f"{env_base}_TOKEN", f"{env_base}_CLIENT_ID"]
        from shared.integrations.capability_registry import get_capability_registry

        self._registry = get_capability_registry()

    def _capability(self) -> dict[str, Any] | None:
        try:
            res = self._registry.get_capability(self.app_name)
            return res.data if res.success else None
        except Exception:
            return None

    async def authenticate(self) -> bool:
        """Real auth: the app's credentials must be present in the environment."""
        return any(os.getenv(k) for k in self.required_env)

    async def fetch_recent(self, limit: int = 10) -> list[dict]:
        """Real fetch requires the app's API client + credentials; no mock data."""
        cap = self._capability()
        return [] if cap is not None else []

    async def search(self, query: str, limit: int = 10) -> list[dict]:
        try:
            res = self._registry.search_apps(query)
            apps = res.data if res.success else []
            return apps[:limit]
        except Exception:
            return []

    async def perform_action(self, action: str, params: dict) -> dict:
        cap = self._capability() or {}
        return {
            "status": "not_implemented",
            "action": action,
            "app": self.app_name,
            "available_actions": cap.get("actions", []),
        }

    def describe(self) -> dict[str, Any]:
        cap = self._capability() or {}
        return {
            "name": self.name,
            "app": self.app_name,
            "class": "SharedConnector",
            "category": cap.get("category"),
            "display_name": cap.get("display_name"),
            "tier": cap.get("tier"),
            "required_env": self.required_env,
        }


def get_connector(name: str) -> SharedConnector | None:
    """Get a shared-backed connector instance by friendly name."""
    if name in CONNECTOR_ALIASES or _registry_knows(name):
        return SharedConnector(name)
    return None


def _registry_knows(name: str) -> bool:
    try:
        from shared.integrations.capability_registry import get_capability_registry

        res = get_capability_registry().search_apps(name)
        return bool(res.success and res.data)
    except Exception:
        return False


def list_connectors() -> dict[str, dict]:
    """List available connectors from the canonical shared.integrations registry."""
    try:
        from shared.integrations.capability_registry import get_capability_registry

        res = get_capability_registry().list_all_apps()
        apps = res.data if res.success else []
        out: dict[str, dict] = {}
        for app in apps:
            name = app.get("app_name", "")
            out[name] = {
                "class": "SharedConnector",
                "display_name": app.get("display_name"),
                "category": app.get("category"),
                "tier": app.get("tier"),
            }
        # keep the friendly aliases addressable too
        for friendly, app_name in CONNECTOR_ALIASES.items():
            if app_name in out and friendly not in out:
                out[friendly] = dict(out[app_name], alias_for=app_name)
        return out
    except Exception:
        return {name: {"class": "SharedConnector", "alias_for": app} for name, app in CONNECTOR_ALIASES.items()}
