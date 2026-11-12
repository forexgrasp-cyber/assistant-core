"""Help system + interactive demo. Platform-specific (no importable shared module
in this checkout for demo/docs), so they live here."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from retention_analytics_core.repository import data_root
from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced.customer_intel import _JsonStore

logger = structlog.get_logger(__name__)

# In-app help articles, keyed by context (page/feature). Each has a short tooltip
# and a longer article body.
HELP_ARTICLES: dict[str, dict[str, Any]] = {
    "campaigns": {
        "title": "Campaigns",
        "tooltip": "A campaign = target segment + flows + schedule + metrics. Run it to see results.",
        "body": "Pick a goal (reduce churn, recover payments, reactivate…). Choose WHO via a segment (a filter over your customer records). Choose which flows run. Set a schedule. Pick success metrics. Run it — we compute before/after and show deltas.",
        "related": ["flows", "customers", "events", "reports"],
    },
    "flows": {
        "title": "Flows",
        "tooltip": "A flow is a reusable automation: event → steps → services. Build once, use in many campaigns.",
        "body": "37 flows are prebuilt. Each shows WHAT it does, WHEN it triggers, WHO it targets, and the RESULT. Pause/activate any flow, assign a target segment, run it manually to test.",
        "related": ["campaigns", "events"],
    },
    "customers": {
        "title": "Customers",
        "tooltip": "Your customer records. Segments filter on these fields. Next-due dates are computed automatically.",
        "body": "Add customers with any fields. If you set last_service_date + service_interval_days, we compute next_due_date and days_until_due — the service-due scan uses this to find who needs a reminder.",
        "related": ["campaigns", "events"],
    },
    "events": {
        "title": "Events",
        "tooltip": "Events are customer actions that trigger workflows. Single form or bulk CSV import with column mapping.",
        "body": "Pick an event type — the form renders the right fields. Or bulk-import a CSV: we detect columns and suggest a mapping to event fields. Export anytime.",
        "related": ["flows", "campaigns"],
    },
    "reports": {
        "title": "Reports",
        "tooltip": "Build a report from analytics widgets, filter by time/campaign/segment, save it, re-run, download.",
        "body": "Choose widgets (retention, RFM, cohorts, SaaS metrics, NPS), set filters, optionally schedule email delivery. Saved reports re-run on demand or on a schedule (daily/weekly/monthly).",
        "related": ["analytics", "campaigns"],
    },
    "analytics": {
        "title": "Analytics",
        "tooltip": "Retention, churn, RFM, cohorts, SaaS metrics — computed on demand from your data.",
        "body": "30-day retention and churn bars, RFM segment counts, cohort table, and the full SaaS suite (MRR, ARR, GRR, NRR, LTV, CAC, ARPU, payback, logo retention, quick ratio).",
        "related": ["reports", "growth"],
    },
    "growth": {
        "title": "Growth & AI",
        "tooltip": "Predictive churn, feedback AI, offer recommendations, benchmarks, goals, A/B tests.",
        "body": "Score churn risk per customer, classify feedback by theme and MRR impact, get the best retention offer per churn reason, compare against industry benchmarks, track goals, run A/B tests.",
        "related": ["analytics", "campaigns"],
    },
    "settings": {
        "title": "Settings",
        "tooltip": "Feature flags, notification channels, quotas, branding, API keys — all editable and saved per tenant.",
        "body": "Toggle features, set daily quotas, pick notification channels, brand the workspace, create/revoke API keys. Everything persists to your tenant.",
        "related": [],
    },
    "presets": {
        "title": "Industry presets",
        "tooltip": "Optional shortcut bundles. Apply any to any business whose records have the fields — not structural verticals.",
        "body": "Each preset bundles customer fields, segments, campaigns, and drip sequences. Apply automotive to a gym if your records have next-due dates. Fully editable after applying.",
        "related": ["campaigns", "customers"],
    },
    "how-it-works": {
        "title": "How it works",
        "tooltip": "The unified loop: customers → segments → campaigns → flows → services → results → reports.",
        "body": "One loop, seven pieces. Campaigns tie your data, targets, automations, and measurement together. See the pain coverage matrix below.",
        "related": ["campaigns", "flows"],
    },
}


class HelpService:
    """In-app help: articles per context, search, contextual lookup."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def register(self) -> None:
        reg = self.registry.register("help", version="1.0.0", metadata={"domain": "platform", "type": "help"})
        reg.actions["list"] = self._list
        reg.actions["get"] = self._get
        reg.actions["search"] = self._search
        reg.actions["context"] = self._context

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "articles": [
            {"id": k, "title": v["title"], "tooltip": v["tooltip"], "related": v.get("related", [])}
            for k, v in HELP_ARTICLES.items()
        ], "count": len(HELP_ARTICLES)}

    async def _get(self, p: dict[str, Any]) -> dict[str, Any]:
        key = p.get("id", "")
        if key in HELP_ARTICLES:
            return {"status": "ok", "article": {"id": key, **HELP_ARTICLES[key]}}
        return {"status": "not_found"}

    async def _search(self, p: dict[str, Any]) -> dict[str, Any]:
        q = (p.get("q") or "").lower()
        if not q:
            return await self._list(p)
        results = []
        for k, v in HELP_ARTICLES.items():
            text = (v["title"] + " " + v["tooltip"] + " " + v["body"]).lower()
            if q in text:
                results.append({"id": k, "title": v["title"], "tooltip": v["tooltip"], "score": text.count(q)})
        results.sort(key=lambda x: x["score"], reverse=True)
        return {"status": "ok", "query": q, "results": results}

    async def _context(self, p: dict[str, Any]) -> dict[str, Any]:
        """Return the help article + related for a given page context."""
        ctx = p.get("context", "")
        base = await self._get({"id": ctx})
        if base["status"] != "ok":
            return base
        related = []
        for rid in base["article"].get("related", []):
            r = await self._get({"id": rid})
            if r["status"] == "ok":
                related.append({"id": rid, "title": r["article"]["title"], "tooltip": r["article"]["tooltip"]})
        return {"status": "ok", "article": base["article"], "related": related}


