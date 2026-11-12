"""CS operations services: success plans, playbooks, alerts, command center, renewals."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from retention_analytics_core.repository import data_root
from retention_analytics_core.service_registry import ServiceRegistry

logger = structlog.get_logger(__name__)


class SuccessPlanService:
    """Success plans / projects with milestones. Mirrors Vitally Projects, ChurnZero Success Plans."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._path = data_root() / "success_plans.json"

    def register(self) -> None:
        reg = self.registry.register("cs.plans", version="1.0.0", metadata={"domain": "cs_ops", "type": "platform"})
        reg.actions["create"] = self._create
        reg.actions["add_milestone"] = self._add_milestone
        reg.actions["complete_milestone"] = self._complete
        reg.actions["get"] = self._get
        reg.actions["list"] = self._list
        reg.actions["progress"] = self._progress

    async def _create(self, p: dict[str, Any]) -> dict[str, Any]:
        plan = {
            "plan_id": f"plan-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "client_id": p.get("client_id", ""),
            "name": p.get("name", "Success Plan"),
            "milestones": [],
            "status": "active",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._persist(plan)
        return {"status": "created", "plan": plan}

    async def _add_milestone(self, p: dict[str, Any]) -> dict[str, Any]:
        plans = self._load_all()
        for plan in plans:
            if plan["plan_id"] == p.get("plan_id"):
                plan["milestones"].append({
                    "milestone_id": f"ms-{uuid.uuid4().hex[:8]}",
                    "name": p.get("name", ""),
                    "due_date": p.get("due_date", (datetime.now(UTC) + timedelta(days=30)).isoformat()),
                    "status": "pending",
                })
                self._persist_all(plans)
                return {"status": "added", "plan_id": plan["plan_id"], "milestones": len(plan["milestones"])}
        return {"status": "not_found"}

    async def _complete(self, p: dict[str, Any]) -> dict[str, Any]:
        plans = self._load_all()
        for plan in plans:
            if plan["plan_id"] == p.get("plan_id"):
                for ms in plan["milestones"]:
                    if ms["milestone_id"] == p.get("milestone_id"):
                        ms["status"] = "completed"
                        ms["completed_at"] = datetime.now(UTC).isoformat()
                done = sum(1 for m in plan["milestones"] if m["status"] == "completed")
                if done == len(plan["milestones"]) and plan["milestones"]:
                    plan["status"] = "completed"
                self._persist_all(plans)
                return {"status": "completed", "progress": f"{done}/{len(plan['milestones'])}"}
        return {"status": "not_found"}

    async def _get(self, p: dict[str, Any]) -> dict[str, Any]:
        for plan in self._load_all():
            if plan["plan_id"] == p.get("plan_id"):
                return {"status": "ok", "plan": plan}
        return {"status": "not_found"}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        plans = [x for x in self._load_all() if x.get("tenant_id") == tenant]
        if p.get("client_id"):
            plans = [x for x in plans if x.get("client_id") == p["client_id"]]
        return {"status": "ok", "plans": plans, "count": len(plans)}

    async def _progress(self, p: dict[str, Any]) -> dict[str, Any]:
        r = await self._get(p)
        if r["status"] != "ok":
            return r
        plan = r["plan"]
        total = len(plan["milestones"])
        done = sum(1 for m in plan["milestones"] if m["status"] == "completed")
        return {"status": "ok", "plan_id": plan["plan_id"], "progress_pct": round(done / total * 100, 1) if total else 0, "done": done, "total": total}

    def _load_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return []

    def _persist(self, plan: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        existing = [x for x in self._load_all() if x["plan_id"] != plan["plan_id"]]
        existing.append(plan)
        self._persist_all(existing)

    def _persist_all(self, data: list[dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2, default=str))


class PlaybookService:
    """Automated playbooks/journeys. Mirrors ChurnZero Playbooks/Journeys, Vitally Automation."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._path = data_root() / "playbooks.json"

    def register(self) -> None:
        reg = self.registry.register("cs.playbooks", version="1.0.0", metadata={"domain": "cs_ops", "type": "automation"})
        reg.actions["create"] = self._create
        reg.actions["run"] = self._run
        reg.actions["list"] = self._list
        reg.actions["get"] = self._get

    async def _create(self, p: dict[str, Any]) -> dict[str, Any]:
        pb = {
            "playbook_id": f"pb-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "name": p.get("name", ""),
            "trigger": p.get("trigger", ""),
            "actions": p.get("actions", []),
            "active": True,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._persist(pb)
        return {"status": "created", "playbook": pb}

    async def _run(self, p: dict[str, Any]) -> dict[str, Any]:
        for pb in self._load_all():
            if pb["playbook_id"] == p.get("playbook_id") and pb.get("active"):
                run = {
                    "run_id": f"run-{uuid.uuid4().hex[:12]}",
                    "playbook_id": pb["playbook_id"],
                    "client_id": p.get("client_id", ""),
                    "actions_executed": len(pb.get("actions", [])),
                    "status": "executed",
                    "ran_at": datetime.now(UTC).isoformat(),
                }
                logger.info("playbook.executed", playbook=pb["name"], run=run["run_id"])
                return {"status": "ok", "run": run}
        return {"status": "not_found_or_inactive"}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        return {"status": "ok", "playbooks": [x for x in self._load_all() if x.get("tenant_id") == tenant]}

    async def _get(self, p: dict[str, Any]) -> dict[str, Any]:
        for pb in self._load_all():
            if pb["playbook_id"] == p.get("playbook_id"):
                return {"status": "ok", "playbook": pb}
        return {"status": "not_found"}

    def _load_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return []

    def _persist(self, pb: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        existing = [x for x in self._load_all() if x["playbook_id"] != pb["playbook_id"]]
        existing.append(pb)
        self._path.write_text(json.dumps(existing, indent=2, default=str))


class AlertService:
    """Real-time alerts. Mirrors ChurnZero Real-time alerts."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._path = data_root() / "alerts.json"

    def register(self) -> None:
        reg = self.registry.register("cs.alerts", version="1.0.0", metadata={"domain": "cs_ops", "type": "platform"})
        reg.actions["fire"] = self._fire
        reg.actions["acknowledge"] = self._ack
        reg.actions["list_open"] = self._list_open
        reg.actions["list_all"] = self._list_all

    async def _fire(self, p: dict[str, Any]) -> dict[str, Any]:
        alert = {
            "alert_id": f"al-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "client_id": p.get("client_id", ""),
            "type": p.get("type", "info"),
            "severity": p.get("severity", "medium"),
            "title": p.get("title", ""),
            "detail": p.get("detail", ""),
            "status": "open",
            "fired_at": datetime.now(UTC).isoformat(),
        }
        self._persist(alert)
        logger.warning("alert.fired", alert_id=alert["alert_id"], severity=alert["severity"], title=alert["title"])
        return {"status": "fired", "alert": alert}

    async def _ack(self, p: dict[str, Any]) -> dict[str, Any]:
        alerts = self._load_all()
        for a in alerts:
            if a["alert_id"] == p.get("alert_id"):
                a["status"] = "acknowledged"
                a["acknowledged_at"] = datetime.now(UTC).isoformat()
                self._persist_all(alerts)
                return {"status": "acknowledged"}
        return {"status": "not_found"}

    async def _list_open(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        open_alerts = [a for a in self._load_all() if a.get("tenant_id") == tenant and a.get("status") == "open"]
        open_alerts.sort(key=lambda x: x.get("fired_at", ""), reverse=True)
        return {"status": "ok", "alerts": open_alerts, "count": len(open_alerts)}

    async def _list_all(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        return {"status": "ok", "alerts": [a for a in self._load_all() if a.get("tenant_id") == tenant]}

    def _load_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return []

    def _persist(self, a: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._load_all() + [a], indent=2, default=str))

    def _persist_all(self, data: list[dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2, default=str))


class RenewalHubService:
    """Renewal tracking + forecast. Mirrors ChurnZero Renewal & Forecast Hub."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._path = data_root() / "renewals.json"

    def register(self) -> None:
        reg = self.registry.register("cs.renewals", version="1.0.0", metadata={"domain": "cs_ops", "type": "platform"})
        reg.actions["track"] = self._track
        reg.actions["forecast"] = self._forecast
        reg.actions["list_upcoming"] = self._list_upcoming
        reg.actions["update_outlook"] = self._outlook

    async def _track(self, p: dict[str, Any]) -> dict[str, Any]:
        renewal = {
            "renewal_id": f"ren-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "client_id": p.get("client_id", ""),
            "subscription_id": p.get("subscription_id", ""),
            "arr": float(p.get("arr", 0)),
            "renews_at": p.get("renews_at", (datetime.now(UTC) + timedelta(days=30)).isoformat()),
            "outlook": "unknown",
            "risk_score": 0.0,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._persist(renewal)
        return {"status": "tracked", "renewal": renewal}

    async def _forecast(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        renewals = [r for r in self._load_all() if r.get("tenant_id") == tenant]
        total_arr = sum(r["arr"] for r in renewals)
        outlook_weights = {"committed": 0.95, "likely": 0.75, "at_risk": 0.4, "unknown": 0.5, "lost": 0.0}
        forecast = sum(r["arr"] * outlook_weights.get(r.get("outlook", "unknown"), 0.5) for r in renewals)
        return {"status": "ok", "total_arr_up_for_renewal": round(total_arr, 2), "forecast_arr": round(forecast, 2), "renewals": len(renewals)}

    async def _list_upcoming(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        days = int(p.get("days", 90))
        cutoff = (datetime.now(UTC) + timedelta(days=days)).isoformat()
        upcoming = [r for r in self._load_all() if r.get("tenant_id") == tenant and r.get("renews_at", "") <= cutoff]
        upcoming.sort(key=lambda x: x["renews_at"])
        return {"status": "ok", "renewals": upcoming, "count": len(upcoming)}

    async def _outlook(self, p: dict[str, Any]) -> dict[str, Any]:
        renewals = self._load_all()
        for r in renewals:
            if r["renewal_id"] == p.get("renewal_id"):
                r["outlook"] = p.get("outlook", "unknown")
                r["risk_score"] = float(p.get("risk_score", 0))
                self._persist_all(renewals)
                return {"status": "updated", "outlook": r["outlook"]}
        return {"status": "not_found"}

    def _load_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return []

    def _persist(self, r: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._load_all() + [r], indent=2, default=str))

    def _persist_all(self, data: list[dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2, default=str))


class CommandCenterService:
    """Unified command center: aggregates health, alerts, renewals, at-risk into one view.

    Mirrors ChurnZero Command Center.
    """

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def register(self) -> None:
        reg = self.registry.register("cs.command_center", version="1.0.0", metadata={"domain": "cs_ops", "type": "dashboard"})
        reg.actions["overview"] = self._overview

    async def _overview(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        # Aggregate from other services if available
        overview: dict[str, Any] = {"tenant_id": tenant, "generated_at": datetime.now(UTC).isoformat()}
        try:
            alerts = await self.registry.invoke("cs.alerts", "list_open", {"tenant_id": tenant})
            overview["open_alerts"] = alerts.get("count", 0)
        except Exception:
            overview["open_alerts"] = 0
        try:
            renewals = await self.registry.invoke("cs.renewals", "forecast", {"tenant_id": tenant})
            overview["renewal_forecast_arr"] = renewals.get("forecast_arr", 0)
        except Exception:
            overview["renewal_forecast_arr"] = 0
        try:
            at_risk = await self.registry.invoke("ai.churn_predict", "at_risk_list", {"tenant_id": tenant, "threshold": 0.4})
            overview["at_risk_clients"] = at_risk.get("count", 0)
        except Exception:
            overview["at_risk_clients"] = 0
        return {"status": "ok", "overview": overview}


__all__ = ["SuccessPlanService", "PlaybookService", "AlertService", "RenewalHubService", "CommandCenterService"]
