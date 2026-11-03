"""FastMCP server exposing retention analytics as natural-language tools.

AI assistants can query roster, retention, campaigns, flows, RFM segments and
subscriptions without knowing the underlying service boundaries.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

mcp = FastMCP("retention-analytics")

# In production these call the API gateway / services directly. Here they
# delegate to the shared registry/engine so MCP tools and the REST API share
# the same integration path (no silo between AI and UI).
from apps.api.main import engine, registry  # noqa: E402


@mcp.tool()
def get_roster_summary(tenant_id: str) -> dict[str, Any]:
    """Get the roster summary for a tenant."""
    import asyncio

    return asyncio.run(
        registry.invoke("analytics.metric", "compute_roster", {"tenant_id": tenant_id})
    )


@mcp.tool()
def get_retention_metrics(tenant_id: str) -> dict[str, Any]:
    """Get retention and churn metrics for a tenant."""
    import asyncio

    return asyncio.run(
        registry.invoke("analytics.metric", "compute_retention", {"tenant_id": tenant_id})
    )


@mcp.tool()
def get_rfm_segments(tenant_id: str) -> dict[str, Any]:
    """Get RFM segments for a tenant."""
    import asyncio

    return asyncio.run(
        registry.invoke("analytics.metric", "compute_rfm", {"tenant_id": tenant_id})
    )


@mcp.tool()
def get_subscription_metrics(tenant_id: str) -> dict[str, Any]:
    """Get subscription metrics for a tenant."""
    import asyncio

    return asyncio.run(
        registry.invoke("analytics.cohort", "compute_cohorts", {"tenant_id": tenant_id, "cohort_months": 6})
    )


@mcp.tool()
def run_workflow(workflow_id: str, tenant_id: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run a retention workflow by id."""
    import asyncio

    return asyncio.run(engine.run(workflow_id, tenant_id, initial_context=context or {}))


@mcp.tool()
def list_services() -> dict[str, Any]:
    """List all registered services and their actions."""
    from apps.api.main import registry as _r

    return {
        "services": [
            {"name": name, "actions": sorted(_r.get(name).actions.keys())} for name in _r.list_services()
        ]
    }


__all__ = ["mcp"]
