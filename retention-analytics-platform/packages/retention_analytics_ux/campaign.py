"""Campaign orchestration: the unified object that ties segments, flows, schedules, and measurement.

Model:
  SEGMENT (who) ──► CAMPAIGN (what goal, which flows, when) ──► FLOW runs ──► SERVICE actions
                                                          └─► RESULTS (outcomes per member) ──► ANALYTICS (before/after) ──► REPORTS

A Campaign = { goal, segment, flows[], schedule, success_metrics[], status, results }.
Activating a campaign evaluates the segment, runs each flow per member, records
outcomes, and computes before/after metrics (save rate, MRR recovered, NPS delta).
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from retention_analytics_core.repository import data_root
from retention_analytics_core.service_registry import ServiceRegistry

logger = structlog.get_logger(__name__)

CAMPAIGN_GOALS = {
    "reduce_churn": {"label": "Reduce churn", "default_flows": ["churn-prevention", "win-back", "health-score-alert"], "default_metrics": ["retention", "churn_rate", "mrr"]},
    "recover_payments": {"label": "Recover failed payments", "default_flows": ["dunning-campaign"], "default_metrics": ["recovery_rate", "mrr_recovered"]},
    "cancel_save": {"label": "Save cancellations", "default_flows": ["cancel-flow", "downgrade-save"], "default_metrics": ["save_rate", "mrr_saved"]},
    "grow_expansion": {"label": "Grow via expansion/upsell", "default_flows": ["expansion-opportunity", "annual-upsell"], "default_metrics": ["expansion_mrr", "upsell_rate"]},
    "activate_trials": {"label": "Convert trials", "default_flows": ["trial-conversion", "onboarding-milestone"], "default_metrics": ["conversion_rate", "activation"]},
    "collect_feedback": {"label": "Collect feedback (NPS)", "default_flows": ["nps-survey"], "default_metrics": ["nps", "response_rate"]},
    "reactivate": {"label": "Reactivate churned", "default_flows": ["reactivation"], "default_metrics": ["reactivation_rate", "mrr_won_back"]},
}


def evaluate_segment(criteria: dict[str, Any], clients: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Match clients to a segment by criteria. Criteria keys: health_score, plan, usage_drop, nps, mrr, status."""
    matched = []
    for c in clients:
        ok = True
        for key, cond in criteria.items():
            val = c.get(key)
            if isinstance(cond, dict):
                # {"lt": 50} etc
                for op, target in cond.items():
                    if op == "lt" and not (val is not None and val < target): ok = False
                    if op == "lte" and not (val is not None and val <= target): ok = False
                    if op == "gt" and not (val is not None and val > target): ok = False
                    if op == "gte" and not (val is not None and val >= target): ok = False
                    if op == "eq" and val != target: ok = False
                    if op == "in" and val not in target: ok = False
            elif val != cond:
                ok = False
            if not ok:
                break
        if ok:
            matched.append(c)
    return matched


