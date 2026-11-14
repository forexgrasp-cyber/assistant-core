"""Hiro MCP server — exposes Hiro analytics as MCP tools for AI assistants."""

from __future__ import annotations

import os
from typing import Any

import structlog

from retention_analytics_core.service_registry import ServiceRegistry
from shared.integrations.hiro_client import HiroClient, HIRO_DEFAULT_API_BASE, HIRO_DEFAULT_MCP_URL

logger = structlog.get_logger(__name__)


class HiroMCPService:
    """MCP bridge to Hiro Analytics: ask_hiro, hiro_roster tools."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._client = HiroClient(
            api_key=os.environ.get("HIRO_API_KEY", ""),
            api_base=os.environ.get("HIRO_API_BASE", HIRO_DEFAULT_API_BASE),
            mcp_url=os.environ.get("HIRO_MCP_URL", HIRO_DEFAULT_MCP_URL),
        )

    def register(self) -> None:
        reg = self.registry.register("hiro.mcp", version="1.0.0", metadata={"domain": "integrations", "type": "mcp"})
        reg.actions["ask"] = self._ask
        reg.actions["roster"] = self._roster
        reg.actions["platforms"] = self._platforms
        reg.actions["sync"] = self._sync
        reg.actions["syncs"] = self._syncs

    async def _ask(self, p: dict[str, Any]) -> dict[str, Any]:
        """Ask a natural-language question via Hiro's ask_hiro MCP tool."""
        return await self._client.ask(p.get("question", ""), p.get("tenant_id"))

    async def _roster(self, p: dict[str, Any]) -> dict[str, Any]:
        """Get agency roster via Hiro's hiro_roster MCP tool."""
        return await self._client.mcp_roster(p.get("tenant_id"))

    async def _platforms(self, p: dict[str, Any]) -> dict[str, Any]:
        """Get Hiro platform catalog via REST."""
        return await self._client.platforms()

    async def _sync(self, p: dict[str, Any]) -> dict[str, Any]:
        """Trigger a platform sync via Hiro REST."""
        return await self._client.sync_platform(p.get("platform", ""), p.get("tenant_id", ""))

    async def _syncs(self, p: dict[str, Any]) -> dict[str, Any]:
        """Get sync history via Hiro REST."""
        return await self._client.syncs(p.get("tenant_id"))


__all__ = ["HiroMCPService"]