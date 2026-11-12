"""Health engine v2: time-decaying health score.

Health decays when there is no engagement and recovers on engagement.
Components: usage, support, payment, engagement. Thresholds trigger actions
(alert team, run playbook, send check-in).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced.customer_intel import _JsonStore

logger = structlog.get_logger(__name__)

DECAY_PER_DAY = 1.5          # points lost per day without engagement
RECOVERY_ON_ENGAGE = 10      # points gained per engagement event
COMPONENT_WEIGHTS = {"usage": 0.35, "engagement": 0.25, "support": 0.20, "payment": 0.20}

THRESHOLDS = [
    {"score": 70, "action": "watch", "note": "slightly declining"},
    {"score": 50, "action": "playbook", "note": "run churn playbook"},
    {"score": 30, "action": "alert", "note": "alert CS team + exec sponsor"},
    {"score": 15, "action": "critical", "note": "critical — save offer + call"},
]


class HealthEngine:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._scores = _JsonStore("health_scores_v2.json")

    def register(self) -> None:
        reg = self.registry.register("health.engine", version="2.0.0", metadata={"domain": "health", "type": "engine"})
        reg.actions["compute"] = self._compute
        reg.actions["record_engagement"] = self._engage
        reg.actions["tick_decay"] = self._decay
        reg.actions["get"] = self._get
        reg.actions["list"] = self._list
        reg.actions["thresholds"] = self._thresholds
        reg.actions["action_for"] = self._action_for

    async def _thresholds(self, p: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "thresholds": THRESHOLDS, "decay_per_day": DECAY_PER_DAY}

    def _score_components(self, p: dict[str, Any]) -> dict[str, float]:
        return {
            "usage": min(float(p.get("usage_score", 50)) / 100, 1.0),
            "engagement": min(float(p.get("engagement_score", 50)) / 100, 1.0),
            "support": 1.0 - min(int(p.get("open_tickets", 0)) / 5, 1.0),
            "payment": 1.0 - min(int(p.get("payment_failures", 0)) / 3, 1.0),
        }

    async def _compute(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        cid = p.get("client_id", "")
        comps = self._score_components(p)
        score = round(sum(comps[k] * w for k, w in COMPONENT_WEIGHTS.items()) * 100, 1)
        # decay since last engagement
        existing = next((s for s in self._scores.load() if s.get("client_id") == cid and s.get("tenant_id") == tenant), None)
        if existing and existing.get("last_engagement_at"):
            days = (datetime.now(UTC) - datetime.fromisoformat(existing["last_engagement_at"].replace("Z", "+00:00"))).days
            score = max(0.0, score - days * DECAY_PER_DAY)
            score = round(score, 1)
        action = next((t for t in THRESHOLDS if score < t["score"]), None)
        rec = {
            "client_id": cid, "tenant_id": tenant, "score": score,
            "tier": "critical" if score < 15 else "at_risk" if score < 50 else "healthy" if score >= 70 else "watch",
            "components": comps, "action": action["action"] if action else "none",
            "action_note": action["note"] if action else "",
            "last_engagement_at": (existing or {}).get("last_engagement_at"),
            "computed_at": datetime.now(UTC).isoformat(),
        }
        self._scores.upsert("client_id", rec, match="client_id")
        return {"status": "ok", "result": rec}

    async def _engage(self, p: dict[str, Any]) -> dict[str, Any]:
        """Record an engagement event: bumps score and resets decay clock."""
        tenant = p.get("tenant_id", "")
        cid = p.get("client_id", "")
        scores = self._scores.load()
        rec = next((s for s in scores if s.get("client_id") == cid and s.get("tenant_id") == tenant), None)
        if not rec:
            r = await self._compute({**p, "usage_score": 60, "engagement_score": 60})
            rec = r["result"]
        rec["score"] = round(min(100.0, rec["score"] + RECOVERY_ON_ENGAGE), 1)
        rec["last_engagement_at"] = datetime.now(UTC).isoformat()
        rec["tier"] = "critical" if rec["score"] < 15 else "at_risk" if rec["score"] < 50 else "healthy" if rec["score"] >= 70 else "watch"
        self._scores.save(scores if rec in scores else scores + [rec])
        return {"status": "ok", "score": rec["score"], "tier": rec["tier"]}

    async def _decay(self, p: dict[str, Any]) -> dict[str, Any]:
        """Apply daily decay to all scores without recent engagement (cron tick)."""
        now = datetime.now(UTC)
        data = self._scores.load()
        decayed = 0
        for s in data:
            last = s.get("last_engagement_at")
            if not last:
                continue
            days = (now - datetime.fromisoformat(last.replace("Z", "+00:00"))).days
            if days > 0:
                s["score"] = round(max(0.0, s["score"] - days * DECAY_PER_DAY), 1)
                decayed += 1
        self._scores.save(data)
        return {"status": "ok", "decayed": decayed}

    async def _action_for(self, p: dict[str, Any]) -> dict[str, Any]:
        score = float(p.get("score", 100))
        action = next((t for t in THRESHOLDS if score < t["score"]), None)
        return {"status": "ok", "score": score, "action": action["action"] if action else "none", "note": action["note"] if action else ""}

    async def _get(self, p: dict[str, Any]) -> dict[str, Any]:
        for s in self._scores.load():
            if s.get("client_id") == p.get("client_id"):
                return {"status": "ok", "score": s}
        return {"status": "not_found"}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        tier = p.get("tier")
        rows = [s for s in self._scores.load() if s.get("tenant_id") == tenant and (not tier or s.get("tier") == tier)]
        rows.sort(key=lambda x: x.get("score", 100))
        return {"status": "ok", "scores": rows, "count": len(rows)}


__all__ = ["HealthEngine", "THRESHOLDS", "DECAY_PER_DAY"]
