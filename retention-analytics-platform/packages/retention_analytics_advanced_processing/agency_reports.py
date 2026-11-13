"""Natural-language per-client Q&A + role views + branded report deck.

Answers agency questions like "which clients are behind this month?" directly
from live data, and produces the role-specific views Hiro sells (leadership /
account manager / copywriter) plus a branded PDF report deck.
"""

from __future__ import annotations

import html as html_lib
import json
import re
from datetime import UTC, datetime
from typing import Any

import structlog

from retention_analytics_core.service_registry import ServiceRegistry

logger = structlog.get_logger(__name__)

# Intent patterns -> handler key. Ordered: first match wins.
INTENTS = [
    (r"behind|pacing|goal|behind goal", "clients_behind"),
    (r"revenue|mrr|arr|money|spend", "revenue_overview"),
    (r"churn|risk|at risk|losing", "churn_risk"),
    (r"alert|incident|problem|issue|error", "open_alerts"),
    (r"deliverab|bounce|spam|inbox", "deliverability"),
    (r"best|worst|top|rank|creative|subject", "top_performers"),
    (r"renew|expiring|upcoming", "renewals"),
    (r"client|roster|portfolio|all clients", "roster"),
]


class AgencyQAService:
    """Plain-English questions answered from live roster data."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def register(self) -> None:
        reg = self.registry.register("agency.qa", version="1.0.0", metadata={"domain": "agency", "type": "ai"})
        reg.actions["ask"] = self._ask
        reg.actions["intents"] = self._intents
        reg.actions["suggestions"] = self._suggestions

    async def _intents(self, p: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "intents": [{"intent": k, "pattern": pat} for pat, k in INTENTS]}

    async def _suggestions(self, p: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "questions": [
            "Which clients are behind their revenue goal this month?",
            "What is total attributed revenue across all clients?",
            "Which clients have customers at churn risk?",
            "What is the deliverability score by client?",
            "Which campaign performs best per recipient?",
            "Which clients have renewals coming up?",
        ]}

    async def _ask(self, p: dict[str, Any]) -> dict[str, Any]:
        question = (p.get("question") or "").strip()
        agency_id = p.get("agency_id", "default")
        q = question.lower()
        intent = "roster"
        for pattern, key in INTENTS:
            if re.search(pattern, q):
                intent = key
                break
        handler = getattr(self, f"_h_{intent}")
        answer = await handler(agency_id, p)
        return {"status": "ok", "question": question, "intent": intent, **answer}

    async def _h_roster(self, agency_id: str, p: dict[str, Any]) -> dict[str, Any]:
        r = await self.registry.invoke("agency", "roster", {"agency_id": agency_id})
        return {"answer": f"{r['count']} clients on the roster. "
                          f"{r['summary']['behind_goal']} behind goal, "
                          f"{r['summary']['needs_attention']} need attention, "
                          f"${r['summary']['total_revenue_mtd']:,.0f} revenue MTD.",
                "data": r}

    async def _h_clients_behind(self, agency_id: str, p: dict[str, Any]) -> dict[str, Any]:
        r = await self.registry.invoke("agency", "roster", {"agency_id": agency_id})
        behind = [c for c in r["clients"] if c.get("behind_goal")]
        rows = [{"client": c["name"], "to_date": c.get("revenue_mtd", 0),
                 "goal": c.get("goal", {}).get("monthly_target", 0),
                 "pacing_pct": c.get("goal_pct"), "month_pct": c.get("pacing_pct")} for c in behind]
        answer = (f"{len(behind)} client{'s' if len(behind) != 1 else ''} behind goal this month."
                  if behind else "No clients are behind goal this month.")
        return {"answer": answer, "data": {"behind_goal": rows}}

    async def _h_revenue_overview(self, agency_id: str, p: dict[str, Any]) -> dict[str, Any]:
        r = await self.registry.invoke("agency", "roster", {"agency_id": agency_id})
        total = r["summary"]["total_revenue_mtd"]
        top = sorted(r["clients"], key=lambda c: -(c.get("revenue_mtd") or 0))[:5]
        return {"answer": f"Total attributed revenue MTD: ${total:,.0f} across {r['count']} clients. "
                          f"Top: " + ", ".join(f"{c['name']} (${c.get('revenue_mtd', 0):,.0f})" for c in top),
                "data": {"total": total, "top_clients": top}}

    async def _h_churn_risk(self, agency_id: str, p: dict[str, Any]) -> dict[str, Any]:
        r = await self.registry.invoke("agency", "roster", {"agency_id": agency_id})
        rows = [{"client": c["name"], "at_risk": c.get("churn_risk", 0),
                 "mrr_at_risk": c.get("at_risk_mrr", 0)} for c in r["clients"] if c.get("churn_risk")]
        rows.sort(key=lambda x: -x["at_risk"])
        total = sum(x["at_risk"] for x in rows)
        return {"answer": f"{total} customers are at churn risk across {len(rows)} clients. "
                          + (", ".join(f"{x['client']}: {x['at_risk']}" for x in rows[:3]) if rows else ""),
                "data": {"at_risk": rows}}

    async def _h_open_alerts(self, agency_id: str, p: dict[str, Any]) -> dict[str, Any]:
        r = await self.registry.invoke("agency", "roster", {"agency_id": agency_id})
        rows = [{"client": c["name"], "alerts": c.get("open_alerts", 0)} for c in r["clients"] if c.get("open_alerts")]
        total = r["summary"]["total_open_alerts"]
        return {"answer": f"{total} open alerts across the roster."
                          + ((" " + ", ".join(f"{x['client']}: {x['alerts']}" for x in rows[:3])) if rows else ""),
                "data": {"alerts": rows}}

    async def _h_deliverability(self, agency_id: str, p: dict[str, Any]) -> dict[str, Any]:
        r = await self.registry.invoke("agency", "roster", {"agency_id": agency_id})
        rows = [{"client": c["name"], "bounce_rate": c.get("bounce_rate")} for c in r["clients"] if c.get("bounce_rate")]
        worst = max(rows, key=lambda x: x["bounce_rate"]) if rows else None
        answer = (f"Worst inbox delivery: {worst['client']} at {worst['bounce_rate']}% bounce." if worst
                  else "No deliverability issues detected.")
        return {"answer": answer, "data": {"by_client": rows}}

    async def _h_top_performers(self, agency_id: str, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        r = await self.registry.invoke("analytics.performance", "campaign_deep_dive", {"tenant_id": tenant})
        sends = sorted(r.get("sends", []), key=lambda s: -(s.get("revenue_per_recipient") or 0))[:5]
        if not sends:
            return {"answer": "No campaign performance recorded yet.", "data": {}}
        top = sends[0]
        return {"answer": f"Best performer: “{top['subject']}” at ${top['revenue_per_recipient']} per recipient "
                          f"({top['open_rate']}% open, ${top['revenue']} revenue).",
                "data": {"ranked": sends}}

    async def _h_renewals(self, agency_id: str, p: dict[str, Any]) -> dict[str, Any]:
        r = await self.registry.invoke("agency", "roster", {"agency_id": agency_id})
        rows = [{"client": c["name"], "forecast_arr": c.get("renewal_forecast_arr", 0)} for c in r["clients"]]
        return {"answer": f"Renewal forecast tracked for {len(rows)} clients.", "data": {"renewals": rows}}


class RoleViewService:
    """Role-specific views: leadership, account manager, copywriter."""

    ROLES = ["leadership", "account_manager", "copywriter"]

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def register(self) -> None:
        reg = self.registry.register("agency.roles", version="1.0.0", metadata={"domain": "agency", "type": "reporting"})
        reg.actions["view"] = self._view
        reg.actions["roles"] = self._roles

    async def _roles(self, p: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "roles": self.ROLES}

    async def _view(self, p: dict[str, Any]) -> dict[str, Any]:
        role = p.get("role", "leadership")
        agency_id = p.get("agency_id", "default")
        if role == "leadership":
            return await self._leadership(agency_id)
        if role == "account_manager":
            return await self._account_manager(agency_id, p)
        if role == "copywriter":
            return await self._copywriter(p)
        return {"status": "ok", "role": role, "error": "unknown role"}

    async def _leadership(self, agency_id: str) -> dict[str, Any]:
        r = await self.registry.invoke("agency", "roster", {"agency_id": agency_id})
        return {"status": "ok", "role": "leadership", "headline": {
            "revenue_mtd": r["summary"]["total_revenue_mtd"],
            "behind_goal": r["summary"]["behind_goal"],
            "needs_attention": r["summary"]["needs_attention"],
            "churn_risk": r["summary"]["total_churn_risk"],
            "mrr_at_risk": r["summary"]["total_at_risk_mrr"],
        }, "clients": [{"name": c["name"], "status": c["status"], "status_label": c["status_label"],
                        "revenue_mtd": c.get("revenue_mtd"), "goal_pct": c.get("goal_pct")} for c in r["clients"]]}

    async def _account_manager(self, agency_id: str, p: dict[str, Any]) -> dict[str, Any]:
        client_id = p.get("client_id", "")
        roster = await self.registry.invoke("agency", "roster", {"agency_id": agency_id})
        client = next((c for c in roster["clients"] if c["client_id"] == client_id), None)
        if not client:
            return {"status": "ok", "role": "account_manager", "error": "client not found"}
        report = await self.registry.invoke("agency", "client_report", {"tenant_id": client.get("tenant_id", "")})
        return {"status": "ok", "role": "account_manager", "client": {
            "name": client["name"], "status": client["status"], "status_label": client["status_label"],
            "revenue_mtd": client.get("revenue_mtd"), "goal": client.get("goal"),
            "pacing_pct": client.get("pacing_pct"), "churn_risk": client.get("churn_risk"),
            "open_alerts": client.get("open_alerts"),
        }, "report": report.get("report", {})}

    async def _copywriter(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        timing = await self.registry.invoke("analytics.performance", "message_timing", {"tenant_id": tenant})
        dive = await self.registry.invoke("analytics.performance", "campaign_deep_dive", {"tenant_id": tenant})
        subjects = timing.get("subjects_ranked", [])[:10]
        best_slot = None
        modes = timing.get("modes", {})
        for mode, data in modes.items():
            if data.get("best_slot"):
                best_slot = {"mode": mode, **data["best_slot"]}
        sends = sorted(dive.get("sends", []), key=lambda s: -(s.get("open_rate") or 0))[:10]
        return {"status": "ok", "role": "copywriter", "headline": {
            "best_slot": best_slot,
            "best_subject": subjects[0]["subject"] if subjects else None,
            "creative_count": len(dive.get("sends", [])),
        }, "subjects": subjects, "sends_by_open_rate": sends}


class ReportDeckService:
    """Branded, multi-slide report deck (agency-branded, exportable as HTML->PDF)."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def register(self) -> None:
        reg = self.registry.register("agency.deck", version="1.0.0", metadata={"domain": "agency", "type": "reporting"})
        reg.actions["build"] = self._build
        reg.actions["render_html"] = self._render_html

    async def _build(self, p: dict[str, Any]) -> dict[str, Any]:
        """Assemble the deck slides from live data."""
        client_id = p.get("client_id", "")
        agency_id = p.get("agency_id", "default")
        roster = await self.registry.invoke("agency", "roster", {"agency_id": agency_id})
        client = next((c for c in roster["clients"] if c["client_id"] == client_id), None)
        if not client:
            return {"status": "not_found", "error": "client not found"}
        tenant = client.get("tenant_id", "")
        report = await self.registry.invoke("agency", "client_report", {"tenant_id": tenant})
        slides = [
            {"kind": "title", "title": f"{client['name']} — retention report",
             "subtitle": f"{p.get('period', 'This month')} · prepared by Snapford Retention"},
            {"kind": "metrics", "title": "The numbers", "items": [
                {"label": "Revenue MTD", "value": f"${client.get('revenue_mtd', 0):,.0f}"},
                {"label": "Goal", "value": f"${client.get('goal', {}).get('monthly_target', 0):,.0f}"},
                {"label": "Pacing", "value": f"{client.get('goal_pct') or 0}% of goal"},
                {"label": "Status", "value": client.get("status_label", "")},
            ]},
            {"kind": "retention", "title": "Retention",
             "retention": report.get("report", {}).get("retention", {})},
            {"kind": "campaigns", "title": "Campaigns that ran", "campaigns": report.get("report", {}).get("campaigns", [])},
            {"kind": "closing", "title": "What we recommend next",
             "items": [{"label": "Action", "value": "Keep the win-back flow live for at-risk accounts"},
                       {"label": "Owner", "value": "Account manager"}]},
        ]
        deck = {"deck_id": f"deck-{client_id}", "client_id": client_id, "agency_id": agency_id,
                "branding": client.get("branding", {}), "period": p.get("period", "This month"),
                "slides": slides, "built_at": datetime.now(UTC).isoformat()}
        return {"status": "ok", "deck": deck}

    async def _render_html(self, p: dict[str, Any]) -> dict[str, Any]:
        deck = p.get("deck")
        if not deck:
            return await self._build(p)
        brand = deck.get("branding", {})
        accent = brand.get("primary_color", "#4f46e5")
        company = brand.get("company_name", "Client")
        slide_html = []
        for s in deck.get("slides", []):
            body = []
            if s["kind"] == "title":
                body.append(f"<h1>{html_lib.escape(s['title'])}</h1>")
                body.append(f"<p class='sub'>{html_lib.escape(s.get('subtitle', ''))}</p>")
            elif s["kind"] == "metrics":
                items = "".join(f"<div class='m'><b>{html_lib.escape(str(i['value']))}</b><span>{html_lib.escape(i['label'])}</span></div>"
                                for i in s.get("items", []))
                body.append(f"<h2>{html_lib.escape(s['title'])}</h2><div class='metrics'>{items}</div>")
            elif s["kind"] == "retention":
                r = s.get("retention", {})
                body.append(f"<h2>{html_lib.escape(s['title'])}</h2>")
                body.append(f"<p class='big'>{round((r.get('retention_rate_30d') or 0) * 100, 1)}%</p><p class='sub'>30-day retention</p>")
            elif s["kind"] == "campaigns":
                rows = "".join(f"<tr><td>{html_lib.escape(str(c.get('name')))}</td><td>{html_lib.escape(str(c.get('status')))}</td></tr>"
                               for c in s.get("campaigns", []))
                body.append(f"<h2>{html_lib.escape(s['title'])}</h2><table>{rows}</table>")
            else:
                items = "".join(f"<div class='m'><b>{html_lib.escape(str(i['value']))}</b><span>{html_lib.escape(i['label'])}</span></div>"
                                for i in s.get("items", []))
                body.append(f"<h2>{html_lib.escape(s['title'])}</h2><div class='metrics'>{items}</div>")
            slide_html.append(f"<section class='slide'>{''.join(body)}</section>")

        doc = f"""<!DOCTYPE html><html><head><meta charset='utf-8'/><title>{html_lib.escape(company)} — retention report</title>
<style>
@page {{ size: A4 landscape; margin: 12mm; }}
body {{ font-family: system-ui, sans-serif; margin: 0; color: #0f172a; }}
.slide {{ page-break-after: always; border: 1px solid #e2e8f0; border-radius: 8px; padding: 28px; margin: 12px; min-height: 70vh; }}
h1 {{ font-size: 30px; margin: 40px 0 6px; }}
h2 {{ font-size: 19px; margin: 0 0 14px; }}
.sub {{ color: #64748b; }}
.big {{ font-size: 48px; font-weight: 700; color: {accent}; margin: 12px 0 0; }}
.metrics {{ display: flex; gap: 14px; flex-wrap: wrap; }}
.m {{ border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 18px; min-width: 150px; }}
.m b {{ display: block; font-size: 24px; color: {accent}; }}
.m span {{ font-size: 12px; color: #64748b; }}
table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
td {{ padding: 6px 8px; border-bottom: 1px solid #f1f5f9; }}
.brand {{ position: fixed; top: 8px; right: 14px; font-size: 11px; color: #94a3b8; }}
</style></head><body>
<div class='brand'>{html_lib.escape(company)} · prepared by Snapford Retention</div>
{''.join(slide_html)}
</body></html>"""
        return {"status": "ok", "html": doc, "slides": len(deck.get("slides", [])),
                "print_to_pdf": "open in a browser and print to PDF (A4 landscape)"}


__all__ = ["AgencyQAService", "RoleViewService", "ReportDeckService", "INTENTS"]
