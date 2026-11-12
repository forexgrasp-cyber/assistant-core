"""Customer intelligence services: Customer 360, benchmarks, goals, augmentation,
touchpoints, session recordings, voice of customer, service-due detection.

All universal — work on any customer record fields the tenant has.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from retention_analytics_core.repository import data_root
from retention_analytics_core.service_registry import ServiceRegistry

logger = structlog.get_logger(__name__)

# Industry benchmark baselines (Baremetrics Open Benchmarks style).
BENCHMARKS: dict[str, dict[str, float]] = {
    "saas": {"mrr_growth_rate": 0.12, "churn_rate": 0.035, "ltv_cac_ratio": 3.0, "nps": 30, "arpu": 99, "quick_ratio": 4.0, "net_revenue_retention": 105},
    "ecommerce": {"mrr_growth_rate": 0.08, "churn_rate": 0.06, "ltv_cac_ratio": 2.5, "nps": 40, "arpu": 65, "quick_ratio": 3.0, "net_revenue_retention": 100},
    "fitness": {"mrr_growth_rate": 0.10, "churn_rate": 0.08, "ltv_cac_ratio": 3.5, "nps": 45, "arpu": 40, "quick_ratio": 3.5, "net_revenue_retention": 102},
    "beauty": {"mrr_growth_rate": 0.09, "churn_rate": 0.07, "ltv_cac_ratio": 3.0, "nps": 50, "arpu": 55, "quick_ratio": 3.2, "net_revenue_retention": 101},
    "automotive": {"mrr_growth_rate": 0.06, "churn_rate": 0.04, "ltv_cac_ratio": 4.0, "nps": 42, "arpu": 180, "quick_ratio": 4.5, "net_revenue_retention": 106},
    "healthcare": {"mrr_growth_rate": 0.07, "churn_rate": 0.05, "ltv_cac_ratio": 3.8, "nps": 48, "arpu": 120, "quick_ratio": 3.8, "net_revenue_retention": 104},
    "default": {"mrr_growth_rate": 0.08, "churn_rate": 0.05, "ltv_cac_ratio": 3.0, "nps": 35, "arpu": 70, "quick_ratio": 3.0, "net_revenue_retention": 100},
}


class _JsonStore:
    """Small file-backed JSON store shared by the advanced services."""

    def __init__(self, filename: str) -> None:
        self.path = data_root() / filename

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        try:
            return json.loads(self.path.read_text())
        except Exception:
            return []

    def save(self, data: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, default=str))

    def upsert(self, key: str, record: dict[str, Any], match: str | None = None) -> None:
        """Insert or replace a record. ``match`` defaults to the ``key`` field name."""
        match_field = match or key
        data = [x for x in self.load() if x.get(match_field) != record.get(match_field)]
        data.append(record)
        self.save(data)


class Customer360Service:
    """Unified customer view: profile + timeline + touchpoints + recordings + enrichment.

    Mirrors Baremetrics People Insights and Churnkey Customer Timelines.
    """

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._profiles = _JsonStore("customer_profiles.json")
        self._touchpoints = _JsonStore("touchpoints.json")
        self._recordings = _JsonStore("session_recordings.json")
        self._enrichment = _JsonStore("customer_enrichment.json")

    def register(self) -> None:
        reg = self.registry.register("customers.360", version="1.0.0", metadata={"domain": "customers", "type": "platform"})
        reg.actions["upsert_profile"] = self._upsert_profile
        reg.actions["get_profile"] = self._get_profile
        reg.actions["list_profiles"] = self._list_profiles
        reg.actions["timeline"] = self._timeline
        reg.actions["log_touchpoint"] = self._log_touchpoint
        reg.actions["list_touchpoints"] = self._list_touchpoints
        reg.actions["link_recording"] = self._link_recording
        reg.actions["list_recordings"] = self._list_recordings
        reg.actions["enrich"] = self._enrich
        reg.actions["get_enrichment"] = self._get_enrichment

    async def _upsert_profile(self, p: dict[str, Any]) -> dict[str, Any]:
        profile = {
            "id": p.get("id") or p.get("client_id") or f"cust-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "name": p.get("name", ""),
            "email": p.get("email") or p.get("client_email", ""),
            "phone": p.get("phone", ""),
            "plan": p.get("plan", ""),
            "mrr": float(p.get("mrr", 0)),
            "ltv": float(p.get("ltv", 0)),
            "health_score": float(p.get("health_score", 100)),
            "last_service_date": p.get("last_service_date"),
            "service_interval_days": int(p.get("service_interval_days", 0)),
            "service_name": p.get("service_name", ""),
            "next_due_date": None,
            "days_until_due": None,
            "attributes": p.get("attributes", {}),
            "updated_at": datetime.now(UTC).isoformat(),
        }
        profile["next_due_date"], profile["days_until_due"] = compute_due(profile["last_service_date"], profile["service_interval_days"])
        self._profiles.upsert("id", profile)
        return {"status": "saved", "profile": profile}

    async def _get_profile(self, p: dict[str, Any]) -> dict[str, Any]:
        for prof in self._profiles.load():
            if prof.get("id") == p.get("id") or prof.get("email") == p.get("email"):
                enriched = dict(prof)
                enriched["enrichment"] = next((e for e in self._enrichment.load() if e.get("id") == prof.get("id")), {})
                enriched["touchpoints"] = [t for t in self._touchpoints.load() if t.get("customer_id") == prof.get("id")]
                enriched["recordings"] = [r for r in self._recordings.load() if r.get("customer_id") == prof.get("id")]
                return {"status": "ok", "profile": enriched}
        return {"status": "not_found"}

    async def _list_profiles(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        profiles = [x for x in self._profiles.load() if x.get("tenant_id") == tenant]
        return {"status": "ok", "profiles": profiles, "count": len(profiles)}

    async def _timeline(self, p: dict[str, Any]) -> dict[str, Any]:
        """Unified timeline: profile history + touchpoints + recordings + events."""
        cust_id = p.get("id", "")
        entries: list[dict[str, Any]] = []
        prof = next((x for x in self._profiles.load() if x.get("id") == cust_id), None)
        if prof:
            entries.append({"at": prof.get("updated_at"), "type": "profile_updated", "detail": prof.get("plan", "")})
        for t in self._touchpoints.load():
            if t.get("customer_id") == cust_id:
                entries.append({"at": t.get("at"), "type": t.get("type", "touchpoint"), "detail": t.get("summary", "")})
        for r in self._recordings.load():
            if r.get("customer_id") == cust_id:
                entries.append({"at": r.get("recorded_at"), "type": "session_recording", "detail": r.get("url", "")})
        entries.sort(key=lambda x: x.get("at") or "", reverse=True)
        return {"status": "ok", "customer_id": cust_id, "timeline": entries, "count": len(entries)}

    async def _log_touchpoint(self, p: dict[str, Any]) -> dict[str, Any]:
        tp = {
            "id": f"tp-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "customer_id": p.get("customer_id", ""),
            "type": p.get("type", "call"),  # call | meeting | email | note
            "summary": p.get("summary", ""),
            "outcome": p.get("outcome", ""),
            "at": p.get("at", datetime.now(UTC).isoformat()),
        }
        self._touchpoints.upsert("id", tp)
        return {"status": "logged", "touchpoint": tp}

    async def _list_touchpoints(self, p: dict[str[str, Any]]) -> dict[str, Any]:  # type: ignore[valid-type]
        cust_id = p.get("customer_id", "")
        return {"status": "ok", "touchpoints": [t for t in self._touchpoints.load() if t.get("customer_id") == cust_id]}

    async def _link_recording(self, p: dict[str, Any]) -> dict[str, Any]:
        rec = {
            "id": f"rec-{uuid.uuid4().hex[:12]}",
            "customer_id": p.get("customer_id", ""),
            "url": p.get("url", ""),
            "duration_seconds": int(p.get("duration_seconds", 0)),
            "events": p.get("events", []),
            "recorded_at": p.get("recorded_at", datetime.now(UTC).isoformat()),
        }
        self._recordings.upsert("id", rec)
        return {"status": "linked", "recording": rec}

    async def _list_recordings(self, p: dict[str, Any]) -> dict[str, Any]:
        cust_id = p.get("customer_id", "")
        return {"status": "ok", "recordings": [r for r in self._recordings.load() if r.get("customer_id") == cust_id]}

    async def _enrich(self, p: dict[str, Any]) -> dict[str, Any]:
        """Augmentation: merge external data into a customer profile (Baremetrics Augmentation)."""
        rec = {
            "id": p.get("id", ""),
            "tenant_id": p.get("tenant_id", ""),
            "source": p.get("source", "manual"),
            "company_name": p.get("company_name"),
            "industry": p.get("industry"),
            "employee_count": p.get("employee_count"),
            "country": p.get("country"),
            "timezone": p.get("timezone"),
            "custom": p.get("custom", {}),
            "enriched_at": datetime.now(UTC).isoformat(),
        }
        self._enrichment.upsert("id", rec)
        return {"status": "enriched", "enrichment": rec}

    async def _get_enrichment(self, p: dict[str, Any]) -> dict[str, Any]:
        for e in self._enrichment.load():
            if e.get("id") == p.get("id"):
                return {"status": "ok", "enrichment": e}
        return {"status": "not_found"}


def compute_due(last_service_date: str | None, interval_days: int) -> tuple[str | None, int | None]:
    """Compute next due date and days remaining from last service date + interval."""
    if not last_service_date or not interval_days:
        return None, None
    try:
        last = datetime.fromisoformat(last_service_date.replace("Z", "+00:00"))
        if last.tzinfo is None:
            last = last.replace(tzinfo=UTC)
        next_due = last + timedelta(days=interval_days)
        days = (next_due - datetime.now(UTC)).days
        return next_due.isoformat(), days
    except Exception:
        return None, None


class ServiceDueService:
    """Detects services due soon / overdue from customer records and triggers reminders.

    Universal: works for oil changes, beauty treatments, fitness subscriptions,
    annual renewals, maintenance, prescriptions — anything with a date + interval.
    """

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._profiles = _JsonStore("customer_profiles.json")
        self._reminders = _JsonStore("service_due_reminders.json")

    def register(self) -> None:
        reg = self.registry.register("customers.service_due", version="1.0.0", metadata={"domain": "customers", "type": "automation"})
        reg.actions["scan"] = self._scan
        reg.actions["list_due"] = self._list_due
        reg.actions["schedule_reminders"] = self._schedule
        reg.actions["mark_reminded"] = self._mark_reminded

    async def _scan(self, p: dict[str, Any]) -> dict[str, Any]:
        """Scan customer records for services due soon (within N days) or overdue."""
        tenant = p.get("tenant_id", "")
        within_days = int(p.get("within_days", 7))
        profiles = [x for x in self._profiles.load() if x.get("tenant_id") == tenant]
        due_soon, overdue = [], []
        for prof in profiles:
            days = prof.get("days_until_due")
            if days is None:
                nxt, days = compute_due(prof.get("last_service_date"), prof.get("service_interval_days", 0))
                prof["next_due_date"], prof["days_until_due"] = nxt, days
            if days is None:
                continue
            if days < 0:
                overdue.append(prof)
            elif days <= within_days:
                due_soon.append(prof)
        return {"status": "ok", "scanned": len(profiles), "due_soon": due_soon, "overdue": overdue,
                "due_soon_count": len(due_soon), "overdue_count": len(overdue)}

    async def _list_due(self, p: dict[str, Any]) -> dict[str, Any]:
        r = await self._scan(p)
        return {"status": "ok", "due_soon": r["due_soon"], "overdue": r["overdue"]}

    async def _schedule(self, p: dict[str, Any]) -> dict[str, Any]:
        """Create reminders for due/overdue services. Returns reminder records for flows to act on."""
        scan = await self._scan(p)
        tenant = p.get("tenant_id", "")
        created = []
        for prof in list(scan["due_soon"]) + list(scan["overdue"]):
            state = "overdue" if (prof.get("days_until_due") or 0) < 0 else "due_soon"
            rem = {
                "reminder_id": f"sdr-{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant,
                "customer_id": prof.get("id"),
                "customer_email": prof.get("email"),
                "service_name": prof.get("service_name") or "your service",
                "next_due_date": prof.get("next_due_date"),
                "days_until_due": prof.get("days_until_due"),
                "state": state,
                "status": "scheduled",
                "created_at": datetime.now(UTC).isoformat(),
            }
            self._reminders.upsert("reminder_id", rem)
            created.append(rem)
        logger.info("service_due.reminders_scheduled", count=len(created))
        return {"status": "scheduled", "reminders": created, "count": len(created)}

    async def _mark_reminded(self, p: dict[str, Any]) -> dict[str, Any]:
        data = self._reminders.load()
        for r in data:
            if r.get("reminder_id") == p.get("reminder_id"):
                r["status"] = "reminded"
                r["reminded_at"] = datetime.now(UTC).isoformat()
        self._reminders.save(data)
        return {"status": "reminded"}


class BenchmarksService:
    """Industry benchmark comparison. Mirrors Baremetrics Open Benchmarks."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def register(self) -> None:
        reg = self.registry.register("benchmarks", version="1.0.0", metadata={"domain": "analytics", "type": "platform"})
        reg.actions["list_industries"] = self._industries
        reg.actions["compare"] = self._compare
        reg.actions["set_industry"] = self._set_industry

    async def _industries(self, p: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "industries": {k: v for k, v in BENCHMARKS.items()}}

    async def _compare(self, p: dict[str, Any]) -> dict[str, Any]:
        industry = p.get("industry", "default")
        baseline = BENCHMARKS.get(industry, BENCHMARKS["default"])
        actual = p.get("metrics", {})
        rows = []
        for metric, bench in baseline.items():
            val = actual.get(metric)
            if val is None:
                continue
            if metric in ("churn_rate",):
                pct_diff = ((bench - val) / bench * 100) if bench else 0
                better = val <= bench
            elif metric == "ltv_cac_ratio":
                pct_diff = ((val - bench) / bench * 100) if bench else 0
                better = val >= bench
            else:
                pct_diff = ((val - bench) / bench * 100) if bench else 0
                better = val >= bench
            rows.append({"metric": metric, "your_value": val, "benchmark": bench,
                         "difference_pct": round(pct_diff, 1), "verdict": "better" if better else "worse"})
        return {"status": "ok", "industry": industry, "comparison": rows, "better_count": sum(1 for r in rows if r["verdict"] == "better")}

    async def _set_industry(self, p: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "industry": p.get("industry", "default"), "benchmark": BENCHMARKS.get(p.get("industry", ""), BENCHMARKS["default"])}


