"""
MCP Server for Retention Analytics Platform.

Self-contained server that queries the REST API via httpx.
Supports both stdio and SSE transports.

Run:
    python -m mcp_server.main              # stdio (for Claude Desktop etc.)
    python -m mcp_server.main --sse        # SSE on port from MCP_PORT env
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx
import structlog

log = structlog.get_logger(__name__)

API_BASE_URL = os.getenv("API_URL", "http://localhost:8765")
API_TOKEN = os.getenv("API_TOKEN", "")  # Bearer token for the API


def _headers() -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if API_TOKEN:
        h["Authorization"] = f"Bearer {API_TOKEN}"
    return h


async def _get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    async with httpx.AsyncClient(base_url=API_BASE_URL, headers=_headers(), timeout=30.0) as client:
        r = await client.get(path, params=params)
        r.raise_for_status()
        return r.json()


async def _post(path: str, json_body: Optional[Dict[str, Any]] = None, params: Optional[Dict[str, Any]] = None) -> Any:
    async with httpx.AsyncClient(base_url=API_BASE_URL, headers=_headers(), timeout=60.0) as client:
        r = await client.post(path, json=json_body, params=params)
        r.raise_for_status()
        return r.json()


# ── Tool implementations ──────────────────────────────────────────────────

async def get_roster_summary(days: int = 30) -> Dict[str, Any]:
    """Agency-level roster summary: total revenue, orders, new customers, channel breakdown."""
    return await _get("/api/v1/analytics/dashboard", {"days": days})


async def get_client_metrics(client_id: str, days: int = 30) -> Dict[str, Any]:
    """Detailed metrics for a specific client."""
    return await _get("/api/v1/analytics/dashboard", {"client_id": client_id, "days": days})


async def get_campaign_performance(campaign_id: str) -> Dict[str, Any]:
    """Campaign stats: sent, delivered, opened, clicked, revenue, rates."""
    return await _get(f"/api/v1/engagement/email/campaigns/{campaign_id}/stats")


async def get_flow_analytics(flow_id: str) -> Dict[str, Any]:
    """Flow analytics: total executions, completion rate, revenue."""
    return await _get(f"/api/v1/engagement/flows/{flow_id}/analytics")


async def get_retention_cohorts(months: int = 12) -> Dict[str, Any]:
    """Cohort retention analysis: repeat rates, revenue per customer by cohort month."""
    return await _get("/api/v1/analytics/cohorts", {"months": months})


async def get_rfm_segments() -> Dict[str, Any]:
    """RFM segment analysis: champions, loyal, at-risk, hibernating etc. with revenue."""
    return await _get("/api/v1/analytics/rfm")


async def get_attribution(days: int = 30) -> Dict[str, Any]:
    """Multi-touch attribution: revenue and touchpoints by channel."""
    return await _get("/api/v1/analytics/attribution", {"days": days})


async def get_subscription_metrics() -> Dict[str, Any]:
    """Subscription analytics: MRR, active subs, churn."""
    return await _get("/api/v1/ecommerce/subscriptions", {"limit": 1})


async def get_predictive_metrics() -> Dict[str, Any]:
    """Predictive metrics: churn risk, predicted LTV."""
    return await _get("/api/v1/analytics/predictive")


async def get_anomalies(status: str = "open", days: int = 30) -> Dict[str, Any]:
    """Detected anomalies: spikes, drops, trend changes with severity."""
    return await _get("/api/v1/analytics/anomalies", {"status": status, "days": days})


async def get_realtime_metrics() -> Dict[str, Any]:
    """Today's real-time metrics: revenue, orders, sessions."""
    return await _get("/api/v1/analytics/realtime")


async def list_clients() -> Dict[str, Any]:
    """List all clients with their stats."""
    return await _get("/api/v1/clients", {"limit": 100})


async def list_reports() -> Dict[str, Any]:
    """List saved reports."""
    return await _get("/api/v1/reports", {"limit": 50})


async def run_report(report_id: str) -> Dict[str, Any]:
    """Trigger a report run."""
    return await _post(f"/api/v1/reports/{report_id}/run", {})


async def list_workflows() -> Dict[str, Any]:
    """List automation workflows."""
    return await _get("/api/v1/workflows", {"limit": 50})


async def list_vertical_packs() -> Dict[str, Any]:
    """List available vertical packs (marketplace)."""
    return await _get("/api/v1/vertical-packs", {"limit": 50})


# ── MCP wire protocol (JSON-RPC over stdio) ───────────────────────────────

