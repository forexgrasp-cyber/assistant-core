"""Renewal risk pipeline: T-90/60/30/14/7 tasks + composite risk score + auto-playbook.

Risk score = health + payment history + support tickets + engagement trend.
At each checkpoint a CS task is created; if risk is high the matching playbook
is auto-selected and armed.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced.customer_intel import _JsonStore

logger = structlog.get_logger(__name__)

CHECKPOINTS = [90, 60, 30, 14, 7]

PLAYBOOKS_BY_RISK = {
    "critical": "executive-save",
    "high": "churn-save",
    "medium": "value-realization",
    "low": "renewal-upsell",
}


class RenewalRiskService:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._renewals = _JsonStore("renewal_risk.json")

    def register(self) -> None:
        reg = self.registry.register("renewals.risk", version="1.0.0", metadata={"domain": "cs_ops", "type": "pipeline"})
        reg.actions["track"] = self._track
        reg.actions["score"] = self._score
        reg.actions["checkpoints"] = self._checkpoints
        reg.actions["tick"] = self._tick
        reg.actions["list"] = self._list
        reg.actions["get"] = self._get

    async def _track(self, p: dict[str, Any]) -> dict[str, Any]:
        rec = {
            "renewal_id": f"ren2-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "customer_id": p.get("customer_id", ""),
            "subscription_id": p.get("subscription_id", ""),
            "arr": float(p.get("arr", 0)),
            "renews_at": p.get("renews_at", (datetime.now(UTC) + timedelta(days=90)).isoformat()),
            "risk_score": 0.0, "risk_tier": "low", "playbook": None,
            "checkpoints_done": [],
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._renewals.upsert("renewal_id", rec)
        await self._score({"renewal_id": rec["renewal_id"], "tenant_id": rec["tenant_id"],
                           "health": p.get("health", 80), "payment_failures": p.get("payment_failures", 0),
                           "open_tickets": p.get("open_tickets", 0), "usage_trend": p.get("usage_trend", 0)})
        return {"status": "tracked", "renewal_id": rec["renewal_id"]}

    def _risk(self, health: float, payment_failures: int, open_tickets: int, usage_trend: float) -> tuple[float, str]:
        # health 0-100 (lower=worse), failures/tickets increase risk, usage_trend negative increases
        score = (100 - health) * 0.5 + payment_failures * 10 + open_tickets * 5 + max(0, -usage_trend) * 2
        score = round(min(score, 100), 1)
        tier = "critical" if score >= 70 else "high" if score >= 45 else "medium" if score >= 25 else "low"
        return score, tier

    async def _score(self, p: dict[str, Any]) -> dict[str, Any]:
        data = self._renewals.load()
        for r in data:
            if r["renewal_id"] == p.get("renewal_id"):
                score, tier = self._risk(
                    float(p.get("health", 80)), int(p.get("payment_failures", 0)),
                    int(p.get("open_tickets", 0)), float(p.get("usage_trend", 0)))
                r["risk_score"] = score
                r["risk_tier"] = tier
                r["playbook"] = PLAYBOOKS_BY_RISK.get(tier)
                r["scored_at"] = datetime.now(UTC).isoformat()
                self._renewals.save(data)
                return {"status": "ok", "renewal_id": r["renewal_id"], "risk_score": score,
                        "risk_tier": tier, "playbook": r["playbook"]}
        return {"status": "not_found"}

    async def _checkpoints(self, p: dict[str, Any]) -> dict[str, Any]:
        """Checkpoints due now for tracked renewals."""
        now = datetime.now(UTC)
        data = self._renewals.load()
        due = []
        for r in data:
            renews = datetime.fromisoformat(r["renews_at"].replace("Z", "+00:00"))
            days_left = (renews - now).days
            done = r.get("checkpoints_done", [])
            for i, cp in enumerate(CHECKPOINTS):
                if cp in done:
                    continue
                # fire checkpoint cp only if it is the next one due
                # (all higher checkpoints already done)
                higher_done = all(h in done for h in CHECKPOINTS[:i])
                if higher_done and days_left <= cp:
                    due.append({"renewal_id": r["renewal_id"], "customer_id": r["customer_id"],
                                "checkpoint": cp, "days_left": days_left, "risk_tier": r.get("risk_tier"),
                                "playbook": r.get("playbook"), "arr": r["arr"]})
                    r.setdefault("checkpoints_done", []).append(cp)
        self._renewals.save(data)
        return {"status": "ok", "due": due, "count": len(due)}

    async def _tick(self, p: dict[str, Any]) -> dict[str, Any]:
        return await self._checkpoints(p)

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        risk_tier = p.get("risk_tier")
        rows = [r for r in self._renewals.load() if r.get("tenant_id") == tenant]
        if risk_tier:
            rows = [r for r in rows if r.get("risk_tier") == risk_tier]
        rows.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
        return {"status": "ok", "renewals": rows, "count": len(rows)}

    async def _get(self, p: dict[str, Any]) -> dict[str, Any]:
        for r in self._renewals.load():
            if r["renewal_id"] == p.get("renewal_id"):
                return {"status": "ok", "renewal": r}
        return {"status": "not_found"}


__all__ = ["RenewalRiskService", "CHECKPOINTS", "PLAYBOOKS_BY_RISK"]
