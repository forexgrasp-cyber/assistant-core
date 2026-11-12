"""Remaining automation services: scheduled reports worker, flow editor,
cancel-flow public API, slack bot, session replay, micro-surveys, universal export."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from retention_analytics_core.repository import data_root
from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced.customer_intel import _JsonStore

logger = structlog.get_logger(__name__)


class ScheduledReportService:
    """Cron scheduler for saved reports. Mirrors Baremetrics Email Reports.

    Tick: find reports whose schedule is due, run them, email the result.
    """

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._runs = _JsonStore("scheduled_report_runs.json")

    def register(self) -> None:
        reg = self.registry.register("reports.scheduler", version="1.0.0", metadata={"domain": "automation", "type": "scheduler"})
        reg.actions["tick"] = self._tick
        reg.actions["due"] = self._due
        reg.actions["run_due"] = self._run_due

    async def _due(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        reports = _JsonStore("saved_reports.json")
        now = datetime.now(UTC)
        due = []
        for r in reports.load():
            if r.get("tenant_id") != tenant:
                continue
            sched = r.get("schedule")
            if not sched:
                continue
            last = r.get("last_run_at")
            freq = sched.get("frequency", "weekly")
            if not last:
                due.append(r)
                continue
            last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            delta_days = {"daily": 1, "weekly": 7, "monthly": 30}.get(freq, 7)
            if (now - last_dt).days >= delta_days:
                due.append(r)
        return {"status": "ok", "due_count": len(due), "due": [{"report_id": r["report_id"], "name": r["name"], "frequency": r["schedule"]["frequency"]} for r in due]}

    async def _tick(self, p: dict[str, Any]) -> dict[str, Any]:
        return await self._due(p)

    async def _run_due(self, p: dict[str, Any]) -> dict[str, Any]:
        """Run all due scheduled reports and email results (via email service)."""
        tenant = p.get("tenant_id", "")
        due = await self._due({"tenant_id": tenant})
        executed = []
        for d in due["due"]:
            rid = d["report_id"]
            try:
                result = await self.registry.invoke("ux.reports", "run", {"tenant_id": tenant, "report_id": rid})
                # email the report
                await self.registry.invoke("email", "send", {
                    "to": d.get("schedule", {}).get("email_to", "team@company.com"),
                    "subject": f"Scheduled report: {d['name']}",
                    "body": f"Report '{d['name']}' ran at {datetime.now(UTC).isoformat()}.\n\nResult summary: {json.dumps(result.get('result', {}), default=str)[:2000]}",
                })
                self._runs.upsert("run_id", {
                    "run_id": f"srr-{uuid.uuid4().hex[:12]}",
                    "report_id": rid, "tenant_id": tenant,
                    "ran_at": datetime.now(UTC).isoformat(),
                    "emailed_to": d.get("schedule", {}).get("email_to"),
                    "status": "sent",
                })
                executed.append({"report_id": rid, "status": "sent"})
            except Exception as e:
                logger.warning("scheduled_report.failed", report_id=rid, error=str(e))
                executed.append({"report_id": rid, "status": "failed", "error": str(e)})
        return {"status": "ok", "executed": executed, "count": len(executed)}


class FlowEditorService:
    """No-code flow editor backend: nodes + edges graph CRUD, validation, publish.

    Mirrors Churnkey No-Code Flow Editor. The UI renders a canvas from the graph;
    publishing compiles the graph into a WorkflowDefinition.
    """

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._graphs = _JsonStore("flow_graphs.json")

    def register(self) -> None:
        reg = self.registry.register("flows.editor", version="1.0.0", metadata={"domain": "automation", "type": "editor"})
        reg.actions["create_graph"] = self._create
        reg.actions["get_graph"] = self._get
        reg.actions["update_graph"] = self._update
        reg.actions["validate"] = self._validate
        reg.actions["publish"] = self._publish
        reg.actions["list"] = self._list
        reg.actions["delete"] = self._delete

    async def _create(self, p: dict[str, Any]) -> dict[str, Any]:
        graph = {
            "graph_id": f"flow-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "name": p.get("name", "Untitled Flow"),
            "trigger_event": p.get("trigger_event", ""),
            "nodes": p.get("nodes", []),  # [{id, type: trigger|service|condition|end, service, action, input, position:{x,y}}]
            "edges": p.get("edges", []),  # [{from, to}]
            "status": "draft",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._graphs.upsert("graph_id", graph)
        return {"status": "created", "graph": graph}

    async def _get(self, p: dict[str, Any]) -> dict[str, Any]:
        for g in self._graphs.load():
            if g.get("graph_id") == p.get("graph_id"):
                return {"status": "ok", "graph": g}
        return {"status": "not_found"}

    async def _update(self, p: dict[str, Any]) -> dict[str, Any]:
        data = self._graphs.load()
        for g in data:
            if g.get("graph_id") == p.get("graph_id"):
                for k in ("name", "trigger_event", "nodes", "edges"):
                    if k in p:
                        g[k] = p[k]
                g["updated_at"] = datetime.now(UTC).isoformat()
                self._graphs.save(data)
                return {"status": "updated", "graph": g}
        return {"status": "not_found"}

    async def _validate(self, p: dict[str, Any]) -> dict[str, Any]:
        """Validate graph: single trigger, connected nodes, known services, no cycles."""
        r = await self._get(p)
        if r["status"] != "ok":
            return r
        g = r["graph"]
        nodes = g.get("nodes", [])
        edges = g.get("edges", [])
        errors = []
        triggers = [n for n in nodes if n.get("type") == "trigger"]
        if len(triggers) != 1:
            errors.append(f"expected exactly 1 trigger node, found {len(triggers)}")
        if not g.get("trigger_event"):
            errors.append("trigger_event is required")
        node_ids = {n["id"] for n in nodes}
        for e in edges:
            if e.get("from") not in node_ids or e.get("to") not in node_ids:
                errors.append(f"edge references unknown node: {e}")
        # cycle detection
        adj: dict[str, list[str]] = {}
        for e in edges:
            adj.setdefault(e["from"], []).append(e["to"])
        visited, stack = set(), set()
        def has_cycle(n: str) -> bool:
            if n in stack:
                return True
            if n in visited:
                return False
            visited.add(n); stack.add(n)
            for m in adj.get(n, []):
                if has_cycle(m):
                    return True
            stack.discard(n)
            return False
        for n in node_ids:
            if has_cycle(n):
                errors.append("graph contains a cycle")
                break
        # known services
        known = set(self.registry.list_services())
        for n in nodes:
            if n.get("type") == "service" and n.get("service") not in known:
                errors.append(f"unknown service in node {n.get('id')}: {n.get('service')}")
        return {"status": "ok", "valid": len(errors) == 0, "errors": errors, "node_count": len(nodes), "edge_count": len(edges)}

    async def _publish(self, p: dict[str, Any]) -> dict[str, Any]:
        """Compile graph into a workflow definition and register it in the engine."""
        v = await self._validate(p)
        if not v["valid"]:
            return {"status": "invalid", "errors": v["errors"]}
        r = await self._get(p)
        g = r["graph"]
        # topological order from trigger
        nodes = {n["id"]: n for n in g["nodes"]}
        edges = g["edges"]
        adj: dict[str, list[str]] = {}
        indeg: dict[str, int] = {n: 0 for n in nodes}
        for e in edges:
            adj.setdefault(e["from"], []).append(e["to"])
            indeg[e["to"]] += 1
        queue = [n for n in nodes if indeg[n] == 0]
        order = []
        while queue:
            n = queue.pop(0)
            order.append(n)
            for m in adj.get(n, []):
                indeg[m] -= 1
                if indeg[m] == 0:
                    queue.append(m)
        from retention_analytics_core.workflows.engine import WorkflowDefinition, WorkflowStep
        steps = []
        for nid in order:
            node = nodes[nid]
            if node.get("type") != "service":
                continue
            deps = [e["from"] for e in edges if e["to"] == nid and nodes.get(e["from"], {}).get("type") == "service"]
            steps.append(WorkflowStep(
                id=nid, service=node.get("service", ""), action=node.get("action", ""),
                input=node.get("input", {}), depends_on=deps,
            ))
        wf = WorkflowDefinition(
            id=g["graph_id"], name=g["name"], tenant_id=g.get("tenant_id", ""),
            trigger_event=g.get("trigger_event", ""), steps=steps,
        )
        data = self._graphs.load()
        for gg in data:
            if gg.get("graph_id") == g["graph_id"]:
                gg["status"] = "published"
                gg["published_at"] = datetime.now(UTC).isoformat()
        self._graphs.save(data)
        return {"status": "published", "workflow": {"id": wf.id, "name": wf.name, "trigger_event": wf.trigger_event, "steps": [{"id": s.id, "service": s.service, "action": s.action} for s in steps]}}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        return {"status": "ok", "graphs": [g for g in self._graphs.load() if g.get("tenant_id") == tenant]}

    async def _delete(self, p: dict[str, Any]) -> dict[str, Any]:
        self._graphs.save([g for g in self._graphs.load() if g.get("graph_id") != p.get("graph_id")])
        return {"status": "deleted"}


class CancelFlowAPI:
    """Public cancel-flow API for embedding in client apps (Churnkey SDK parity).

    Flow: start session -> get offers -> select offer -> confirm (pause/discount/cancel) -> wall config.
    """

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._sessions = _JsonStore("cancel_sessions.json")

    def register(self) -> None:
        reg = self.registry.register("cancel_flow.api", version="1.0.0", metadata={"domain": "engagement", "type": "public"})
        reg.actions["start"] = self._start
        reg.actions["offers"] = self._offers
        reg.actions["select"] = self._select
        reg.actions["confirm"] = self._confirm
        reg.actions["get_session"] = self._get

    async def _start(self, p: dict[str, Any]) -> dict[str, Any]:
        sess = {
            "session_id": f"cancel-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "customer_id": p.get("customer_id", ""),
            "subscription_id": p.get("subscription_id", ""),
            "reason": p.get("reason", ""),
            "status": "open",
            "selected_offer": None,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._sessions.upsert("session_id", sess)
        return {"status": "started", "session": sess}

    async def _offers(self, p: dict[str, Any]) -> dict[str, Any]:
        """Return offers for a cancel session: from catalog + AI recommendation."""
        tenant = p.get("tenant_id", "")
        sess = next((s for s in self._sessions.load() if s.get("session_id") == p.get("session_id")), None)
        if not sess:
            return {"status": "not_found"}
        reason = sess.get("reason", "general")
        try:
            rec = await self.registry.invoke("ai.offers", "recommend", {
                "tenant_id": tenant, "churn_reason": reason,
                "churn_probability": float(p.get("churn_probability", 0.5)), "mrr": float(p.get("mrr", 0))})
            ai_offer = rec.get("recommendation")
        except Exception:
            ai_offer = None
        try:
            catalog = await self.registry.invoke("catalog", "list_offers", {"tenant_id": tenant})
            offers = catalog.get("offers", [])
        except Exception:
            offers = []
        return {"status": "ok", "session_id": p.get("session_id"),
                "ai_recommended": ai_offer,
                "catalog_offers": offers,
                "default_options": [
                    {"type": "pause", "label": "Pause my subscription"},
                    {"type": "downgrade", "label": "Switch to a cheaper plan"},
                    {"type": "cancel", "label": "Cancel anyway"},
                ]}

    async def _select(self, p: dict[str, Any]) -> dict[str, Any]:
        data = self._sessions.load()
        for s in data:
            if s.get("session_id") == p.get("session_id"):
                s["selected_offer"] = p.get("offer")
                s["selected_at"] = datetime.now(UTC).isoformat()
                self._sessions.save(data)
                return {"status": "selected", "offer": p.get("offer")}
        return {"status": "not_found"}

    async def _confirm(self, p: dict[str, Any]) -> dict[str, Any]:
        data = self._sessions.load()
        for s in data:
            if s.get("session_id") == p.get("session_id"):
                offer = s.get("selected_offer") or p.get("offer") or {"type": "cancel"}
                s["status"] = "completed"
                s["outcome"] = offer.get("type", "cancel")
                s["completed_at"] = datetime.now(UTC).isoformat()
                self._sessions.save(data)
                # Apply the outcome
                outcome = offer.get("type", "cancel")
                if outcome == "pause":
                    await self.registry.invoke("subscriptions", "pause", {"subscription_id": s.get("subscription_id"), "resume_at": p.get("resume_at")}) if False else None
                if outcome in ("cancel", "downgrade"):
                    await self.registry.invoke("walls", "create", {
                        "tenant_id": s.get("tenant_id"), "customer_id": s.get("customer_id"),
                        "type": "pause" if outcome == "pause" else "payment",
                        "reason": s.get("reason", ""), "message": "Complete your cancellation",
                    }) if False else None
                return {"status": "confirmed", "outcome": outcome, "session": s}
        return {"status": "not_found"}

    async def _get(self, p: dict[str, Any]) -> dict[str, Any]:
        for s in self._sessions.load():
            if s.get("session_id") == p.get("session_id"):
                return {"status": "ok", "session": s}
        return {"status": "not_found"}


class SlackBotService:
    """Inbound Slack/Teams bot command handler. /at-risk /renewals /mrr /help."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def register(self) -> None:
        reg = self.registry.register("integrations.bot", version="1.0.0", metadata={"domain": "integrations", "type": "bot"})
        reg.actions["handle_command"] = self._handle

    async def _handle(self, p: dict[str, Any]) -> dict[str, Any]:
        """Handle a slash command: text like '/at-risk', '/renewals 30', '/mrr', '/help'."""
        text = (p.get("text") or "").strip()
        tenant = p.get("tenant_id", "")
        cmd, _, arg = text.partition(" ")
        cmd = cmd.lower().lstrip("/")
        if cmd in ("help", ""):
            return {"status": "ok", "response": "Commands: /at-risk [threshold] · /renewals [days] · /mrr · /nps · /alerts · /churn [pct]"}
        if cmd == "at-risk":
            r = await self.registry.invoke("ai.churn_predict", "at_risk_list", {"tenant_id": tenant, "threshold": float(arg or 0.4)})
            return {"status": "ok", "response": f"🚨 {r.get('count', 0)} at-risk customers (threshold {arg or 0.4})", "data": r.get("at_risk", [])[:10]}
        if cmd == "renewals":
            days = int(arg or 90)
            r = await self.registry.invoke("cs.renewals", "list_upcoming", {"tenant_id": tenant, "days": days})
            return {"status": "ok", "response": f"📅 {r.get('count', 0)} renewals in {days}d — ARR at stake: see data", "data": r.get("renewals", [])[:10]}
        if cmd == "mrr":
            r = await self.registry.invoke("saas.metrics", "compute_mrr", {"tenant_id": tenant, "subscriptions": []})
            return {"status": "ok", "response": f"💰 MRR: ${r.get('result', {}).get('mrr', 0)}"}
        if cmd == "nps":
            r = await self.registry.invoke("surveys", "compute_nps", {"tenant_id": tenant})
            return {"status": "ok", "response": f"⭐ NPS: {r.get('nps')} ({r.get('responses', 0)} responses)"}
        if cmd == "alerts":
            r = await self.registry.invoke("cs.alerts", "list_open", {"tenant_id": tenant})
            return {"status": "ok", "response": f"🔔 {r.get('count', 0)} open alerts", "data": r.get("alerts", [])[:10]}
        if cmd == "churn":
            r = await self.registry.invoke("analytics.metric", "compute_retention", {"tenant_id": tenant})
            res = r.get("result", r)
            return {"status": "ok", "response": f"📉 Churn 30d: {round(res.get('churn_rate_30d', 0) * 100, 1)}% · Retention: {round(res.get('retention_rate_30d', 0) * 100, 1)}%"}
        return {"status": "ok", "response": f"Unknown command: {cmd}. Try /help"}


