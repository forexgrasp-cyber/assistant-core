"""Advanced customer analysis: computed segmentation predicates, next-best-action,
tailored campaign content, and the automatic-approach loop.

Everything is universal — it works on whatever fields the customer records
carry (plan, MRR, LTV, health, next service due, churn risk, RFM segment).
"""

from __future__ import annotations

import json
import re
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from retention_analytics_core.repository import data_root
from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced.customer_intel import _JsonStore

logger = structlog.get_logger(__name__)

# Computed fields the segmentation engine can filter on, derived from records.
COMPUTED_FIELDS = {
    "days_until_due": "Days until the next service/subscription is due (negative = overdue)",
    "due_soon": "Service or subscription due within 7 days",
    "overdue": "Service or subscription already overdue",
    "health_tier": "critical | at_risk | watch | healthy",
    "ltv_tier": "champion | high | mid | low (by lifetime value)",
    "churn_risk_tier": "critical | high | medium | low",
    "mrr_band": "enterprise | mid | small | micro (by monthly value)",
    "rfm_segment": "RFM segment from shared.predictive.churn",
    "renewal_days": "Days until renewal",
    "tenure_months": "Months since the customer was created",
    "value_rank": "Rank by lifetime value inside the tenant (1 = highest)",
}

# Which fields are numeric vs categorical (for the predicate builder UI).
FIELD_TYPES = {
    "mrr": "number", "ltv": "number", "health_score": "number", "days_until_due": "number",
    "renewal_days": "number", "tenure_months": "number", "value_rank": "number",
    "plan": "text", "service_name": "text", "email": "text", "name": "text",
    "health_tier": "enum", "ltv_tier": "enum", "churn_risk_tier": "enum",
    "mrr_band": "enum", "rfm_segment": "enum", "due_soon": "bool", "overdue": "bool",
}

LTV_TIERS = [(5000, "champion"), (1000, "high"), (250, "mid"), (0, "low")]
MRR_BANDS = [(1000, "enterprise"), (250, "mid"), (50, "small"), (0, "micro")]


def _mrr_band(mrr: float) -> str:
    for threshold, label in MRR_BANDS:
        if mrr >= threshold:
            return label
    return "micro"


def _ltv_tier(ltv: float) -> str:
    for threshold, label in LTV_TIERS:
        if ltv >= threshold:
            return label
    return "low"


def _health_tier(score: float) -> str:
    if score < 30:
        return "critical"
    if score < 50:
        return "at_risk"
    if score < 70:
        return "watch"
    return "healthy"


