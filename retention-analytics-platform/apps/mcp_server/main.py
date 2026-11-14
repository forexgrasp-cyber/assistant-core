"""FastMCP server exposing retention analytics as natural-language tools.

AI assistants can query roster, retention, campaigns, flows, RFM segments and
subscriptions without knowing the underlying service boundaries.

Tools are async (FastMCP supports async tool functions natively), so they share
the process event loop with the API instead of creating a new one per call via
``asyncio.run()``.
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
async def get_roster_summary(tenant_id: str) -> dict[str, Any]:
    """Get the roster summary for a tenant."""
    return await registry.invoke("analytics.metric", "compute_roster", {"tenant_id": tenant_id})


@mcp.tool()
async def get_retention_metrics(tenant_id: str) -> dict[str, Any]:
    """Get retention and churn metrics for a tenant."""
    return await registry.invoke("analytics.metric", "compute_retention", {"tenant_id": tenant_id})


@mcp.tool()
async def get_rfm_segments(tenant_id: str) -> dict[str, Any]:
    """Get RFM segments for a tenant."""
    return await registry.invoke("analytics.metric", "compute_rfm", {"tenant_id": tenant_id})


@mcp.tool()
async def get_subscription_metrics(tenant_id: str) -> dict[str, Any]:
    """Get subscription metrics for a tenant."""
    return await registry.invoke(
        "analytics.cohort", "compute_cohorts", {"tenant_id": tenant_id, "cohort_months": 6}
    )


@mcp.tool()
async def run_workflow(workflow_id: str, tenant_id: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run a retention workflow by id."""
    run = await engine.run(workflow_id, tenant_id, initial_context=context or {})
    return {
        "id": run.id,
        "workflow_id": run.workflow_id,
        "status": run.status,
        "step_outputs": run.step_outputs,
        "error": run.error,
    }


@mcp.tool()
async def ask_hiro(question: str, tenant_id: str | None = None) -> dict[str, Any]:
    """Ask Hiro a natural-language question about agency roster, clients, or platform analytics."""
    params = {"question": question}
    if tenant_id:
        params["tenant_id"] = tenant_id
    return await registry.invoke("hiro.mcp", "ask", params)


@mcp.tool()
async def hiro_roster(tenant_id: str | None = None) -> dict[str, Any]:
    """Get the full agency roster from Hiro analytics."""
    params = {}
    if tenant_id:
        params["tenant_id"] = tenant_id
    return await registry.invoke("hiro.mcp", "roster", params)


@mcp.tool()
def list_services() -> dict[str, Any]:
    """List all registered services and their actions."""
    return {
        "services": [
            {"name": name, "actions": sorted(registry.get(name).actions.keys())}
            for name in registry.list_services()
        ]
    }


__all__ = ["mcp"]