TOOLS: List[Dict[str, Any]] = [
    {"name": "get_roster_summary", "description": "Agency-level roster summary: revenue, orders, customers, channel breakdown", "input_schema": {"type": "object", "properties": {"days": {"type": "integer", "default": 30}}}},
    {"name": "get_client_metrics", "description": "Detailed metrics for a specific client", "input_schema": {"type": "object", "properties": {"client_id": {"type": "string"}, "days": {"type": "integer", "default": 30}}, "required": ["client_id"]}},
    {"name": "get_campaign_performance", "description": "Email campaign stats: opens, clicks, revenue, rates", "input_schema": {"type": "object", "properties": {"campaign_id": {"type": "string"}}, "required": ["campaign_id"]}},
    {"name": "get_flow_analytics", "description": "Automation flow analytics: executions, completion rate, revenue", "input_schema": {"type": "object", "properties": {"flow_id": {"type": "string"}}, "required": ["flow_id"]}},
    {"name": "get_retention_cohorts", "description": "Cohort retention analysis with repeat rates", "input_schema": {"type": "object", "properties": {"months": {"type": "integer", "default": 12}}}},
    {"name": "get_rfm_segments", "description": "RFM segmentation: champions, loyal, at-risk etc.", "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_attribution", "description": "Multi-touch attribution by channel", "input_schema": {"type": "object", "properties": {"days": {"type": "integer", "default": 30}}}},
    {"name": "get_subscription_metrics", "description": "Subscription analytics: MRR, active subs", "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_predictive_metrics", "description": "Predictive metrics: churn risk, predicted LTV", "input_schema": {"type": "object", "properties": {}}},
    {"name": "get_anomalies", "description": "Detected anomalies: spikes, drops, trend changes", "input_schema": {"type": "object", "properties": {"status": {"type": "string", "default": "open"}, "days": {"type": "integer", "default": 30}}}},
    {"name": "get_realtime_metrics", "description": "Today's real-time metrics", "input_schema": {"type": "object", "properties": {}}},
    {"name": "list_clients", "description": "List all clients with their stats", "input_schema": {"type": "object", "properties": {}}},
    {"name": "list_reports", "description": "List saved reports", "input_schema": {"type": "object", "properties": {}}},
    {"name": "run_report", "description": "Trigger a report run by ID", "input_schema": {"type": "object", "properties": {"report_id": {"type": "string"}}, "required": ["report_id"]}},
    {"name": "list_workflows", "description": "List automation workflows", "input_schema": {"type": "object", "properties": {}}},
    {"name": "list_vertical_packs", "description": "List available vertical packs", "input_schema": {"type": "object", "properties": {}}},
]

TOOL_FUNCS = {
    "get_roster_summary": get_roster_summary,
    "get_client_metrics": get_client_metrics,
    "get_campaign_performance": get_campaign_performance,
    "get_flow_analytics": get_flow_analytics,
    "get_retention_cohorts": get_retention_cohorts,
    "get_rfm_segments": get_rfm_segments,
    "get_attribution": get_attribution,
    "get_subscription_metrics": get_subscription_metrics,
    "get_predictive_metrics": get_predictive_metrics,
    "get_anomalies": get_anomalies,
    "get_realtime_metrics": get_realtime_metrics,
    "list_clients": list_clients,
    "list_reports": list_reports,
    "run_report": run_report,
    "list_workflows": list_workflows,
    "list_vertical_packs": list_vertical_packs,
}


def _respond(msg_id: Any, result: Dict[str, Any]) -> None:
    print(json.dumps({"jsonrpc": "2.0", "id": msg_id, "result": result}), flush=True)


def _respond_error(msg_id: Any, code: int, message: str) -> None:
    print(json.dumps({"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}), flush=True)


async def handle_request(msg: Dict[str, Any]) -> None:
    msg_id = msg.get("id")
    method = msg.get("method")

    if method == "initialize":
        _respond(msg_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "retention-analytics", "version": "0.1.0"},
        })
    elif method == "notifications/initialized":
        pass  # notification, no response
    elif method == "tools/list":
        _respond(msg_id, {"tools": TOOLS})
    elif method == "tools/call":
        params = msg.get("params", {})
        name = params.get("name")
        args = params.get("arguments", {})
        func = TOOL_FUNCS.get(name)
        if not func:
            _respond_error(msg_id, -32602, f"Unknown tool: {name}")
            return
        try:
            result = await func(**args)
            _respond(msg_id, {
                "content": [{"type": "text", "text": json.dumps(result, default=str, indent=2)}],
                "isError": False,
            })
        except Exception as e:
            log.error("tool_call_failed", tool=name, error=str(e))
            _respond(msg_id, {
                "content": [{"type": "text", "text": f"Error: {e}"}],
                "isError": True,
            })
    elif method == "ping":
        _respond(msg_id, {})
    else:
        if msg_id is not None:
            _respond_error(msg_id, -32601, f"Method not found: {method}")


async def run_stdio() -> None:
    """Main stdio loop: read JSON-RPC lines from stdin, respond on stdout."""
    import sys
    log.info("mcp_server_started", transport="stdio", api=API_BASE_URL)
    loop = asyncio.get_event_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        await handle_request(msg)


async def run_sse(port: int) -> None:
    """SSE transport using Starlette (for remote MCP clients)."""
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse, StreamingResponse
    from starlette.routing import Route
    import uvicorn

    async def messages(request):
        # Check for API key in header
        api_key = request.headers.get("Authorization")
        if api_key and api_key.startswith("Bearer "):
            api_key = api_key[7:]  # Remove "Bearer " prefix
        elif "X-API-Key" in request.headers:
            api_key = request.headers["X-API-Key"]
        else:
            return JSONResponse({"error": "Missing API key"}, status_code=401)

        # Validate API key (in production, validate against database)
        if not api_key:
            return JSONResponse({"error": "Invalid API key"}, status_code=401)

        body = await request.json()
        await handle_request(body)
        return JSONResponse({})

    async def sse(request):
        async def event_stream():
            yield f"data: {json.dumps({'type': 'ready'})}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    app = Starlette(routes=[
        Route("/sse", sse),
        Route("/messages", messages, methods=["POST"]),
    ])
    log.info("mcp_server_started", transport="sse", port=port)
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


def main() -> None:
    parser = argparse.ArgumentParser(description="Retention Analytics MCP Server")
    parser.add_argument("--sse", action="store_true", help="Run with SSE transport instead of stdio")
    parser.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", "8767")))
    args = parser.parse_args()

    if args.sse:
        asyncio.run(run_sse(args.port))
    else:
        asyncio.run(run_stdio())


if __name__ == "__main__":
    main()