class AdvancedSegmentation:
    """Filter customer records on raw AND computed fields, preview members, save as a segment."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._segments = _JsonStore("advanced_segments.json")

    def register(self) -> None:
        reg = self.registry.register("segmentation.advanced", version="1.0.0", metadata={"domain": "customers", "type": "analytics"})
        reg.actions["fields"] = self._fields
        reg.actions["preview"] = self._preview
        reg.actions["save"] = self._save
        reg.actions["list"] = self._list
        reg.actions["delete"] = self._delete
        reg.actions["profiles"] = self._profiles

    async def _fields(self, p: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "computed": COMPUTED_FIELDS, "types": FIELD_TYPES}

    async def _profiles(self, p: dict[str, Any]) -> dict[str, Any]:
        """Customer records with computed fields attached (the analysis surface)."""
        tenant = p.get("tenant_id", "")
        rows = await self._enrich_records(tenant, p.get("include_churn_risk", True))
        return {"status": "ok", "profiles": rows, "count": len(rows)}

    async def _enrich_records(self, tenant: str, with_risk: bool = True) -> list[dict[str, Any]]:
        profiles = [x for x in _JsonStore("customer_profiles.json").load() if x.get("tenant_id") == tenant]
        # churn risk from the AI engine, keyed by client id
        risk_by_client: dict[str, dict[str, Any]] = {}
        if with_risk:
            try:
                r = await self.registry.invoke("ai.churn_ml", "score", {"tenant_id": tenant, "client_id": "*"})
                if r.get("result"):
                    risk_by_client[r["result"]["client_id"]] = r["result"]
            except Exception:
                pass
        # health scores
        health_by_client: dict[str, dict[str, Any]] = {}
        try:
            r = await self.registry.invoke("health.engine", "list", {"tenant_id": tenant})
            for h in r.get("scores", []):
                health_by_client[h.get("client_id", "")] = h
        except Exception:
            pass
        now = datetime.now(UTC)
        out = []
        for prof in profiles:
            row = dict(prof)
            mrr = float(row.get("mrr") or 0)
            ltv = float(row.get("ltv") or 0)
            health = float(row.get("health_score") or 100)
            due = row.get("days_until_due")
            row["mrr_band"] = _mrr_band(mrr)
            row["ltv_tier"] = _ltv_tier(ltv)
            row["health_tier"] = _health_tier(health)
            row["due_soon"] = bool(due is not None and 0 <= due <= 7)
            row["overdue"] = bool(due is not None and due < 0)
            created = row.get("created_at")
            if created:
                try:
                    c = datetime.fromisoformat(str(created).replace("Z", "+00:00"))
                    row["tenure_months"] = max(0, (now - c).days // 30)
                except Exception:
                    row["tenure_months"] = 0
            else:
                row["tenure_months"] = 0
            h = health_by_client.get(row.get("id", ""))
            if h:
                row["health_score"] = h.get("score", health)
                row["health_tier"] = h.get("tier", row["health_tier"])
            risk = risk_by_client.get(row.get("id", ""))
            if risk:
                row["churn_risk"] = risk.get("blended_risk")
                row["churn_risk_tier"] = risk.get("risk_level")
            else:
                row.setdefault("churn_risk", None)
                row.setdefault("churn_risk_tier", "unknown")
            out.append(row)
        # value rank
        ordered = sorted(out, key=lambda x: float(x.get("ltv") or 0), reverse=True)
        for i, row in enumerate(ordered, 1):
            row["value_rank"] = i
        return out

    def _matches(self, row: dict[str, Any], criteria: dict[str, Any]) -> bool:
        for field, cond in criteria.items():
            val = row.get(field)
            if isinstance(cond, dict):
                for op, target in cond.items():
                    if op == "lt" and not (isinstance(val, (int, float)) and val < target):
                        return False
                    if op == "lte" and not (isinstance(val, (int, float)) and val <= target):
                        return False
                    if op == "gt" and not (isinstance(val, (int, float)) and val > target):
                        return False
                    if op == "gte" and not (isinstance(val, (int, float)) and val >= target):
                        return False
                    if op == "eq" and val != target:
                        return False
                    if op == "ne" and val == target:
                        return False
                    if op == "in" and val not in target:
                        return False
                    if op == "not_in" and val in target:
                        return False
                    if op == "contains" and str(target).lower() not in str(val or "").lower():
                        return False
                    if op == "is_true" and not bool(val):
                        return False
                    if op == "is_false" and bool(val):
                        return False
            elif isinstance(cond, list):
                if val not in cond:
                    return False
            else:
                if val != cond:
                    return False
        return True

    async def _preview(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        criteria = p.get("criteria", {})
        limit = int(p.get("limit", 100))
        rows = await self._enrich_records(tenant, p.get("include_churn_risk", True))
        matched = [r for r in rows if self._matches(r, criteria)]
        # aggregate profile of the match
        total_mrr = sum(float(r.get("mrr") or 0) for r in matched)
        total_ltv = sum(float(r.get("ltv") or 0) for r in matched)
        avg_health = (sum(float(r.get("health_score") or 0) for r in matched) / len(matched)) if matched else 0
        due_soon = sum(1 for r in matched if r.get("due_soon"))
        overdue = sum(1 for r in matched if r.get("overdue"))
        return {
            "status": "ok",
            "total_customers": len(rows),
            "matched": len(matched),
            "criteria": criteria,
            "members": matched[:limit],
            "aggregate": {
                "total_mrr": round(total_mrr, 2),
                "total_ltv": round(total_ltv, 2),
                "avg_health": round(avg_health, 1),
                "due_soon": due_soon,
                "overdue": overdue,
                "mrr_at_risk": round(sum(float(r.get("mrr") or 0) for r in matched
                                         if r.get("churn_risk_tier") in ("critical", "high")), 2),
            },
        }

    async def _save(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        seg = {
            "segment_id": p.get("segment_id") or f"seg-{uuid.uuid4().hex[:12]}",
            "tenant_id": tenant,
            "name": p.get("name", "Segment"),
            "criteria": p.get("criteria", {}),
            "computed_on": p.get("computed_on", ["days_until_due", "health_tier", "ltv_tier", "churn_risk_tier", "mrr_band"]),
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._segments.upsert("segment_id", seg)
        logger.info("segment.saved", segment_id=seg["segment_id"], name=seg["name"])
        return {"status": "saved", "segment": seg}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        rows = [s for s in self._segments.load() if s.get("tenant_id") == tenant]
        return {"status": "ok", "segments": rows, "count": len(rows)}

    async def _delete(self, p: dict[str, Any]) -> dict[str, Any]:
        self._segments.save([s for s in self._segments.load() if s.get("segment_id") != p.get("segment_id")])
        return {"status": "deleted"}


class NextBestActionService:
    """Per-customer recommended action with reason and priority."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def register(self) -> None:
        reg = self.registry.register("customers.next_best_action", version="1.0.0", metadata={"domain": "customers", "type": "ai"})
        reg.actions["recommend"] = self._recommend
        reg.actions["recommend_all"] = self._all

    def _decide(self, row: dict[str, Any]) -> dict[str, Any]:
        due = row.get("days_until_due")
        overdue = bool(row.get("overdue"))
        due_soon = bool(row.get("due_soon"))
        health = float(row.get("health_score") or 100)
        risk = row.get("churn_risk") or 0
        risk_tier = row.get("churn_risk_tier", "unknown")
        mrr = float(row.get("mrr") or 0)
        ltv = float(row.get("ltv") or 0)

        if overdue:
            return {"action": "service_recovery", "priority": 1, "channel": "email+sms",
                    "reason": f"{row.get('service_name') or 'Service'} was due {abs(due)} days ago",
                    "flow": "service-overdue", "offer": "priority booking"}
        if due_soon:
            return {"action": "service_reminder", "priority": 2, "channel": "email+sms",
                    "reason": f"{row.get('service_name') or 'Service'} due in {due} days",
                    "flow": "service-due-reminder", "offer": "book now"}
        if risk_tier in ("critical", "high"):
            return {"action": "save_offer", "priority": 1, "channel": "email+call",
                    "reason": f"churn risk {risk_tier} ({risk})", "flow": "churn-prevention",
                    "offer": "retention discount / pause"}
        if row.get("health_tier") == "watch":
            return {"action": "check_in", "priority": 3, "channel": "email",
                    "reason": f"health score {health} is slipping", "flow": "health-score-alert", "offer": ""}
        if row.get("mrr_band") == "enterprise" and row.get("value_rank", 99) <= 5:
            return {"action": "expansion", "priority": 4, "channel": "email+sales",
                    "reason": f"top-{row.get('value_rank')} value account (${mrr}/mo)",
                    "flow": "expansion-opportunity", "offer": "annual plan / extra seats"}
        if row.get("ltv_tier") == "champion" and health >= 70:
            return {"action": "referral", "priority": 5, "channel": "email",
                    "reason": "healthy high-value customer", "flow": "referral-ask", "offer": "referral credit"}
        if row.get("health_tier") == "healthy" and row.get("tenure_months", 0) < 2:
            return {"action": "onboarding", "priority": 6, "channel": "email+inapp",
                    "reason": f"new customer ({row.get('tenure_months')} months in)", "flow": "onboarding-milestone", "offer": ""}
        return {"action": "maintain", "priority": 9, "channel": "none",
                "reason": "healthy, no immediate trigger", "flow": "", "offer": ""}

    async def _recommend(self, p: dict[str, Any]) -> dict[str, Any]:
        seg = AdvancedSegmentation(self.registry)
        rows = await seg._enrich_records(p.get("tenant_id", ""), p.get("include_churn_risk", True))
        cid = p.get("customer_id", "")
        email = p.get("email", "")
        for row in rows:
            if (cid and row.get("id") == cid) or (cid and row.get("email") == cid) or (email and row.get("email") == email):
                decision = self._decide(row)
                return {"status": "ok", "customer_id": row.get("id"), "customer": row, "recommendation": decision}
        return {"status": "not_found"}

    async def _all(self, p: dict[str, Any]) -> dict[str, Any]:
        seg = AdvancedSegmentation(self.registry)
        rows = await seg._enrich_records(p.get("tenant_id", ""), p.get("include_churn_risk", True))
        out = []
        for row in rows:
            d = self._decide(row)
            if d["action"] != "maintain" or p.get("include_maintain"):
                out.append({"customer_id": row.get("id"), "name": row.get("name"), "email": row.get("email"),
                            "mrr": row.get("mrr"), "health_score": row.get("health_score"),
                            "churn_risk": row.get("churn_risk"), "due_soon": row.get("due_soon"),
                            "overdue": row.get("overdue"), **d})
        out.sort(key=lambda x: x["priority"])
        return {"status": "ok", "recommendations": out, "count": len(out),
                "by_action": {a: sum(1 for x in out if x["action"] == a) for a in {x["action"] for x in out}}}