class GoalsService:
    """Business goal tracking with progress. Mirrors Baremetrics Goals."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._goals = _JsonStore("goals.json")

    def register(self) -> None:
        reg = self.registry.register("goals", version="1.0.0", metadata={"domain": "analytics", "type": "platform"})
        reg.actions["create"] = self._create
        reg.actions["list"] = self._list
        reg.actions["update_progress"] = self._update
        reg.actions["delete"] = self._delete

    async def _create(self, p: dict[str, Any]) -> dict[str, Any]:
        goal = {
            "goal_id": f"goal-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "name": p.get("name", ""),
            "metric": p.get("metric", "mrr"),
            "target": float(p.get("target", 0)),
            "current": float(p.get("current", 0)),
            "period": p.get("period", "quarterly"),
            "direction": p.get("direction", "increase"),  # increase | decrease
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._goals.upsert("goal_id", goal)
        return {"status": "created", "goal": goal}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        goals = [g for g in self._goals.load() if g.get("tenant_id") == tenant]
        for g in goals:
            if g["direction"] == "increase":
                g["progress_pct"] = round(min(g["current"] / g["target"] * 100, 100), 1) if g["target"] else 0
            else:
                g["progress_pct"] = round(min((g["target"] / g["current"] * 100) if g["current"] else 0, 100), 1)
            g["on_track"] = g["progress_pct"] >= 50
        return {"status": "ok", "goals": goals, "count": len(goals)}

    async def _update(self, p: dict[str[str, Any]]) -> dict[str, Any]:  # type: ignore[valid-type]
        data = self._goals.load()
        for g in data:
            if g.get("goal_id") == p.get("goal_id"):
                g["current"] = float(p.get("current", g.get("current", 0)))
                self._goals.save(data)
                return {"status": "updated", "goal": g}
        return {"status": "not_found"}

    async def _delete(self, p: dict[str[str, Any]]) -> dict[str, Any]:  # type: ignore[valid-type]
        self._goals.save([g for g in self._goals.load() if g.get("goal_id") != p.get("goal_id")])
        return {"status": "deleted"}


class VoiceOfCustomerService:
    """Public feedback board with upvoting and roadmap status. Churnkey/Gainsight VoC."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._items = _JsonStore("voc_items.json")

    def register(self) -> None:
        reg = self.registry.register("feedback.voc", version="1.0.0", metadata={"domain": "customers", "type": "platform"})
        reg.actions["submit"] = self._submit
        reg.actions["list"] = self._list
        reg.actions["upvote"] = self._upvote
        reg.actions["set_status"] = self._set_status

    async def _submit(self, p: dict[str, Any]) -> dict[str, Any]:
        item = {
            "id": f"voc-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "title": p.get("title", ""),
            "body": p.get("body", ""),
            "author": p.get("author", "anonymous"),
            "votes": 0,
            "status": "open",  # open | planned | shipped | closed
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._items.upsert("id", item)
        return {"status": "submitted", "item": item}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        items = [i for i in self._items.load() if i.get("tenant_id") == tenant]
        items.sort(key=lambda x: x.get("votes", 0), reverse=True)
        return {"status": "ok", "items": items, "count": len(items)}

    async def _upvote(self, p: dict[str, Any]) -> dict[str, Any]:
        data = self._items.load()
        for i in data:
            if i.get("id") == p.get("id"):
                i["votes"] = int(i.get("votes", 0)) + 1
                self._items.save(data)
                return {"status": "upvoted", "votes": i["votes"]}
        return {"status": "not_found"}

    async def _set_status(self, p: dict[str, Any]) -> dict[str, Any]:
        data = self._items.load()
        for i in data:
            if i.get("id") == p.get("id"):
                i["status"] = p.get("status", "open")
                self._items.save(data)
                return {"status": "updated", "item": i}
        return {"status": "not_found"}


__all__ = ["Customer360Service", "ServiceDueService", "BenchmarksService", "GoalsService", "VoiceOfCustomerService", "BENCHMARKS", "compute_due"]
