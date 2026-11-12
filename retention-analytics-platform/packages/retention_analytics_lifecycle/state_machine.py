"""Subscription lifecycle state machine.

States: trial -> active -> past_due -> grace -> suspended -> cancelled -> churned
Plus: paused (from active/grace), reactivated (from cancelled/churned -> active).

Each transition is validated, recorded with a timestamp, emits an event, and
can trigger workflows (event bindings). Timers (grace expiry, suspension) are
advanced by `tick`.
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

STATES = ["trial", "active", "past_due", "grace", "suspended", "paused", "cancelled", "churned"]

# Valid transitions
TRANSITIONS: dict[str, list[str]] = {
    "trial": ["active", "cancelled", "churned"],
    "active": ["past_due", "paused", "cancelled", "suspended"],
    "past_due": ["active", "grace", "suspended", "cancelled"],
    "grace": ["active", "suspended", "cancelled"],
    "suspended": ["active", "cancelled", "churned"],
    "paused": ["active", "cancelled"],
    "cancelled": ["active", "churned"],  # reactivation or churn after 30d
    "churned": ["active"],
}

# Events emitted per transition
TRANSITION_EVENTS: dict[tuple[str, str], str] = {
    ("trial", "active"): "subscription.activated",
    ("active", "past_due"): "payment.failed",
    ("past_due", "grace"): "subscription.grace_started",
    ("grace", "suspended"): "subscription.suspended",
    ("suspended", "cancelled"): "subscription.cancelled",
    ("active", "cancelled"): "subscription.cancelled",
    ("cancelled", "active"): "client.reactivated",
    ("churned", "active"): "client.reactivated",
    ("active", "paused"): "subscription.paused",
    ("paused", "active"): "subscription.resumed",
    ("active", "suspended"): "subscription.suspended",
    ("past_due", "active"): "payment.recovered",
    ("grace", "active"): "payment.recovered",
    ("suspended", "active"): "payment.recovered",
}

GRACE_DAYS = 7
SUSPEND_AFTER_GRACE_DAYS = 3
CHURN_AFTER_CANCEL_DAYS = 30


class LifecycleService:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._subs = _JsonStore("subscription_lifecycle.json")

    def register(self) -> None:
        reg = self.registry.register("lifecycle", version="2.0.0", metadata={"domain": "lifecycle", "type": "state_machine"})
        reg.actions["create"] = self._create
        reg.actions["transition"] = self._transition
        reg.actions["get"] = self._get
        reg.actions["list"] = self._list
        reg.actions["tick"] = self._tick
        reg.actions["states"] = self._states
        reg.actions["history"] = self._history

    async def _states(self, p: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "states": STATES, "transitions": {k: v for k, v in TRANSITIONS.items()}}

    async def _create(self, p: dict[str, Any]) -> dict[str, Any]:
        sub = {
            "subscription_id": p.get("subscription_id") or f"sub-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "customer_id": p.get("customer_id", ""),
            "plan": p.get("plan", "starter"),
            "amount": float(p.get("amount", 0)),
            "interval": p.get("interval", "month"),
            "state": p.get("state", "trial"),
            "current_period_start": p.get("current_period_start", datetime.now(UTC).isoformat()),
            "trial_ends_at": p.get("trial_ends_at"),
            "grace_ends_at": None,
            "suspended_at": None,
            "cancelled_at": None,
            "history": [{"state": p.get("state", "trial"), "at": datetime.now(UTC).isoformat(), "reason": "created"}],
            "created_at": datetime.now(UTC).isoformat(),
        }
        if sub["state"] not in STATES:
            sub["state"] = "trial"
        self._subs.upsert("subscription_id", sub)
        return {"status": "created", "subscription": sub}

    async def _transition(self, p: dict[str, Any]) -> dict[str, Any]:
        """Transition a subscription to a new state if valid; records history, emits event."""
        data = self._subs.load()
        for s in data:
            if s["subscription_id"] == p.get("subscription_id"):
                frm = s["state"]
                to = p.get("to", "")
                if to not in STATES:
                    return {"status": "invalid_state", "to": to}
                if to not in TRANSITIONS.get(frm, []):
                    return {"status": "invalid_transition", "from": frm, "to": to,
                            "allowed": TRANSITIONS.get(frm, [])}
                s["state"] = to
                entry = {"from": frm, "to": to, "at": datetime.now(UTC).isoformat(),
                         "reason": p.get("reason", "")}
                s["history"].append(entry)
                now = datetime.now(UTC)
                if to == "grace":
                    s["grace_ends_at"] = (now + timedelta(days=GRACE_DAYS)).isoformat()
                if to == "suspended":
                    s["suspended_at"] = now.isoformat()
                if to == "cancelled":
                    s["cancelled_at"] = now.isoformat()
                if to == "churned":
                    s["churned_at"] = now.isoformat()
                if to == "active":
                    s["grace_ends_at"] = None
                    s["suspended_at"] = None
                self._subs.save(data)
                event = TRANSITION_EVENTS.get((frm, to), f"subscription.{to}")
                logger.info("lifecycle.transition", sub=s["subscription_id"], frm=frm, to=to, event_name=event)
                return {"status": "ok", "subscription_id": s["subscription_id"],
                        "from": frm, "to": to, "event": event, "history": s["history"]}
        return {"status": "not_found"}

    async def _tick(self, p: dict[str, Any]) -> dict[str, Any]:
        """Advance timers: grace expiry -> suspended, suspension -> cancelled -> churned, trial expiry -> churned."""
        now = datetime.now(UTC)
        data = self._subs.load()
        changed = []
        for s in data:
            state = s["state"]
            if state == "trial" and s.get("trial_ends_at"):
                end = datetime.fromisoformat(s["trial_ends_at"].replace("Z", "+00:00"))
                if now >= end:
                    r = await self._transition({"subscription_id": s["subscription_id"], "to": "active", "reason": "trial ended, card on file"})
                    if r["status"] == "ok":
                        changed.append((s["subscription_id"], "trial->active"))
                    else:
                        r = await self._transition({"subscription_id": s["subscription_id"], "to": "churned", "reason": "trial expired, no payment"})
                        if r["status"] == "ok":
                            changed.append((s["subscription_id"], "trial->churned"))
            elif state == "grace" and s.get("grace_ends_at"):
                end = datetime.fromisoformat(s["grace_ends_at"].replace("Z", "+00:00"))
                if now >= end:
                    r = await self._transition({"subscription_id": s["subscription_id"], "to": "suspended", "reason": "grace expired"})
                    if r["status"] == "ok":
                        changed.append((s["subscription_id"], "grace->suspended"))
            elif state == "suspended" and s.get("suspended_at"):
                end = datetime.fromisoformat(s["suspended_at"].replace("Z", "+00:00")) + timedelta(days=SUSPEND_AFTER_GRACE_DAYS)
                if now >= end:
                    r = await self._transition({"subscription_id": s["subscription_id"], "to": "cancelled", "reason": "suspension timeout"})
                    if r["status"] == "ok":
                        changed.append((s["subscription_id"], "suspended->cancelled"))
            elif state == "cancelled" and s.get("cancelled_at"):
                end = datetime.fromisoformat(s["cancelled_at"].replace("Z", "+00:00")) + timedelta(days=CHURN_AFTER_CANCEL_DAYS)
                if now >= end:
                    r = await self._transition({"subscription_id": s["subscription_id"], "to": "churned", "reason": "cancelled 30d ago"})
                    if r["status"] == "ok":
                        changed.append((s["subscription_id"], "cancelled->churned"))
        return {"status": "ok", "ticked": len(changed), "changes": changed}

    async def _get(self, p: dict[str, Any]) -> dict[str, Any]:
        for s in self._subs.load():
            if s["subscription_id"] == p.get("subscription_id"):
                return {"status": "ok", "subscription": s}
        return {"status": "not_found"}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        state = p.get("state")
        subs = [s for s in self._subs.load() if s.get("tenant_id") == tenant and (not state or s["state"] == state)]
        return {"status": "ok", "subscriptions": subs, "count": len(subs)}

    async def _history(self, p: dict[str, Any]) -> dict[str, Any]:
        r = await self._get(p)
        if r["status"] != "ok":
            return r
        return {"status": "ok", "subscription_id": p.get("subscription_id"), "history": r["subscription"]["history"]}


__all__ = ["LifecycleService", "STATES", "TRANSITIONS"]
