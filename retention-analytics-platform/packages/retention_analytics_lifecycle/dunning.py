"""Dunning escalation engine v2: reason-based retry timing, escalation levels,
card updater, recovery attribution.

Failure reasons map to retry strategies (e.g. insufficient_funds retries sooner
than card_declined). Escalation levels: L1 email (day 0), L2 sms (day 2),
L3 call task (day 5), L4 suspend (day 7). Each attempt is recorded; recovery
is attributed to the attempt that succeeded.
"""

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

# Retry delay (days) per failure reason
RETRY_DELAYS: dict[str, list[int]] = {
    "insufficient_funds": [1, 2, 4],
    "card_declined": [3, 5, 7],
    "expired_card": [1, 3, 5],      # card updater may fix automatically
    "do_not_honor": [2, 4, 6],
    "generic_decline": [3, 5, 7],
    "lost_card": [1, 3, 5],
}

ESCALATION = [
    {"level": 1, "day": 0, "channel": "email", "action": "payment_reminder_email"},
    {"level": 2, "day": 2, "channel": "sms", "action": "payment_reminder_sms"},
    {"level": 3, "day": 5, "channel": "task", "action": "call_customer_task"},
    {"level": 4, "day": 7, "channel": "suspend", "action": "suspend_service"},
]


class DunningEngine:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._campaigns = _JsonStore("dunning_campaigns_v2.json")

    def register(self) -> None:
        reg = self.registry.register("dunning.engine", version="2.0.0", metadata={"domain": "billing", "type": "engine"})
        reg.actions["start"] = self._start
        reg.actions["record_failure"] = self._record_failure
        reg.actions["tick"] = self._tick
        reg.actions["recover"] = self._recover
        reg.actions["get"] = self._get
        reg.actions["list"] = self._list
        reg.actions["attribution"] = self._attribution

    async def _start(self, p: dict[str, Any]) -> dict[str, Any]:
        camp = {
            "campaign_id": f"dun2-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "subscription_id": p.get("subscription_id", ""),
            "customer_id": p.get("customer_id", ""),
            "customer_email": p.get("customer_email", ""),
            "customer_phone": p.get("customer_phone", ""),
            "amount_due": float(p.get("amount_due", 0)),
            "failure_reason": p.get("failure_reason", "generic_decline"),
            "retry_schedule": RETRY_DELAYS.get(p.get("failure_reason", ""), RETRY_DELAYS["generic_decline"]),
            "attempts": [],
            "escalation_level": 0,
            "card_updater_enrolled": p.get("card_updater", True),
            "status": "active",
            "started_at": datetime.now(UTC).isoformat(),
        }
        self._campaigns.upsert("campaign_id", camp)
        return {"status": "started", "campaign": camp}

    async def _record_failure(self, p: dict[str, Any]) -> dict[str, Any]:
        data = self._campaigns.load()
        for c in data:
            if c["campaign_id"] == p.get("campaign_id"):
                attempt = {
                    "attempt": len(c["attempts"]) + 1,
                    "at": datetime.now(UTC).isoformat(),
                    "reason": p.get("reason", c["failure_reason"]),
                    "status": "failed",
                }
                c["attempts"].append(attempt)
                # advance escalation based on days since start
                days = (datetime.now(UTC) - datetime.fromisoformat(c["started_at"].replace("Z", "+00:00"))).days
                for esc in ESCALATION:
                    if days >= esc["day"] and c["escalation_level"] < esc["level"]:
                        c["escalation_level"] = esc["level"]
                        c.setdefault("escalations", []).append({**esc, "at": datetime.now(UTC).isoformat()})
                self._campaigns.save(data)
                return {"status": "recorded", "attempt": attempt, "escalation_level": c["escalation_level"]}
        return {"status": "not_found"}

    async def _tick(self, p: dict[str, Any]) -> dict[str, Any]:
        """Return campaigns due for their next retry/escalation now."""
        now = datetime.now(UTC)
        data = self._campaigns.load()
        due = []
        for c in data:
            if c["status"] != "active":
                continue
            days = (now - datetime.fromisoformat(c["started_at"].replace("Z", "+00:00"))).days
            sched = c["retry_schedule"]
            next_retry_day = sched[len(c["attempts"])] if len(c["attempts"]) < len(sched) else None
            if next_retry_day is not None and days >= next_retry_day:
                due.append({"campaign_id": c["campaign_id"], "customer_email": c["customer_email"],
                            "amount_due": c["amount_due"], "next_attempt": len(c["attempts"]) + 1,
                            "escalation_level": c["escalation_level"]})
            # escalations due
            for esc in ESCALATION:
                if days >= esc["day"] and not any(e["level"] == esc["level"] for e in c.get("escalations", [])):
                    due.append({"campaign_id": c["campaign_id"], "escalation": esc, "customer_id": c["customer_id"]})
        return {"status": "ok", "due": due, "count": len(due)}

    async def _recover(self, p: dict[str, Any]) -> dict[str, Any]:
        """Mark a campaign recovered; attribute to the latest attempt."""
        data = self._campaigns.load()
        for c in data:
            if c["campaign_id"] == p.get("campaign_id"):
                c["status"] = "recovered"
                c["recovered_at"] = datetime.now(UTC).isoformat()
                c["recovered_by_attempt"] = len(c["attempts"])
                c["recovered_by_card_updater"] = bool(p.get("card_updater", False))
                self._campaigns.save(data)
                return {"status": "recovered", "campaign_id": c["campaign_id"],
                        "recovered_by_attempt": c["recovered_by_attempt"],
                        "amount_recovered": c["amount_due"]}
        return {"status": "not_found"}

    async def _attribution(self, p: dict[str, Any]) -> dict[str, Any]:
        """Which channel/attempt recovered revenue — for optimizing the dunning mix."""
        tenant = p.get("tenant_id", "")
        camps = [c for c in self._campaigns.load() if c.get("tenant_id") == tenant]
        recovered = [c for c in camps if c["status"] == "recovered"]
        by_attempt: dict[int, int] = {}
        by_updater = 0
        total = 0.0
        for c in recovered:
            by_attempt[c.get("recovered_by_attempt", 0)] = by_attempt.get(c.get("recovered_by_attempt", 0), 0) + 1
            if c.get("recovered_by_card_updater"):
                by_updater += 1
            total += c.get("amount_due", 0)
        return {"status": "ok", "campaigns": len(camps), "recovered": len(recovered),
                "recovery_rate": round(len(recovered) / len(camps) * 100, 1) if camps else 0,
                "amount_recovered": round(total, 2),
                "by_attempt": by_attempt, "by_card_updater": by_updater}

    async def _get(self, p: dict[str, Any]) -> dict[str, Any]:
        for c in self._campaigns.load():
            if c["campaign_id"] == p.get("campaign_id"):
                return {"status": "ok", "campaign": c}
        return {"status": "not_found"}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        status = p.get("status")
        camps = [c for c in self._campaigns.load() if c.get("tenant_id") == tenant and (not status or c["status"] == status)]
        return {"status": "ok", "campaigns": camps, "count": len(camps)}


__all__ = ["DunningEngine", "RETRY_DELAYS", "ESCALATION"]
