"""Close-the-loop processes: NPS follow-up, experiment auto-promotion,
anomaly->incident, timed win-back sequences."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced.customer_intel import _JsonStore

logger = structlog.get_logger(__name__)

WINBACK_SCHEDULE = [7, 30, 90]  # days after churn


class NPSLoopService:
    """Close the loop on survey responses: detractor -> urgent call task,
    passive -> product feedback ask, promoter -> referral ask."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._responses = _JsonStore("nps_responses.json")

    def register(self) -> None:
        reg = self.registry.register("nps.loop", version="1.0.0", metadata={"domain": "feedback", "type": "automation"})
        reg.actions["handle_response"] = self._handle
        reg.actions["list_actions"] = self._list

    async def _handle(self, p: dict[str, Any]) -> dict[str, Any]:
        score = int(p.get("score", 5))
        cid = p.get("client_id", "")
        email = p.get("customer_email", "")
        tenant = p.get("tenant_id", "")
        if score <= 6:
            kind = "detractor"
            action = {"type": "call_task", "priority": "urgent",
                      "body": f"Detractor (score {score}) — call within 24h: {p.get('comment', '')}"}
        elif score <= 8:
            kind = "passive"
            action = {"type": "feedback_ask", "priority": "normal",
                      "body": f"Passive (score {score}) — ask what would make it a 9-10"}
        else:
            kind = "promoter"
            action = {"type": "referral_ask", "priority": "low",
                      "body": f"Promoter (score {score}) — ask for a referral (reward $50)"}
        rec = {"id": f"npsr-{uuid.uuid4().hex[:12]}", "tenant_id": tenant, "client_id": cid,
               "customer_email": email, "score": score, "kind": kind, "action": action,
               "comment": p.get("comment", ""), "at": datetime.now(UTC).isoformat(), "handled": False}
        self._responses.upsert("id", rec)
        logger.info("nps.loop.action", kind=kind, client_id=cid)
        return {"status": "ok", "kind": kind, "action": action, "id": rec["id"]}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        rows = [r for r in self._responses.load() if r.get("tenant_id") == tenant]
        return {"status": "ok", "responses": rows, "count": len(rows)}


class ExperimentAutoPromoteService:
    """Auto-promote A/B winners when the result reaches statistical significance."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._decisions = _JsonStore("experiment_decisions.json")

    def register(self) -> None:
        reg = self.registry.register("experiments.auto", version="1.0.0", metadata={"domain": "experiments", "type": "automation"})
        reg.actions["evaluate"] = self._evaluate
        reg.actions["list_decisions"] = self._list

    async def _evaluate(self, p: dict[str, Any]) -> dict[str, Any]:
        """Evaluate an experiment: if the winner's lift is significant (z-test approx), record promotion."""
        eid = p.get("experiment_id", "")
        results = p.get("results", {})  # {variant_id: {sent, converted}}
        rows = []
        for vid, r in results.items():
            sent = int(r.get("sent", 0)); conv = int(r.get("converted", 0))
            rows.append((vid, sent, conv, conv / sent if sent else 0))
        if len(rows) < 2:
            return {"status": "insufficient_data"}
        rows.sort(key=lambda x: x[3], reverse=True)
        (wid, wsent, wconv, wrate), (cid, csent, cconv, crate) = rows[0], rows[1]
        if csent == 0 or wsent == 0 or crate == 0:
            return {"status": "insufficient_data"}
        # pooled proportion z-test
        p_pool = (wconv + cconv) / (wsent + csent)
        se = (p_pool * (1 - p_pool) * (1 / wsent + 1 / csent)) ** 0.5
        z = (wrate - crate) / se if se else 0
        significant = z >= 1.96  # 95%
        lift = (wrate - crate) / crate * 100 if crate else 0
        decision = None
        if significant and lift > 5:
            decision = {"decision_id": f"dec-{uuid.uuid4().hex[:12]}", "experiment_id": eid,
                        "winner": wid, "lift_pct": round(lift, 1), "z": round(z, 2),
                        "action": "promote", "decided_at": datetime.now(UTC).isoformat()}
            self._decisions.upsert("decision_id", decision)
        return {"status": "ok", "experiment_id": eid, "winner": wid, "lift_pct": round(lift, 1),
                "z": round(z, 2), "significant": significant, "decision": decision}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "decisions": self._decisions.load()}


