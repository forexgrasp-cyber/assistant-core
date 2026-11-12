"""Usage metering + overage engine and proration engine.

Metering: record usage events per resource per tenant, evaluate against quota,
alert at 80/90/100%, produce overage invoice lines, optionally hard-cap.

Proration: plan change mid-cycle -> prorated charge/credit for the remainder.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced.customer_intel import _JsonStore

logger = structlog.get_logger(__name__)

THRESHOLDS_PCT = [80, 90, 100]


class MeteringService:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._usage = _JsonStore("usage_metering.json")
        self._quotas = _JsonStore("usage_quotas.json")

    def register(self) -> None:
        reg = self.registry.register("metering.v2", version="2.0.0", metadata={"domain": "billing", "type": "metering"})
        reg.actions["set_quota"] = self._set_quota
        reg.actions["record"] = self._record
        reg.actions["usage"] = self._usage
        reg.actions["check"] = self._check
        reg.actions["overage_lines"] = self._overage
        reg.actions["tick"] = self._tick

    def _key(self, tenant: str, resource: str, period: str) -> str:
        return f"{tenant}:{resource}:{period}"

    async def _set_quota(self, p: dict[str, Any]) -> dict[str, Any]:
        q = {
            "tenant_id": p.get("tenant_id", ""), "resource": p.get("resource", "api_calls"),
            "limit": float(p.get("limit", 10000)), "period": p.get("period", "month"),
            "hard_cap": bool(p.get("hard_cap", False)), "overage_price": float(p.get("overage_price", 0.01)),
        }
        # key uses the CALENDAR period so lookups by current month match
        self._quotas.upsert("key", {"key": self._key(q["tenant_id"], q["resource"], self._period()), **q}, match="key")
        return {"status": "ok", "quota": q}

    def _period(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m")

    async def _record(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        resource = p.get("resource", "api_calls")
        amount = float(p.get("amount", 1))
        key = self._key(tenant, resource, self._period())
        data = self._usage.load()
        rec = next((x for x in data if x.get("key") == key), None)
        if not rec:
            rec = {"key": key, "tenant_id": tenant, "resource": resource, "period": self._period(), "used": 0.0, "events": 0}
            data.append(rec)
        rec["used"] = round(rec["used"] + amount, 4)
        rec["events"] += 1
        self._usage.save(data)
        check = await self._check({"tenant_id": tenant, "resource": resource})
        return {"status": "ok", "used": rec["used"], "check": check}

    async def _usage(self, p: dict[str, Any]) -> dict[str, Any]:
        key = self._key(p.get("tenant_id", ""), p.get("resource", "api_calls"), p.get("period", self._period()))
        rec = next((x for x in self._usage.load() if x.get("key") == key), None)
        return {"status": "ok", "usage": rec or {"used": 0, "events": 0}}

    async def _check(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        resource = p.get("resource", "api_calls")
        qkey = self._key(tenant, resource, self._period())
        quota = next((x for x in self._quotas.load() if x.get("key") == qkey), None)
        used = next((x for x in self._usage.load() if x.get("key") == qkey), {"used": 0})
        used_v = float(used.get("used", 0))
        if not quota:
            return {"status": "ok", "configured": False, "used": used_v}
        limit = float(quota["limit"])
        pct = used_v / limit * 100 if limit else 0
        alerts = [t for t in THRESHOLDS_PCT if pct >= t and t not in (quota.get("alerts_sent") or [])]
        if alerts:
            quota.setdefault("alerts_sent", []).extend(alerts)
            self._quotas.save(self._quotas.load())
        capped = quota.get("hard_cap") and pct >= 100
        return {"status": "ok", "configured": True, "used": used_v, "limit": limit,
                "pct": round(pct, 1), "alerts_triggered": alerts,
                "over_limit": pct > 100, "hard_capped": capped}

    async def _overage(self, p: dict[str, Any]) -> dict[str, Any]:
        """Invoice line items for usage above the quota."""
        tenant = p.get("tenant_id", "")
        resource = p.get("resource", "api_calls")
        qkey = self._key(tenant, resource, self._period())
        quota = next((x for x in self._quotas.load() if x.get("key") == qkey), None)
        used = next((x for x in self._usage.load() if x.get("key") == qkey), {"used": 0})
        if not quota:
            return {"status": "ok", "lines": []}
        over = max(0.0, float(used.get("used", 0)) - float(quota["limit"]))
        price = float(quota.get("overage_price", 0))
        lines = [{"resource": resource, "overage_units": round(over, 2),
                  "unit_price": price, "amount": round(over * price, 2)}] if over > 0 else []
        return {"status": "ok", "period": self._period(), "lines": lines, "total": round(sum(l["amount"] for l in lines), 2)}

    async def _tick(self, p: dict[str, Any]) -> dict[str, Any]:
        """Cron: check all quotas, return alerts to fire."""
        tenant = p.get("tenant_id", "")
        out = []
        for q in self._quotas.load():
            if q.get("tenant_id") != tenant:
                continue
            c = await self._check({"tenant_id": tenant, "resource": q["resource"]})
            if c.get("alerts_triggered"):
                out.append({"resource": q["resource"], "pct": c["pct"], "alerts": c["alerts_triggered"]})
        return {"status": "ok", "alerts": out, "count": len(out)}


class ProrationService:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def register(self) -> None:
        reg = self.registry.register("billing.proration", version="1.0.0", metadata={"domain": "billing", "type": "engine"})
        reg.actions["quote_change"] = self._quote
        reg.actions["apply_change"] = self._quote

    async def _quote(self, p: dict[str, Any]) -> dict[str, Any]:
        """Prorated charge/credit for changing plan mid-cycle."""
        current_price = float(p.get("current_price", 0))
        new_price = float(p.get("new_price", 0))
        period_start = datetime.fromisoformat(p["period_start"].replace("Z", "+00:00"))
        period_end = datetime.fromisoformat(p["period_end"].replace("Z", "+00:00"))
        now = datetime.now(UTC)
        total_days = (period_end - period_start).total_seconds() / 86400
        remaining_days = max(0.0, (period_end - now).total_seconds() / 86400)
        # credit for unused time on current plan, charge for remaining on new plan
        credit = current_price * (remaining_days / total_days) if total_days else 0
        charge = new_price * (remaining_days / total_days) if total_days else 0
        delta = round(charge - credit, 2)
        return {"status": "ok", "quote": {
            "current_price": current_price, "new_price": new_price,
            "period_days": round(total_days, 1), "remaining_days": round(remaining_days, 1),
            "credit": round(credit, 2), "charge": round(charge, 2),
            "net_delta": delta, "direction": "charge" if delta > 0 else "credit" if delta < 0 else "none",
        }}

    async def _apply_change(self, p: dict[str, Any]) -> dict[str, Any]:
        q = await self._quote(p)
        return {"status": "applied", "plan_from": p.get("current_plan"), "plan_to": p.get("new_plan"), **q["quote"]}


__all__ = ["MeteringService", "ProrationService", "THRESHOLDS_PCT"]
