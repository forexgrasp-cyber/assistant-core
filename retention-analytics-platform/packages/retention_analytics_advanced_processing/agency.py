"""Agency layer: an agency manages many client brands.

Hiro's wedge is the agency roster ("clarity across your client roster").
We match it and beat it: the same roster, plus campaigns/flows that actually
run against each client and prove the outcome.

Each client maps to a tenant_id inside the platform, so every existing service
(analytics, campaigns, flows, billing lifecycle) is already client-scoped.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from retention_analytics_core.repository import data_root
from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced.customer_intel import _JsonStore

logger = structlog.get_logger(__name__)

CLIENT_STATUS = {
    "on_track": "On track",
    "behind_goal": "Behind goal",
    "revenue_down": "Revenue down",
    "deliverability": "Bounce rate high",
    "churn_risk": "Churn risk",
}


class AgencyService:
    """Multi-client roster with goals, pacing, status flags and sharing."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._clients = _JsonStore("agency_clients.json")
        self._shares = _JsonStore("agency_shares.json")
        self._digests = _JsonStore("agency_digests.json")

    def register(self) -> None:
        reg = self.registry.register("agency", version="1.0.0", metadata={"domain": "agency", "type": "platform"})
        reg.actions["create_client"] = self._create_client
        reg.actions["list_clients"] = self._list_clients
        reg.actions["get_client"] = self._get_client
        reg.actions["update_client"] = self._update_client
        reg.actions["delete_client"] = self._delete_client
        reg.actions["roster"] = self._roster
        reg.actions["set_goal"] = self._set_goal
        reg.actions["share_dashboard"] = self._share
        reg.actions["list_shares"] = self._list_shares
        reg.actions["revoke_share"] = self._revoke
        reg.actions["schedule_digest"] = self._schedule_digest
        reg.actions["list_digests"] = self._list_digests
        reg.actions["client_report"] = self._client_report

    # ------------------------------------------------------------ clients
    async def _create_client(self, p: dict[str, Any]) -> dict[str, Any]:
        client = {
            "client_id": p.get("client_id") or f"cli-{uuid.uuid4().hex[:10]}",
            "agency_id": p.get("agency_id", "default"),
            "tenant_id": p.get("tenant_id", ""),  # where this client's data lives
            "name": p.get("name", "Client"),
            "slug": p.get("slug", ""),
            "branding": {
                "company_name": p.get("name", "Client"),
                "primary_color": p.get("primary_color", "#4f46e5"),
                "logo_url": p.get("logo_url", ""),
            },
            "goal": {
                "metric": p.get("goal_metric", "revenue"),
                "monthly_target": float(p.get("monthly_target", 0)),
                "period": p.get("period", "monthly"),
            },
            "platforms": p.get("platforms", []),  # connected marketing platforms
            "status": "on_track",
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._clients.upsert("client_id", client)
        logger.info("agency.client_created", client_id=client["client_id"], name=client["name"])
        return {"status": "created", "client": client}

    async def _list_clients(self, p: dict[str, Any]) -> dict[str, Any]:
        agency = p.get("agency_id", "default")
        rows = [c for c in self._clients.load() if c.get("agency_id") == agency]
        return {"status": "ok", "clients": rows, "count": len(rows)}

    async def _get_client(self, p: dict[str, Any]) -> dict[str, Any]:
        for c in self._clients.load():
            if c.get("client_id") == p.get("client_id"):
                return {"status": "ok", "client": c}
        return {"status": "not_found"}

    async def _update_client(self, p: dict[str, Any]) -> dict[str, Any]:
        data = self._clients.load()
        for c in data:
            if c.get("client_id") == p.get("client_id"):
                for k in ("name", "slug", "branding", "goal", "platforms", "tenant_id"):
                    if k in p:
                        c[k] = p[k]
                c["updated_at"] = datetime.now(UTC).isoformat()
                self._clients.save(data)
                return {"status": "updated", "client": c}
        return {"status": "not_found"}

    async def _delete_client(self, p: dict[str, Any]) -> dict[str, Any]:
        self._clients.save([c for c in self._clients.load() if c.get("client_id") != p.get("client_id")])
        return {"status": "deleted"}

    async def _set_goal(self, p: dict[str, Any]) -> dict[str, Any]:
        data = self._clients.load()
        for c in data:
            if c.get("client_id") == p.get("client_id"):
                c["goal"] = {"metric": p.get("metric", "revenue"),
                              "monthly_target": float(p.get("monthly_target", 0)),
                              "period": p.get("period", "monthly")}
                self._clients.save(data)
                return {"status": "ok", "goal": c["goal"]}
        return {"status": "not_found"}

    # ------------------------------------------------------------ roster
    async def _client_metrics(self, client: dict[str, Any]) -> dict[str, Any]:
        """Pull the numbers for one client from its tenant's stores."""
        tenant = client.get("tenant_id", "")
        out: dict[str, Any] = {"revenue_mtd": 0.0, "orders": 0, "active_subs": 0,
                                "churn_risk": 0, "open_alerts": 0, "bounce_rate": None, "at_risk_mrr": 0.0}
        try:
            r = await self.registry.invoke("saas.metrics", "compute_all", {
                "tenant_id": tenant, "subscriptions": []})
            m = r.get("metrics", {})
            out["active_subs"] = m.get("mrr", {}).get("active_subscriptions", 0)
        except Exception:
            pass
        try:
            r = await self.registry.invoke("campaigns", "list", {"tenant_id": tenant})
            out["orders"] = len(r.get("campaigns", []))
        except Exception:
            pass
        try:
            r = await self.registry.invoke("ai.churn_predict", "at_risk_list", {"tenant_id": tenant, "threshold": 0.5})
            out["churn_risk"] = r.get("count", 0)
        except Exception:
            pass
        try:
            r = await self.registry.invoke("cs.alerts", "list_open", {"tenant_id": tenant})
            out["open_alerts"] = r.get("count", 0)
        except Exception:
            pass
        try:
            r = await self.registry.invoke("analytics.deliverability", "by_provider", {"tenant_id": tenant})
            out["bounce_rate"] = r.get("worst_bounce_rate")
        except Exception:
            pass
        try:
            r = await self.registry.invoke("segmentation.advanced", "preview", {
                "tenant_id": tenant, "criteria": {"churn_risk_tier": ["critical", "high"]}})
            out["at_risk_mrr"] = r.get("aggregate", {}).get("total_mrr", 0)
        except Exception:
            pass
        return out

    async def _roster(self, p: dict[str, Any]) -> dict[str, Any]:
        """The agency roster: every client with pacing, status and what needs attention."""
        agency = p.get("agency_id", "default")
        clients = [c for c in self._clients.load() if c.get("agency_id") == agency]
        rows = []
        total_revenue = 0.0
        behind = 0
        for c in clients:
            m = await self._client_metrics(c)
            target = float(c.get("goal", {}).get("monthly_target") or 0)
            # month-to-date pacing: day-of-month / days-in-month
            now = datetime.now(UTC)
            day = now.day
            days_in_month = 31
            elapsed_ratio = min(day / days_in_month, 1.0)
            pacing = round(elapsed_ratio * 100, 1)
            revenue = m["revenue_mtd"]
            total_revenue += revenue
            goal_pct = round((revenue / target) * 100, 1) if target else None
            status = "on_track"
            if m.get("bounce_rate") and m["bounce_rate"] >= 0.01:
                status = "deliverability"
            elif m.get("churn_risk", 0) > 0:
                status = "churn_risk"
            elif target and revenue < target * elapsed_ratio * 0.8:
                status = "behind_goal"
                behind += 1
            rows.append({
                **c, **m, "revenue_mtd": revenue, "goal_pct": goal_pct,
                "pacing_pct": pacing, "status": status, "status_label": CLIENT_STATUS.get(status, status),
                "behind_goal": status == "behind_goal",
            })
        rows.sort(key=lambda r: (r["status"] != "behind_goal", -(r.get("revenue_mtd") or 0)))
        return {
            "status": "ok",
            "agency_id": agency,
            "clients": rows,
            "count": len(rows),
            "summary": {
                "total_revenue_mtd": round(total_revenue, 2),
                "behind_goal": behind,
                "needs_attention": sum(1 for r in rows if r["status"] != "on_track"),
                "total_churn_risk": sum(r.get("churn_risk", 0) for r in rows),
                "total_open_alerts": sum(r.get("open_alerts", 0) for r in rows),
                "total_at_risk_mrr": round(sum(r.get("at_risk_mrr", 0) for r in rows), 2),
            },
        }

    # ------------------------------------------------------------ sharing
    async def _share(self, p: dict[str, Any]) -> dict[str, Any]:
        """Create a white-label, tokenised client dashboard link."""
        client_id = p.get("client_id", "")
        client = next((c for c in self._clients.load() if c.get("client_id") == client_id), None)
        if not client:
            return {"status": "not_found"}
        share = {
            "share_id": f"shr-{uuid.uuid4().hex[:12]}",
            "token": uuid.uuid4().hex,
            "client_id": client_id,
            "tenant_id": client.get("tenant_id", ""),
            "branding": client.get("branding", {}),
            "expires_at": p.get("expires_at"),
            "views": 0,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._shares.upsert("share_id", share)
        return {"status": "created", "share": {**share, "url": f"/share/{share['token']}"}}

    async def _list_shares(self, p: dict[str, Any]) -> dict[str, Any]:
        rows = [s for s in self._shares.load() if not p.get("client_id") or s.get("client_id") == p["client_id"]]
        return {"status": "ok", "shares": rows, "count": len(rows)}

    async def _revoke(self, p: dict[str, Any]) -> dict[str, Any]:
        self._shares.save([s for s in self._shares.load() if s.get("share_id") != p.get("share_id")])
        return {"status": "revoked"}

    async def _client_report(self, p: dict[str, Any]) -> dict[str, Any]:
        """The numbers a client sees on their shared dashboard."""
        tenant = p.get("tenant_id", "")
        branding = p.get("branding", {})
        report: dict[str, Any] = {"branding": branding, "generated_at": datetime.now(UTC).isoformat()}
        try:
            r = await self.registry.invoke("saas.metrics", "compute_all", {"tenant_id": tenant, "subscriptions": []})
            report["saas"] = r.get("metrics", {})
        except Exception:
            report["saas"] = {}
        try:
            r = await self.registry.invoke("analytics.metric", "compute_retention", {"tenant_id": tenant})
            report["retention"] = r.get("result", r)
        except Exception:
            report["retention"] = {}
        try:
            r = await self.registry.invoke("campaigns", "list", {"tenant_id": tenant})
            report["campaigns"] = [{"name": c.get("name"), "status": c.get("status"),
                                    "flows": c.get("flows", []),
                                    "results": (c.get("results") or {}).get("deltas")} for c in r.get("campaigns", [])]
        except Exception:
            report["campaigns"] = []
        return {"status": "ok", "report": report}

    # ------------------------------------------------------------ digests
    async def _schedule_digest(self, p: dict[str, Any]) -> dict[str, Any]:
        """Schedule a recurring Slack digest for a client (Hiro's 'Slack updates')."""
        d = {
            "digest_id": f"dig-{uuid.uuid4().hex[:10]}",
            "client_id": p.get("client_id", ""),
            "agency_id": p.get("agency_id", "default"),
            "frequency": p.get("frequency", "weekly"),  # daily | weekly | monthly
            "day": p.get("day", "monday"),
            "hour": int(p.get("hour", 9)),
            "channel": p.get("channel", "#client-updates"),
            "metrics": p.get("metrics", ["revenue_mtd", "churn_risk", "open_alerts"]),
            "active": True,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._digests.upsert("digest_id", d)
        return {"status": "scheduled", "digest": d}

    async def _list_digests(self, p: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "digests": self._digests.load()}


__all__ = ["AgencyService", "CLIENT_STATUS"]