class IncidentService:
    """Metric anomaly -> incident: record, page team, draft customer comms."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._incidents = _JsonStore("incidents.json")

    def register(self) -> None:
        reg = self.registry.register("incidents", version="1.0.0", metadata={"domain": "ops", "type": "platform"})
        reg.actions["create_from_anomaly"] = self._create
        reg.actions["list"] = self._list
        reg.actions["update_status"] = self._status
        reg.actions["comms_draft"] = self._comms

    async def _create(self, p: dict[str, Any]) -> dict[str, Any]:
        anomaly = p.get("anomaly", {})
        inc = {
            "incident_id": f"inc-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "metric": p.get("metric", ""),
            "severity": anomaly.get("severity", "warning"),
            "direction": anomaly.get("direction", ""),
            "deviation_pct": anomaly.get("deviation_pct", 0),
            "status": "open",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._incidents.upsert("incident_id", inc)
        logger.warning("incident.created", incident_id=inc["incident_id"], metric=inc["metric"], severity=inc["severity"])
        return {"status": "created", "incident": inc}

    async def _comms(self, p: dict[str, Any]) -> dict[str, Any]:
        """Draft customer-facing comms for an incident."""
        inc = next((i for i in self._incidents.load() if i["incident_id"] == p.get("incident_id")), None)
        if not inc:
            return {"status": "not_found"}
        draft = (
            f"Subject: Update on {inc['metric']}\n\n"
            f"We detected a {inc['direction']} of {inc['deviation_pct']}% in {inc['metric']} "
            f"(severity: {inc['severity']}). Our team is actively investigating. "
            f"Status page: /status/{inc['incident_id']}. We will update within 1 hour."
        )
        inc["comms_draft"] = draft
        self._incidents.save(self._incidents.load())
        return {"status": "ok", "incident_id": inc["incident_id"], "draft": draft}

    async def _status(self, p: dict[str, Any]) -> dict[str, Any]:
        data = self._incidents.load()
        for i in data:
            if i["incident_id"] == p.get("incident_id"):
                i["status"] = p.get("status", "open")
                i["updated_at"] = datetime.now(UTC).isoformat()
                self._incidents.save(data)
                return {"status": "ok", "incident": i}
        return {"status": "not_found"}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        rows = [i for i in self._incidents.load() if i.get("tenant_id") == tenant]
        rows.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return {"status": "ok", "incidents": rows, "count": len(rows)}


class WinbackTimingService:
    """Churned-customer win-back at 7/30/90 days with per-customer optimal send time."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._winbacks = _JsonStore("winback_schedule.json")

    def register(self) -> None:
        reg = self.registry.register("winback.timing", version="1.0.0", metadata={"domain": "retention", "type": "automation"})
        reg.actions["schedule"] = self._schedule
        reg.actions["due"] = self._due
        reg.actions["list"] = self._list

    async def _schedule(self, p: dict[str, Any]) -> dict[str, Any]:
        churned_at = p.get("churned_at", datetime.now(UTC).isoformat())
        rec = {
            "winback_id": f"wb-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "customer_id": p.get("customer_id", ""),
            "email": p.get("email", ""),
            "churned_at": churned_at,
            "touches": [{"day": d, "sent": False, "at": None} for d in WINBACK_SCHEDULE],
            "optimal_hour": int(p.get("optimal_hour", 10)),  # predictive send time
        }
        self._winbacks.upsert("winback_id", rec)
        return {"status": "scheduled", "winback": rec}

    async def _due(self, p: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(UTC)
        data = self._winbacks.load()
        due = []
        for w in data:
            churned = datetime.fromisoformat(w["churned_at"].replace("Z", "+00:00"))
            for t in w["touches"]:
                if t["sent"]:
                    continue
                due_at = churned + timedelta(days=t["day"])
                if now >= due_at:
                    t["sent"] = True
                    t["at"] = now.isoformat()
                    due.append({"winback_id": w["winback_id"], "customer_id": w["customer_id"],
                                "email": w["email"], "day": t["day"], "optimal_hour": w["optimal_hour"]})
        self._winbacks.save(data)
        return {"status": "ok", "due": due, "count": len(due)}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        return {"status": "ok", "winbacks": [w for w in self._winbacks.load() if w.get("tenant_id") == tenant]}


__all__ = ["NPSLoopService", "ExperimentAutoPromoteService", "IncidentService", "WinbackTimingService", "WINBACK_SCHEDULE"]
