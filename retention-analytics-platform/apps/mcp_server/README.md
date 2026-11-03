# MCP Server

AI-native access to retention analytics. Tools:
- `get_roster_summary` — roster + churn counts
- `get_retention_metrics` — retention / churn rate
- `get_rfm_segments` — RFM customer segments
- `get_subscription_metrics` — subscription cohorts
- `run_workflow` — run a retention workflow
- `list_services` — all services + actions

Run:

```bash
uv run python -m mcp_server.main
```