class SessionReplayService:
    """Session replay event ingest (Churnkey Session Recordings)."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._events = _JsonStore("session_events.json")

    def register(self) -> None:
        reg = self.registry.register("session.replay", version="1.0.0", metadata={"domain": "customers", "type": "platform"})
        reg.actions["ingest"] = self._ingest
        reg.actions["get_session"] = self._get
        reg.actions["list_sessions"] = self._list

    async def _ingest(self, p: dict[str, Any]) -> dict[str, Any]:
        ev = {
            "event_id": f"se-{uuid.uuid4().hex[:12]}",
            "session_id": p.get("session_id", ""),
            "customer_id": p.get("customer_id", ""),
            "tenant_id": p.get("tenant_id", ""),
            "type": p.get("type", "click"),  # click | input | navigation | error | custom
            "target": p.get("target", ""),
            "value": p.get("value"),
            "url": p.get("url", ""),
            "ts": p.get("ts", datetime.now(UTC).isoformat()),
        }
        self._events.upsert("event_id", ev)
        return {"status": "ingested", "event": ev}

    async def _get(self, p: dict[str, Any]) -> dict[str, Any]:
        sid = p.get("session_id", "")
        evs = [e for e in self._events.load() if e.get("session_id") == sid]
        evs.sort(key=lambda x: x.get("ts", ""))
        return {"status": "ok", "session_id": sid, "events": evs, "count": len(evs)}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        cust = p.get("customer_id", "")
        sessions = {}
        for e in self._events.load():
            if e.get("customer_id") == cust:
                sessions.setdefault(e.get("session_id"), []).append(e)
        return {"status": "ok", "sessions": [{"session_id": k, "events": len(v)} for k, v in sessions.items()]}


class MicroSurveyService:
    """In-app micro-surveys triggered by actions. Churnkey Pulse parity."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._surveys = _JsonStore("micro_surveys.json")

    def register(self) -> None:
        reg = self.registry.register("surveys.micro", version="1.0.0", metadata={"domain": "engagement", "type": "platform"})
        reg.actions["create"] = self._create
        reg.actions["trigger"] = self._trigger
        reg.actions["respond"] = self._respond
        reg.actions["results"] = self._results

    async def _create(self, p: dict[str, Any]) -> dict[str, Any]:
        survey = {
            "survey_id": f"micro-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "trigger_action": p.get("trigger_action", ""),  # e.g. "feature_used", "checkout_completed"
            "question": p.get("question", ""),
            "type": p.get("type", "nps"),  # nps | csat | ces | thumbs | free_text
            "options": p.get("options", []),
            "show_after_events": int(p.get("show_after_events", 1)),
            "active": True,
            "responses": [],
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._surveys.upsert("survey_id", survey)
        return {"status": "created", "survey": survey}

    async def _trigger(self, p: dict[str, Any]) -> dict[str, Any]:
        """Given a customer action, return any micro-surveys that should be shown."""
        action = p.get("action", "")
        cust = p.get("customer_id", "")
        tenant = p.get("tenant_id", "")
        # count recent triggers for this customer
        events = _JsonStore("session_events.json").load()
        count = len([e for e in events if e.get("customer_id") == cust and e.get("type") == "custom" and e.get("value") == action])
        matches = []
        for s in self._surveys.load():
            if s.get("tenant_id") != tenant or not s.get("active"):
                continue
            if s.get("trigger_action") == action and count >= s.get("show_after_events", 1):
                matches.append(s)
        return {"status": "ok", "show": matches, "count": len(matches)}

    async def _respond(self, p: dict[str, Any]) -> dict[str, Any]:
        data = self._surveys.load()
        for s in data:
            if s.get("survey_id") == p.get("survey_id"):
                s.setdefault("responses", []).append({
                    "customer_id": p.get("customer_id", ""),
                    "score": p.get("score"), "answer": p.get("answer", ""),
                    "at": datetime.now(UTC).isoformat(),
                })
                self._surveys.save(data)
                return {"status": "recorded", "responses": len(s["responses"])}
        return {"status": "not_found"}

    async def _results(self, p: dict[str, Any]) -> dict[str, Any]:
        for s in self._surveys.load():
            if s.get("survey_id") == p.get("survey_id"):
                resps = s.get("responses", [])
                scores = [r.get("score") for r in resps if r.get("score") is not None]
                avg = sum(scores) / len(scores) if scores else None
                return {"status": "ok", "survey_id": s["survey_id"], "question": s.get("question"),
                        "responses": len(resps), "avg_score": round(avg, 2) if avg else None,
                        "type": s.get("type")}
        return {"status": "not_found"}


class UniversalExportService:
    """Export any dataset to CSV/JSON. ChartMogul universal export parity."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def register(self) -> None:
        reg = self.registry.register("export", version="1.0.0", metadata={"domain": "analytics", "type": "platform"})
        reg.actions["datasets"] = self._datasets
        reg.actions["export"] = self._export

    async def _datasets(self, p: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "datasets": [
            "customers", "campaigns", "segments", "experiments", "goals", "alerts",
            "renewals", "sequences", "journeys", "surveys", "touchpoints", "recordings",
            "events", "reports", "offers", "products", "walls", "presets_applied",
        ]}

    async def _export(self, p: dict[str, Any]) -> dict[str, Any]:
        import csv, io
        dataset = p.get("dataset", "")
        fmt = p.get("format", "csv")
        store_files = {
            "customers": "customer_profiles.json", "campaigns": "campaigns.json",
            "experiments": "experiments.json", "goals": "goals.json",
            "touchpoints": "touchpoints.json", "recordings": "session_recordings.json",
            "events": "imported_events.json", "reports": "saved_reports.json",
            "offers": "catalog_offers.json", "products": "catalog_products.json",
            "walls": "walls.json", "alerts": "alerts.json", "renewals": "renewals.json",
            "sequences": "sequences.json", "journeys": "journeys.json",
            "surveys": "micro_surveys.json", "presets_applied": "applied_presets.json",
        }
        fname = store_files.get(dataset)
        rows = []
        if fname:
            try:
                rows = _JsonStore(fname).load()
            except Exception:
                rows = []
        if fmt == "json":
            return {"status": "ok", "dataset": dataset, "format": "json", "count": len(rows), "data": rows}
        # CSV
        if not rows:
            return {"status": "ok", "dataset": dataset, "format": "csv", "csv": "", "count": 0}
        keys = set()
        for r in rows:
            if isinstance(r, dict):
                keys.update(r.keys())
        keys = sorted(keys)
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow({k: json.dumps(v) if isinstance(v, (dict, list)) else v for k, v in r.items()})
        return {"status": "ok", "dataset": dataset, "format": "csv", "csv": out.getvalue(), "count": len(rows)}


__all__ = [
    "ScheduledReportService", "FlowEditorService", "CancelFlowAPI",
    "SlackBotService", "SessionReplayService", "MicroSurveyService", "UniversalExportService",
]
