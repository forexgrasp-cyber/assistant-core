"""Advanced analytics processing: multi-touch attribution models, cohort comparison,
anomaly root-cause correlation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced.customer_intel import _JsonStore

logger = structlog.get_logger(__name__)

ATTRIBUTION_MODELS = ["first_touch", "last_touch", "linear", "time_decay", "position_based"]


class MultiTouchAttribution:
    """Attribute revenue across multiple touches. Models: first/last/linear/time_decay/position_based."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._touches = _JsonStore("attribution_touches.json")

    def register(self) -> None:
        reg = self.registry.register("attribution.multitouch", version="1.0.0", metadata={"domain": "analytics", "type": "attribution"})
        reg.actions["record_touch"] = self._record
        reg.actions["attribute"] = self._attribute
        reg.actions["models"] = self._models

    async def _models(self, p: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "models": ATTRIBUTION_MODELS}

    async def _record(self, p: dict[str, Any]) -> dict[str, Any]:
        t = {
            "touch_id": f"t-{uuid.uuid4().hex[:10]}",
            "tenant_id": p.get("tenant_id", ""),
            "customer_id": p.get("customer_id", ""),
            "channel": p.get("channel", "email"),      # email | sms | push | ad | referral | sales
            "campaign_id": p.get("campaign_id", ""),
            "touchpoint": p.get("touchpoint", "click"),
            "value": float(p.get("value", 0)),
            "at": p.get("at", datetime.now(UTC).isoformat()),
            "converted": bool(p.get("converted", False)),
        }
        self._touches.upsert("touch_id", t)
        return {"status": "recorded", "touch": t}

    async def _attribute(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        cust = p.get("customer_id", "")
        model = p.get("model", "linear")
        if model not in ATTRIBUTION_MODELS:
            return {"status": "invalid_model", "models": ATTRIBUTION_MODELS}
        touches = [t for t in self._touches.load() if t.get("tenant_id") == tenant and t.get("customer_id") == cust]
        touches.sort(key=lambda x: x.get("at", ""))
        if not touches:
            return {"status": "no_touches", "attribution": {}}
        conversion = next((t for t in reversed(touches) if t.get("converted")), touches[-1])
        value = float(p.get("conversion_value", conversion.get("value", 0)))
        weights = self._weights(model, len(touches))
        per_touch = {}
        for t, w in zip(touches, weights):
            per_touch[t["touch_id"]] = {"channel": t["channel"], "campaign_id": t.get("campaign_id", ""),
                                        "touchpoint": t["touchpoint"], "weight": round(w, 4),
                                        "value": round(value * w, 2), "at": t["at"]}
        by_channel: dict[str, float] = {}
        for t, w in zip(touches, weights):
            by_channel[t["channel"]] = round(by_channel.get(t["channel"], 0) + value * w, 2)
        by_campaign: dict[str, float] = {}
        for t, w in zip(touches, weights):
            key = t.get("campaign_id") or "direct"
            by_campaign[key] = round(by_campaign.get(key, 0) + value * w, 2)
        return {"status": "ok", "model": model, "customer_id": cust,
                "conversion_value": value, "attribution": per_touch,
                "by_channel": by_channel, "by_campaign": by_campaign,
                "touch_count": len(touches)}

    @staticmethod
    def _weights(model: str, n: int) -> list[float]:
        if n == 0:
            return []
        if model == "first_touch":
            return [1.0] + [0.0] * (n - 1)
        if model == "last_touch":
            return [0.0] * (n - 1) + [1.0]
        if model == "linear":
            return [1.0 / n] * n
        if model == "time_decay":
            raw = [0.5 ** i for i in range(n)][::-1]  # most recent gets highest
            s = sum(raw)
            return [x / s for x in raw]
        if model == "position_based":
            if n == 1:
                return [1.0]
            w = [0.0] * n
            w[0] = w[-1] = 0.4
            rest = 0.2 / (n - 2) if n > 2 else 0.0
            for i in range(1, n - 1):
                w[i] = rest
            return w
        return [1.0 / n] * n


class CohortComparison:
    """Compare two cohorts side by side (retention, value, health)."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def register(self) -> None:
        reg = self.registry.register("analytics.cohort_compare", version="1.0.0", metadata={"domain": "analytics", "type": "platform"})
        reg.actions["compare"] = self._compare

    async def _compare(self, p: dict[str, Any]) -> dict[str, Any]:
        a = p.get("cohort_a", {})
        b = p.get("cohort_b", {})
        metric = p.get("metric", "retention_rate_30d")

        def val(c: dict[str, Any]) -> float:
            if "metrics" in c and isinstance(c["metrics"], dict):
                return float(c["metrics"].get(metric, 0))
            return float(c.get(metric, 0))

        va, vb = val(a), val(b)
        diff = round(vb - va, 4)
        return {"status": "ok", "metric": metric,
                "cohort_a": {"name": a.get("name", "A"), "value": va, "size": a.get("size", 0)},
                "cohort_b": {"name": b.get("name", "B"), "value": vb, "size": b.get("size", 0)},
                "difference": diff,
                "winner": "B" if diff > 0 else "A" if diff < 0 else "tie",
                "relative_diff_pct": round(diff / va * 100, 1) if va else None}


class RootCauseService:
    """Correlate a metric anomaly with recent platform activity (deploys, campaigns, ticket spikes, payment errors)."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def register(self) -> None:
        reg = self.registry.register("analytics.root_cause", version="1.0.0", metadata={"domain": "analytics", "type": "diagnostics"})
        reg.actions["analyze"] = self._analyze

    async def _analyze(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        window_hours = int(p.get("window_hours", 24))
        since = datetime.now(UTC).timestamp() - window_hours * 3600
        signals = []

        # campaigns run recently
        try:
            camps = await self.registry.invoke("campaigns", "list", {"tenant_id": tenant})
            for c in camps.get("campaigns", []):
                last = c.get("last_run_at") or c.get("created_at")
                if not last:
                    continue
                ts = datetime.fromisoformat(last.replace("Z", "+00:00")).timestamp()
                if ts >= since:
                    signals.append({"kind": "campaign", "detail": c.get("name", c.get("campaign_id")),
                                    "impact": "volume spike / fatigue", "at": last, "confidence": 0.6})
        except Exception:
            pass
        # support ticket spike
        try:
            tickets = await self.registry.invoke("support", "list_tickets", {"tenant_id": tenant})
            recent = [t for t in tickets.get("tickets", []) if str(t.get("created_at", "")) >= str(datetime.now(UTC).date())]
            if len(recent) >= 3:
                signals.append({"kind": "support_spike", "detail": f"{len(recent)} tickets today",
                                "impact": "dissatisfaction driving churn", "confidence": 0.7})
        except Exception:
            pass
        # payment failures
        try:
            dunning = await self.registry.invoke("dunning.engine", "list", {"tenant_id": tenant, "status": "active"})
            if dunning.get("count", 0) > 0:
                signals.append({"kind": "payment_failures", "detail": f"{dunning['count']} active dunning campaigns",
                                "impact": "involuntary churn risk", "confidence": 0.8})
        except Exception:
            pass
        # anomalies already recorded
        try:
            inc = await self.registry.invoke("incidents", "list", {"tenant_id": tenant})
            for i in inc.get("incidents", [])[:3]:
                signals.append({"kind": "incident", "detail": f"{i['metric']} {i['direction']} {i['deviation_pct']}%",
                                "impact": "known incident", "confidence": 0.9})
        except Exception:
            pass

        signals.sort(key=lambda s: s["confidence"], reverse=True)
        likely = signals[0] if signals else None
        return {"status": "ok", "metric": p.get("metric", ""), "window_hours": window_hours,
                "signals": signals, "count": len(signals),
                "likely_cause": likely,
                "recommendation": self._recommend(likely)}

    @staticmethod
    def _recommend(signal: dict | None) -> str:
        if not signal:
            return "No correlated platform activity found — check external factors or data pipeline."
        return {
            "campaign": "Review campaign volume/frequency — fatigue may be driving the drop.",
            "support_spike": "Escalate support queue and reach out to affected customers proactively.",
            "payment_failures": "Run dunning escalation now; prioritize involuntary churn.",
            "incident": "Incident is open — follow the incident runbook and draft customer comms.",
        }.get(signal["kind"], "Investigate further.")


__all__ = ["MultiTouchAttribution", "CohortComparison", "RootCauseService", "ATTRIBUTION_MODELS"]