class DemoService:
    """Interactive demo: seeds realistic data and runs a full campaign end-to-end."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._runs = _JsonStore("demo_runs.json")

    def register(self) -> None:
        reg = self.registry.register("demo", version="1.0.0", metadata={"domain": "platform", "type": "demo"})
        reg.actions["run"] = self._run
        reg.actions["scenario"] = self._scenario
        reg.actions["history"] = self._history

    async def _scenario(self, p: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "scenario": {
            "name": "Auto service business — oil change reminders",
            "steps": [
                "1. Seed 6 customers with vehicles, last service date, 180-day interval",
                "2. Service-due scan finds who is due soon / overdue",
                "3. Create a campaign 'October oil change push' targeting the due-soon segment",
                "4. Run the service-due-reminder flow per member",
                "5. Measure: members, executions, before/after metrics",
                "6. Generate a report from the results",
            ],
        }}

    async def _run(self, p: dict[str, Any]) -> dict[str, Any]:
        """Execute the full demo end-to-end and return every artifact."""
        tenant = p.get("tenant_id", "00000000-0000-0000-0000-000000000001")
        now = datetime.now(UTC)
        artifacts: dict[str, Any] = {"started_at": now.isoformat(), "steps": []}

        def log(step: str, data: Any) -> None:
            artifacts["steps"].append({"step": step, "result": data})
            logger.info("demo.step", step=step)

        # 1. Seed customers
        customers = []
        for i, (name, email, days_ago, interval) in enumerate([
            ("Maria Garcia", "maria@x.com", 175, 180),
            ("John Smith", "john@x.com", 185, 180),
            ("Ana Lee", "ana@x.com", 100, 180),
            ("Bob Chen", "bob@x.com", 178, 180),
            ("Sara Khan", "sara@x.com", 60, 90),
            ("Tom Wilson", "tom@x.com", 200, 180),
        ]):
            last = (now - timedelta(days=days_ago)).isoformat()
            r = await self.registry.invoke("customers.360", "upsert_profile", {
                "tenant_id": tenant, "id": f"demo-c{i}", "name": name, "email": email,
                "plan": "premium" if i % 2 == 0 else "standard", "mrr": 80 + i * 20,
                "health_score": 90 - i * 10, "last_service_date": last,
                "service_interval_days": interval, "service_name": "oil change" if interval == 180 else "tire rotation",
            })
            customers.append(r["profile"])
        log("seed_customers", {"count": len(customers)})

        # 2. Service-due scan
        scan = await self.registry.invoke("customers.service_due", "scan", {"tenant_id": tenant, "within_days": 7})
        log("service_due_scan", {"scanned": scan["scanned"], "due_soon": scan["due_soon_count"], "overdue": scan["overdue_count"]})

        # 3. Create campaign targeting due-soon
        camp = await self.registry.invoke("campaigns", "create", {
            "tenant_id": tenant, "name": "DEMO — Oil change push",
            "description": "Target customers whose oil change is due within 7 days",
            "goal": "reactivate",
            "segment": {"id": "due-soon", "name": "Service due soon", "criteria": {"days_until_due": {"lte": 7, "gte": 0}}},
            "flows": ["service-due-reminder"], "schedule": {"type": "once"},
            "success_metrics": ["reactivation_rate"],
        })
        cid = camp["campaign"]["campaign_id"]
        log("create_campaign", {"campaign_id": cid, "name": camp["campaign"]["name"]})

        # 4. Activate + run with the seeded customers
        await self.registry.invoke("campaigns", "activate", {"tenant_id": tenant, "campaign_id": cid})
        run = await self.registry.invoke("campaigns", "run", {"tenant_id": tenant, "campaign_id": cid, "clients": customers})
        log("run_campaign", {
            "segment_size": run["results"]["segment_size"],
            "flows": run["results"]["flows_run"],
            "outcomes": run["results"]["outcomes_count"],
        })

        # 5. Schedule reminders (the automation half)
        reminders = await self.registry.invoke("customers.service_due", "schedule_reminders", {"tenant_id": tenant, "within_days": 7})
        log("schedule_reminders", {"count": reminders["count"]})

        # 6. Save a report
        report = await self.registry.invoke("ux.reports", "save", {
            "tenant_id": tenant, "name": "DEMO — Service due report",
            "filters": {"time_range": "30d"}, "widgets": ["retention", "saas"],
        })
        log("save_report", {"report_id": report["report"]["report_id"]})

        artifacts["finished_at"] = datetime.now(UTC).isoformat()
        artifacts["summary"] = {
            "customers_seeded": len(customers),
            "due_soon": scan["due_soon_count"],
            "overdue": scan["overdue_count"],
            "campaign_id": cid,
            "campaign_segment_size": run["results"]["segment_size"],
            "reminders_scheduled": reminders["count"],
            "report_id": report["report"]["report_id"],
        }
        run_id = f"demo-{uuid.uuid4().hex[:12]}"
        self._runs.upsert("run_id", {"run_id": run_id, "tenant_id": tenant, **artifacts})
        return {"status": "ok", "run_id": run_id, **artifacts}

    async def _history(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        return {"status": "ok", "runs": [r for r in self._runs.load() if r.get("tenant_id") == tenant]}


__all__ = ["HelpService", "DemoService", "HELP_ARTICLES"]