class AutoApproachService:
    """The closed loop: scan customers, find who needs approaching, enrol them
    into campaigns automatically (service due, churn risk, renewal, health)."""

    TRIGGERS = {
        "service_due": {"criteria": {"due_soon": True}, "goal": "reactivate",
                        "flows": ["service-due-reminder"], "name": "Auto — service due reminder"},
        "service_overdue": {"criteria": {"overdue": True}, "goal": "reactivate",
                            "flows": ["service-overdue"], "name": "Auto — overdue service"},
        "churn_risk": {"criteria": {"churn_risk_tier": ["critical", "high"]}, "goal": "reduce_churn",
                       "flows": ["churn-prevention"], "name": "Auto — churn risk save"},
        "low_health": {"criteria": {"health_tier": ["critical", "at_risk"]}, "goal": "reduce_churn",
                       "flows": ["health-score-alert"], "name": "Auto — low health check-in"},
    }

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._log = _JsonStore("auto_approach_log.json")

    def register(self) -> None:
        reg = self.registry.register("automation.auto_approach", version="1.0.0", metadata={"domain": "automation", "type": "orchestration"})
        reg.actions["scan"] = self._scan
        reg.actions["run"] = self._run
        reg.actions["history"] = self._history
        reg.actions["triggers"] = self._triggers

    async def _triggers(self, p: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "triggers": {k: {"criteria": v["criteria"], "goal": v["goal"], "flows": v["flows"], "name": v["name"]}
                                             for k, v in self.TRIGGERS.items()}}

    async def _scan(self, p: dict[str, Any]) -> dict[str, Any]:
        """Preview which customers each auto-trigger would approach."""
        tenant = p.get("tenant_id", "")
        seg = AdvancedSegmentation(self.registry)
        rows = await seg._enrich_records(tenant, True)
        found = {}
        for key, spec in self.TRIGGERS.items():
            matched = [r for r in rows if seg._matches(r, spec["criteria"])]
            found[key] = {"count": len(matched), "customers": [
                {"id": r.get("id"), "name": r.get("name"), "email": r.get("email"),
                 "mrr": r.get("mrr"), "reason": self._reason(spec["criteria"], r)} for r in matched[:50]]}
        return {"status": "ok", "triggers": found, "total_customers": len(rows)}

    @staticmethod
    def _reason(criteria: dict[str, Any], row: dict[str, Any]) -> str:
        parts = []
        for field, cond in criteria.items():
            if field == "due_soon":
                parts.append(f"{row.get('service_name') or 'service'} due in {row.get('days_until_due')}d")
            elif field == "overdue":
                parts.append(f"{row.get('service_name') or 'service'} overdue by {abs(row.get('days_until_due') or 0)}d")
            elif field == "churn_risk_tier":
                parts.append(f"churn risk {row.get('churn_risk')} ({row.get('churn_risk_tier')})")
            elif field == "health_tier":
                parts.append(f"health {row.get('health_score')}")
            else:
                parts.append(f"{field}={row.get(field)}")
        return "; ".join(parts)

    async def _run(self, p: dict[str, Any]) -> dict[str, Any]:
        """Create a campaign per trigger that has matches and execute it."""
        tenant = p.get("tenant_id", "")
        selected = p.get("triggers") or list(self.TRIGGERS.keys())
        dry_run = bool(p.get("dry_run", False))
        created = []
        seg = AdvancedSegmentation(self.registry)
        rows = await seg._enrich_records(tenant, True)
        for key in selected:
            spec = self.TRIGGERS.get(key)
            if not spec:
                continue
            matched = [r for r in rows if seg._matches(r, spec["criteria"])]
            if not matched:
                continue
            if dry_run:
                created.append({"trigger": key, "campaign_id": None, "matched": len(matched), "dry_run": True})
                continue
            camp = await self.registry.invoke("campaigns", "create", {
                "tenant_id": tenant, "name": spec["name"], "goal": spec["goal"],
                "description": f"Auto-created by the approach engine ({key})",
                "segment": {"id": f"auto-{key}", "name": spec["name"],
                            "criteria": spec["criteria"]},
                "flows": spec["flows"], "schedule": {"type": "once"},
                "success_metrics": ["reactivation_rate"] if key.startswith("service") else ["retention"],
                "auto_trigger": key,
            })
            cid = camp.get("campaign", {}).get("campaign_id", "")
            await self.registry.invoke("campaigns", "activate", {"tenant_id": tenant, "campaign_id": cid})
            run = await self.registry.invoke("campaigns", "run", {"tenant_id": tenant, "campaign_id": cid, "clients": matched})
            entry = {"trigger": key, "campaign_id": cid, "matched": len(matched),
                     "segment_size": run.get("results", {}).get("segment_size", 0),
                     "outcomes": run.get("results", {}).get("outcomes_count", 0),
                     "at": datetime.now(UTC).isoformat()}
            self._log.upsert("at", {"at": entry["at"], "tenant_id": tenant, **entry})
            created.append(entry)
        return {"status": "ok", "campaigns_created": len(created), "results": created}

    async def _history(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        return {"status": "ok", "runs": [r for r in self._log.load() if r.get("tenant_id") == tenant]}


class TailoredContentService:
    """Per-campaign message templates with per-member variable rendering."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._templates = _JsonStore("campaign_templates.json")

    def register(self) -> None:
        reg = self.registry.register("campaigns.templates", version="1.0.0", metadata={"domain": "campaigns", "type": "content"})
        reg.actions["set_template"] = self._set
        reg.actions["get_template"] = self._get
        reg.actions["render"] = self._render
        reg.actions["list_templates"] = self._list_templates
        reg.actions["delete"] = self._delete

    async def _set(self, p: dict[str, Any]) -> dict[str, Any]:
        tpl = {
            "template_id": p.get("template_id") or f"tpl-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "campaign_id": p.get("campaign_id", ""),
            "name": p.get("name", "Template"),
            "channel": p.get("channel", "email"),  # email | sms | push
            "subject": p.get("subject", ""),
            "body": p.get("body", ""),
            "segment_overrides": p.get("segment_overrides", {}),  # {segment_id: {subject, body}}
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._templates.upsert("template_id", tpl)
        return {"status": "saved", "template": tpl}

    async def _get(self, p: dict[str, Any]) -> dict[str, Any]:
        cid = p.get("campaign_id", "")
        for t in self._templates.load():
            if t.get("campaign_id") == cid or t.get("template_id") == p.get("template_id"):
                return {"status": "ok", "template": t}
        return {"status": "not_found"}

    async def _list_templates(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        return {"status": "ok", "templates": [t for t in self._templates.load() if t.get("tenant_id") == tenant]}

    async def _delete(self, p: dict[str, Any]) -> dict[str, Any]:
        self._templates.save([t for t in self._templates.load() if t.get("template_id") != p.get("template_id")])
        return {"status": "deleted"}

    @staticmethod
    def _render_text(text: str, member: dict[str, Any], extra: dict[str, Any] | None = None) -> str:
        values = {
            "name": member.get("name") or "there",
            "first_name": (member.get("name") or "there").split(" ")[0],
            "email": member.get("email", ""),
            "plan": member.get("plan", ""),
            "mrr": member.get("mrr", 0),
            "ltv": member.get("ltv", 0),
            "service_name": member.get("service_name") or "your service",
            "next_due_date": member.get("next_due_date") or "",
            "days_until_due": member.get("days_until_due", ""),
            "discount_pct": 20,
            "offer": "20% off your next month",
            "booking_url": "https://retention.snapford.com/book",
            "update_url": "https://retention.snapford.com/account/billing",
        }
        values.update(extra or {})
        def sub(match: re.Match) -> str:
            key = match.group(1).strip()
            return str(values.get(key, match.group(0)))
        return re.sub(r"\{\{\s*([\w.]+)\s*\}\}", sub, text or "")

    async def _render(self, p: dict[str, Any]) -> dict[str, Any]:
        """Render a campaign template for one member (segment override wins)."""
        tpl = await self._get({"campaign_id": p.get("campaign_id", ""), "template_id": p.get("template_id", "")})
        if tpl["status"] != "ok":
            return tpl
        t = tpl["template"]
        member = p.get("member", {})
        segment_id = p.get("segment_id", "")
        override = (t.get("segment_overrides") or {}).get(segment_id, {})
        subject = self._render_text(override.get("subject", t.get("subject", "")), member, p.get("vars"))
        body = self._render_text(override.get("body", t.get("body", "")), member, p.get("vars"))
        return {"status": "ok", "channel": t.get("channel", "email"), "subject": subject, "body": body,
                "used_override": bool(override)}


__all__ = ["AdvancedSegmentation", "NextBestActionService", "AutoApproachService", "TailoredContentService",
           "COMPUTED_FIELDS", "FIELD_TYPES"]
