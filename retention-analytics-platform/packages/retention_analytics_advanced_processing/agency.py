"""Agency layer: an agency manages many client brands.

Hiro's wedge is the agency roster ("clarity across your client roster").
We match it and beat it: the same roster, plus campaigns/flows that actually
run against each client and prove the outcome.

Each client maps to a tenant_id inside the platform, so every existing service
(analytics, campaigns, flows, billing lifecycle) is already client-scoped.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from retention_analytics_advanced.customer_intel import _JsonStore
from retention_analytics_core.service_registry import ServiceRegistry

logger = structlog.get_logger(__name__)

CLIENT_STATUS = {
    "on_track": "On track",
    "behind_goal": "Behind goal",
    "revenue_down": "Revenue down",
    "deliverability": "Bounce rate high",
    "churn_risk": "Churn risk",
}

WEEKDAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6}


def _status_for(m: dict[str, Any], target: float, now: datetime) -> str:
    """Roster status from real metrics: deliverability > churn > pacing > on track."""
    if m.get("bounce_rate") and m["bounce_rate"] >= 0.01:
        return "deliverability"
    if m.get("churn_risk", 0) > 0:
        return "churn_risk"
    if target and m["revenue_mtd"] < target * min(now.day / 31, 1.0) * 0.8:
        return "behind_goal"
    return "on_track"


class AgencyService:
    """Multi-client roster with goals, pacing, status flags and sharing."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._clients = _JsonStore("agency_clients.json")
        self._shares = _JsonStore("agency_shares.json")
        self._digests = _JsonStore("agency_digests.json")
        self._actions = _JsonStore("agency_actions.json")

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
        reg.actions["send_digest"] = self._send_digest
        reg.actions["run_due_digests"] = self._run_due_digests
        reg.actions["client_report"] = self._client_report
        reg.actions["auto_act"] = self._auto_act

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
        """Pull the numbers for one client from its tenant's stores.

        Every source is optional enrichment: when a service is not registered
        the metric stays at its neutral zero/None default (never fabricated)
        and the gap is logged at debug level so it is observable.
        """
        tenant = client.get("tenant_id", "")
        out: dict[str, Any] = {"revenue_mtd": 0.0, "orders": 0, "active_subs": 0,
                                "churn_risk": 0, "open_alerts": 0, "bounce_rate": None, "at_risk_mrr": 0.0}

        async def _try(source: str, action: str, params: dict[str, Any], apply) -> None:
            try:
                r = await self.registry.invoke(source, action, params)
                apply(r)
            except Exception as exc:
                logger.debug("agency.client_metric_unavailable", source=source, action=action,
                             tenant=tenant, error=str(exc))

        await _try("analytics.commerce", "revenue_summary", {"tenant_id": tenant},
                   lambda r: out.__setitem__("revenue_mtd", r.get("revenue_mtd", 0.0)))
        await _try("saas.metrics", "compute_all", {"tenant_id": tenant, "subscriptions": []},
                   lambda r: out.__setitem__("active_subs", r.get("metrics", {}).get("mrr", {}).get("active_subscriptions", 0)))
        await _try("campaigns", "list", {"tenant_id": tenant},
                   lambda r: out.__setitem__("orders", len(r.get("campaigns", []))))
        await _try("ai.churn_predict", "at_risk_list", {"tenant_id": tenant, "threshold": 0.5},
                   lambda r: out.__setitem__("churn_risk", r.get("count", 0)))
        await _try("cs.alerts", "list_open", {"tenant_id": tenant},
                   lambda r: out.__setitem__("open_alerts", r.get("count", 0)))
        await _try("analytics.deliverability", "by_provider", {"tenant_id": tenant},
                   lambda r: out.__setitem__("bounce_rate", r.get("worst_bounce_rate")))
        await _try("segmentation.advanced", "preview",
                   {"tenant_id": tenant, "criteria": {"churn_risk_tier": ["critical", "high"]}},
                   lambda r: out.__setitem__("at_risk_mrr", r.get("aggregate", {}).get("total_mrr", 0)))
        return out

    async def _roster(self, p: dict[str, Any]) -> dict[str, Any]:
        """The agency roster: every client with pacing, status and what needs attention."""
        agency = p.get("agency_id", "default")
        clients = [c for c in self._clients.load() if c.get("agency_id") == agency]
        rows = []
        total_revenue = 0.0
        behind = 0
        now = datetime.now(UTC)
        for c in clients:
            m = await self._client_metrics(c)
            target = float(c.get("goal", {}).get("monthly_target") or 0)
            # month-to-date pacing: day-of-month / days-in-month
            day = now.day
            days_in_month = 31
            elapsed_ratio = min(day / days_in_month, 1.0)
            pacing = round(elapsed_ratio * 100, 1)
            revenue = m["revenue_mtd"]
            total_revenue += revenue
            goal_pct = round((revenue / target) * 100, 1) if target else None
            status = _status_for(m, target, now)
            if status == "behind_goal":
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

    def _digest_due_at(self, d: dict[str, Any], after: datetime) -> datetime:
        """First scheduled slot strictly after ``after`` for the digest's frequency."""
        hour = int(d.get("hour", 9))
        freq = d.get("frequency", "weekly")
        cand = after.replace(hour=hour, minute=0, second=0, microsecond=0)
        if freq == "daily":
            if cand <= after:
                cand += timedelta(days=1)
            return cand
        if freq == "weekly":
            target = WEEKDAYS.get(str(d.get("day", "monday")).lower(), 0)
            while cand.weekday() != target or cand <= after:
                cand += timedelta(days=1)
            return cand
        # monthly: day is day-of-month (default 1)
        try:
            dom = min(max(int(d.get("day", 1)), 1), 28)
        except (TypeError, ValueError):
            dom = 1
        cand = after.replace(day=1, hour=hour, minute=0, second=0, microsecond=0)
        while True:
            try:
                slot = cand.replace(day=dom)
            except ValueError:
                slot = cand.replace(day=28)
            if slot > after:
                return slot
            # next month
            cand = (cand.replace(day=1) + timedelta(days=32)).replace(day=1, hour=hour, minute=0, second=0, microsecond=0)

    async def _send_digest(self, p: dict[str, Any]) -> dict[str, Any]:
        """Build and send one client digest (Slack when available)."""
        digest = None
        digests = self._digests.load()
        if p.get("digest_id"):
            digest = next((d for d in digests if d.get("digest_id") == p["digest_id"]), None)
        elif p.get("client_id"):
            digest = next((d for d in digests if d.get("client_id") == p["client_id"] and d.get("active")), None)
        client = next((c for c in self._clients.load() if c.get("client_id") == (p.get("client_id") or (digest or {}).get("client_id"))), None)
        if not client:
            return {"status": "not_found"}
        m = await self._client_metrics(client)
        metrics = (digest or {}).get("metrics") or ["revenue_mtd", "churn_risk", "open_alerts"]

        def _fmt(metric: str) -> str:
            v = m.get(metric)
            if metric in ("revenue_mtd", "at_risk_mrr"):
                return f"{metric}: ${v:,.2f}" if isinstance(v, (int, float)) else f"{metric}: {v}"
            if metric == "bounce_rate":
                return f"bounce_rate: {v:.2%}" if isinstance(v, (int, float)) else "bounce_rate: n/a"
            return f"{metric}: {v}"

        text = f"Digest — {client.get('name', 'Client')}\n" + "\n".join(f"• {_fmt(k)}" for k in metrics)

        channel = p.get("channel") or (digest or {}).get("channel", "#client-updates")
        delivery = {"attempted": False, "status": "skipped"}
        try:
            r = await self.registry.invoke("integrations.slack", "send", {
                "tenant_id": client.get("tenant_id", ""), "channel": channel, "text": text})
            delivery = {"attempted": True, "status": r.get("status", "sent"), "message_id": r.get("message", {}).get("message_id")}
        except Exception as exc:
            logger.debug("agency.digest_slack_unavailable", error=str(exc))
            delivery = {"attempted": True, "status": "unavailable", "error": str(exc)}

        now_iso = datetime.now(UTC).isoformat()
        if digest:
            digest["last_sent_at"] = now_iso
            digest["last_channel"] = channel
            digest["last_metrics"] = m
            self._digests.upsert("digest_id", digest)
        return {"status": "sent" if delivery["status"] == "sent" else "built", "client_id": client["client_id"], "channel": channel, "text": text, "metrics": m, "delivery": delivery}

    async def _run_due_digests(self, p: dict[str, Any]) -> dict[str, Any]:
        """Send every active digest whose scheduled slot has passed."""
        now = datetime.now(UTC)
        if p.get("now"):
            now = datetime.fromisoformat(str(p["now"]).replace("Z", "+00:00"))
            if now.tzinfo is None:
                now = now.replace(tzinfo=UTC)
        agency = p.get("agency_id")
        results = []
        sent = skipped = 0
        data = self._digests.load()
        for d in data:
            if agency and d.get("agency_id") != agency:
                continue
            if not d.get("active", True):
                continue
            after = None
            if d.get("last_sent_at"):
                after = datetime.fromisoformat(str(d["last_sent_at"]).replace("Z", "+00:00"))
            elif d.get("created_at"):
                after = datetime.fromisoformat(str(d["created_at"]).replace("Z", "+00:00"))
            else:
                after = now - timedelta(days=1)
            if after.tzinfo is None:
                after = after.replace(tzinfo=UTC)
            due = self._digest_due_at(d, after)
            if now >= due:
                r = await self._send_digest({"digest_id": d.get("digest_id")})
                sent += 1
                results.append({"digest_id": d.get("digest_id"), "client_id": d.get("client_id"), "sent": True, "status": r.get("status"), "channel": r.get("channel")})
            else:
                skipped += 1
                results.append({"digest_id": d.get("digest_id"), "client_id": d.get("client_id"), "sent": False, "next_due_at": due.isoformat()})
        # persist next_due_at for all
        fresh = self._digests.load()
        for d in fresh:
            base = d.get("last_sent_at") or d.get("created_at")
            if base:
                b = datetime.fromisoformat(str(base).replace("Z", "+00:00"))
                if b.tzinfo is None:
                    b = b.replace(tzinfo=UTC)
                d["next_due_at"] = self._digest_due_at(d, b).isoformat()
                self._digests.upsert("digest_id", d)
        return {"status": "ok", "sent": sent, "skipped": skipped, "results": results}

    async def _auto_act(self, p: dict[str, Any]) -> dict[str, Any]:
        """Act on clients needing attention: fire a CS alert and post a Slack heads-up.

        Actions are derived from real roster status (never fabricated); every action
        is recorded in agency_actions.json for audit.
        """
        agency = p.get("agency_id", "default")
        clients = [c for c in self._clients.load() if c.get("agency_id") == agency]
        if p.get("client_id"):
            clients = [c for c in clients if c.get("client_id") == p["client_id"]]
        taken = []
        now = datetime.now(UTC)
        for c in clients:
            m = await self._client_metrics(c)
            target = float(c.get("goal", {}).get("monthly_target") or 0)
            status = _status_for(m, target, now)
            if status == "on_track":
                continue
            client_actions = []
            # 1. CS alert (optional service)
            try:
                r = await self.registry.invoke("cs.alerts", "fire", {
                    "tenant_id": c.get("tenant_id", ""), "client_id": c["client_id"],
                    "type": f"agency_{status}", "severity": "high" if status in ("churn_risk", "deliverability") else "medium",
                    "title": f"{c.get('name')}: {CLIENT_STATUS.get(status, status)}",
                    "detail": f"revenue_mtd={m['revenue_mtd']}, churn_risk={m['churn_risk']}, open_alerts={m['open_alerts']}, at_risk_mrr={m['at_risk_mrr']}"})
                client_actions.append({"action": "cs_alert", "status": r.get("status", "fired")})
            except Exception as exc:
                logger.debug("agency.auto_act_alert_unavailable", error=str(exc))
            # 2. Slack heads-up (optional service)
            try:
                r = await self.registry.invoke("integrations.slack", "send", {
                    "tenant_id": c.get("tenant_id", ""), "channel": p.get("channel", "#agency-alerts"),
                    "text": f":warning: *{c.get('name')}* — {CLIENT_STATUS.get(status, status)}\n• revenue_mtd: ${m['revenue_mtd']:,.2f} (goal ${target:,.0f})\n• churn_risk: {m['churn_risk']} • open_alerts: {m['open_alerts']} • at_risk_mrr: ${m['at_risk_mrr']:,.2f}"})
                client_actions.append({"action": "slack_alert", "status": r.get("status", "sent")})
            except Exception as exc:
                logger.debug("agency.auto_act_slack_unavailable", error=str(exc))
            # 3. win-back campaign run if churn risk and an active reduce_churn campaign exists
            if status == "churn_risk":
                try:
                    camps = await self.registry.invoke("campaigns", "list", {"tenant_id": c.get("tenant_id", "")})
                    winback = next((x for x in camps.get("campaigns", []) if x.get("status") == "active" and x.get("goal") in ("reduce_churn", "win_back")), None)
                    if winback:
                        r = await self.registry.invoke("campaigns", "run", {"campaign_id": winback["campaign_id"], "clients": []})
                        client_actions.append({"action": "campaign_run", "campaign_id": winback["campaign_id"], "status": r.get("status")})
                except Exception as exc:
                    logger.debug("agency.auto_act_campaign_unavailable", error=str(exc))
            record = {"action_id": f"act-{uuid.uuid4().hex[:10]}", "client_id": c["client_id"],
                      "agency_id": agency, "status": status, "actions": client_actions,
                      "metrics": m, "at": now.isoformat()}
            self._actions.upsert("action_id", record)
            taken.append(record)
        return {"status": "ok", "acted": len(taken), "clients": [{"client_id": r["client_id"], "status": r["status"], "actions": r["actions"]} for r in taken]}


__all__ = ["AgencyService", "CLIENT_STATUS"]