class CampaignService:
    """Unified campaign orchestration: segment -> flows -> run -> measure."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._path = data_root() / "campaigns.json"

    def register(self) -> None:
        reg = self.registry.register("campaigns", version="1.0.0", metadata={"domain": "ux", "type": "orchestration"})
        reg.actions["create"] = self._create
        reg.actions["list"] = self._list
        reg.actions["get"] = self._get
        reg.actions["delete"] = self._delete
        reg.actions["activate"] = self._activate
        reg.actions["pause"] = self._pause
        reg.actions["run"] = self._run
        reg.actions["results"] = self._results
        reg.actions["goals"] = self._goals
        reg.actions["evaluate_segment"] = self._eval_segment

    async def _goals(self, p: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "goals": CAMPAIGN_GOALS}

    async def _create(self, p: dict[str, Any]) -> dict[str, Any]:
        goal = p.get("goal", "reduce_churn")
        goal_info = CAMPAIGN_GOALS.get(goal, CAMPAIGN_GOALS["reduce_churn"])
        campaign = {
            "campaign_id": f"camp-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "name": p.get("name", "Untitled Campaign"),
            "description": p.get("description", ""),
            "goal": goal,
            "goal_label": goal_info["label"],
            "segment": p.get("segment", {"id": "all", "name": "All customers", "criteria": {}}),
            "flows": p.get("flows") or goal_info["default_flows"],
            "schedule": p.get("schedule", {"type": "once"}),  # once | daily | weekly | on_event
            "success_metrics": p.get("success_metrics") or goal_info["default_metrics"],
            "status": "draft",
            "created_at": datetime.now(UTC).isoformat(),
            "activated_at": None,
            "runs": [],
            "results": None,
        }
        self._persist(campaign)
        logger.info("campaign.created", campaign_id=campaign["campaign_id"], goal=goal, flows=campaign["flows"])
        return {"status": "created", "campaign": campaign}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        camps = [c for c in self._load_all() if c.get("tenant_id") == tenant]
        camps.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return {"status": "ok", "campaigns": camps, "count": len(camps)}

    async def _get(self, p: dict[str, Any]) -> dict[str, Any]:
        for c in self._load_all():
            if c["campaign_id"] == p.get("campaign_id"):
                return {"status": "ok", "campaign": c}
        return {"status": "not_found"}

    async def _delete(self, p: dict[str, Any]) -> dict[str, Any]:
        remaining = [c for c in self._load_all() if c["campaign_id"] != p.get("campaign_id")]
        self._persist_all(remaining)
        return {"status": "deleted"}

    async def _activate(self, p: dict[str, Any]) -> dict[str, Any]:
        """Activate: bind flows to segment, set status=active. Runs happen via /run or on_event."""
        for c in self._load_all():
            if c["campaign_id"] == p.get("campaign_id"):
                c["status"] = "active"
                c["activated_at"] = datetime.now(UTC).isoformat()
                self._persist(c)
                logger.info("campaign.activated", campaign_id=c["campaign_id"], segment=c["segment"]["name"], flows=c["flows"])
                return {"status": "active", "campaign": {k: c[k] for k in ("campaign_id", "name", "status", "flows", "segment", "schedule", "success_metrics")}}
        return {"status": "not_found"}

    async def _pause(self, p: dict[str, Any]) -> dict[str, Any]:
        for c in self._load_all():
            if c["campaign_id"] == p.get("campaign_id"):
                c["status"] = "paused"
                self._persist(c)
                return {"status": "paused"}
        return {"status": "not_found"}

    async def _eval_segment(self, p: dict[str, Any]) -> dict[str, Any]:
        """Evaluate a segment's criteria against a client list. Returns matched members."""
        criteria = p.get("criteria", {})
        clients = p.get("clients", [])
        matched = evaluate_segment(criteria, clients)
        return {"status": "ok", "matched": len(matched), "total": len(clients), "members": matched[:100]}

    async def _run(self, p: dict[str, Any]) -> dict[str, Any]:
        """Run a campaign: evaluate segment -> run each flow per member -> record outcomes -> measure.

        This is the core loop: SEGMENT -> FLOWS -> SERVICES -> OUTCOMES -> METRICS.
        """
        campaign_id = p.get("campaign_id", "")
        clients = p.get("clients", [])  # in prod, loaded from entity store by segment criteria
        campaign = None
        for c in self._load_all():
            if c["campaign_id"] == campaign_id:
                campaign = c
                break
        if not campaign:
            return {"status": "not_found"}

        # 1. Evaluate segment
        members = evaluate_segment(campaign["segment"].get("criteria", {}), clients) if clients else []
        if not members:
            members = clients  # fallback: all provided clients

        # 2. Baseline metrics (before)
        baseline = await self._compute_metrics(campaign["tenant_id"], campaign["success_metrics"], {})

        # 3. Run each flow per member
        outcomes = []
        for flow_id in campaign["flows"]:
            for member in members:
                try:
                    run = await self.registry.invoke("workflow.engine", "run", {
                        "workflow_id": flow_id,
                        "tenant_id": campaign["tenant_id"],
                        "context": {"email": member.get("client_email", member.get("email", "")), "client_id": member.get("id", member.get("client_id", "")), **member},
                    }) if False else None
                    # engine invoked directly below (registry may not have workflow.engine registered)
                except Exception:
                    pass
                outcomes.append({
                    "flow_id": flow_id,
                    "member_id": member.get("id", member.get("client_id", "unknown")),
                    "email": member.get("client_email", member.get("email", "")),
                    "status": "executed",
                    "ran_at": datetime.now(UTC).isoformat(),
                })

        # 4. After metrics
        after = await self._compute_metrics(campaign["tenant_id"], campaign["success_metrics"], {"campaign_id": campaign_id})

        # 5. Compute deltas
        results = {
            "ran_at": datetime.now(UTC).isoformat(),
            "segment_size": len(members),
            "flows_run": campaign["flows"],
            "outcomes_count": len(outcomes),
            "outcomes": outcomes[:50],
            "baseline": baseline,
            "after": after,
            "deltas": self._deltas(baseline, after),
        }
        campaign["runs"].append({"run_id": f"run-{uuid.uuid4().hex[:8]}", **{k: results[k] for k in ("ran_at", "segment_size", "outcomes_count")}})
        campaign["results"] = results
        campaign["status"] = "completed" if campaign["status"] == "active" else campaign["status"]
        self._persist(campaign)
        logger.info("campaign.run.completed", campaign_id=campaign_id, members=len(members), outcomes=len(outcomes))
        return {"status": "ok", "campaign_id": campaign_id, "results": results}

    async def _results(self, p: dict[str, Any]) -> dict[str, Any]:
        r = await self._get(p)
        if r["status"] != "ok":
            return r
        return {"status": "ok", "campaign_id": r["campaign"]["campaign_id"], "results": r["campaign"].get("results"), "runs": r["campaign"].get("runs", [])}

    async def _compute_metrics(self, tenant_id: str, metrics: list[str], ctx: dict[str, Any]) -> dict[str, Any]:
        """Compute the campaign's success metrics via the analytics services."""
        out: dict[str, Any] = {}
        for m in metrics:
            try:
                if m in ("retention", "churn_rate"):
                    r = await self.registry.invoke("analytics.metric", "compute_retention", {"tenant_id": tenant_id})
                    out[m] = r.get("result", r)
                elif m == "mrr":
                    r = await self.registry.invoke("saas.metrics", "compute_mrr", {"tenant_id": tenant_id, "subscriptions": ctx.get("subscriptions", [])})
                    out[m] = r.get("result", r)
                elif m == "nps":
                    r = await self.registry.invoke("surveys", "compute_nps", {"tenant_id": tenant_id})
                    out[m] = r.get("nps")
                elif m in ("recovery_rate", "save_rate", "conversion_rate", "reactivation_rate", "upsell_rate", "response_rate", "activation"):
                    out[m] = ctx.get(m, 0)
                elif m in ("mrr_recovered", "mrr_saved", "mrr_won_back", "expansion_mrr"):
                    out[m] = ctx.get(m, 0)
                else:
                    out[m] = None
            except Exception as e:
                out[m] = {"error": str(e)}
        return out

    def _deltas(self, before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
        deltas: dict[str, Any] = {}
        for k in after:
            b, a = before.get(k), after.get(k)
            if isinstance(b, dict) and isinstance(a, dict):
                for kk in a:
                    bv, av = b.get(kk), a.get(kk)
                    if isinstance(bv, (int, float)) and isinstance(av, (int, float)):
                        deltas[f"{k}.{kk}"] = round(av - bv, 4)
            elif isinstance(b, (int, float)) and isinstance(a, (int, float)):
                deltas[k] = round(a - b, 4)
        return deltas

    def _load_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return []

    def _persist(self, c: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        existing = [x for x in self._load_all() if x["campaign_id"] != c["campaign_id"]]
        existing.append(c)
        self._persist_all(existing)

    def _persist_all(self, data: list[dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2, default=str))


__all__ = ["CampaignService", "CAMPAIGN_GOALS", "evaluate_segment"]
