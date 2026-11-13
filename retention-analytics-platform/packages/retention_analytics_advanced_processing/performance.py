"""The analytics screens Hiro sells — our versions, on our own data.

- Flow map performance: per-message delivered/open/click/revenue with creative
- Campaign deep dive: creative + subject next to open/click/revenue, products
  purchased, first-time vs returning, A/B variants, send by send
- Message timing: actual revenue-per-recipient by day-of-week x hour, static
  sends separated from recipient-local sends, subject lines ranked by open rate
- Deliverability: score + history, bounce/spam/unsub by inbox provider,
  campaigns and flows ranked by the biggest offender
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import structlog

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced.customer_intel import _JsonStore

logger = structlog.get_logger(__name__)

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class PerformanceAnalytics:
    """Deep-dive performance analytics over our own send/event data."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._sends = _JsonStore("send_performance.json")
        self._deliverability = _JsonStore("deliverability_scores.json")

    def register(self) -> None:
        reg = self.registry.register("analytics.performance", version="1.0.0", metadata={"domain": "analytics", "type": "reporting"})
        reg.actions["record_send"] = self._record_send
        reg.actions["flow_map"] = self._flow_map
        reg.actions["campaign_deep_dive"] = self._campaign_deep_dive
        reg.actions["message_timing"] = self._message_timing
        reg.actions["deliverability"] = self._deliverability_report
        reg.actions["record_deliverability"] = self._record_deliverability

    # ------------------------------------------------------------ data in
    async def _record_send(self, p: dict[str, Any]) -> dict[str, Any]:
        """Record one message send with its creative + outcomes."""
        send = {
            "send_id": f"sd-{p.get('send_id', '')}" if p.get("send_id") else f"sd-{len(self._sends.load()) + 1}",
            "tenant_id": p.get("tenant_id", ""),
            "flow_id": p.get("flow_id", ""),
            "message_id": p.get("message_id", ""),
            "campaign_id": p.get("campaign_id", ""),
            "subject": p.get("subject", ""),
            "preview_text": p.get("preview_text", ""),
            "channel": p.get("channel", "email"),
            "send_mode": p.get("send_mode", "static"),  # static | recipient_local
            "sent_at": p.get("sent_at", datetime.now(UTC).isoformat()),
            "sent": int(p.get("sent", 0)),
            "delivered": int(p.get("delivered", 0)),
            "opened": int(p.get("opened", 0)),
            "clicked": int(p.get("clicked", 0)),
            "revenue": float(p.get("revenue", 0)),
            "unsubscribed": int(p.get("unsubscribed", 0)),
            "bounced": int(p.get("bounced", 0)),
            "spam": int(p.get("spam", 0)),
            "inbox_provider": p.get("inbox_provider", "unknown"),
            "products": p.get("products", []),
            "first_time_buyers": int(p.get("first_time_buyers", 0)),
            "returning_buyers": int(p.get("returning_buyers", 0)),
            "variant": p.get("variant", ""),
        }
        self._sends.upsert("send_id", send)
        return {"status": "recorded", "send": send}

    async def _record_deliverability(self, p: dict[str, Any]) -> dict[str, Any]:
        rec = {
            "id": f"dl-{p.get('provider', 'unknown')}-{len(self._deliverability.load()) + 1}",
            "tenant_id": p.get("tenant_id", ""),
            "provider": p.get("provider", "unknown"),
            "sent": int(p.get("sent", 0)),
            "bounced": int(p.get("bounced", 0)),
            "spam": int(p.get("spam", 0)),
            "unsubscribed": int(p.get("unsubscribed", 0)),
            "delivered": int(p.get("delivered", 0)),
            "at": p.get("at", datetime.now(UTC).isoformat()),
            "source": p.get("source", ""),  # campaign/flow id
            "source_name": p.get("source_name", ""),
        }
        self._deliverability.upsert("id", rec)
        return {"status": "recorded", "record": rec}

    # ------------------------------------------------------------ flow map
    async def _flow_map(self, p: dict[str, Any]) -> dict[str, Any]:
        """Every message of every flow with its numbers and creative — the flow map."""
        tenant = p.get("tenant_id", "")
        flow_id = p.get("flow_id", "")
        sends = [s for s in self._sends.load()
                 if s.get("tenant_id") == tenant and (not flow_id or s.get("flow_id") == flow_id)]
        # flow structure from the engine
        structure = []
        try:
            r = await self.registry.invoke("workflows", "list", {"tenant_id": tenant})
            for wf in r.get("workflows", []):
                if flow_id and wf.get("id") != flow_id:
                    continue
                structure.append({"flow_id": wf.get("id"), "name": wf.get("name"),
                                  "trigger": wf.get("trigger_event"),
                                  "steps": wf.get("steps", [])})
        except Exception:
            structure = []
        messages = []
        for s in sorted(sends, key=lambda x: x.get("sent_at", "")):
            sent = max(s.get("sent", 0), 1)
            messages.append({
                "message_id": s["message_id"], "flow_id": s.get("flow_id"), "subject": s.get("subject"),
                "preview_text": s.get("preview_text"), "channel": s.get("channel"),
                "send_mode": s.get("send_mode"), "sent_at": s.get("sent_at"),
                "sent": s.get("sent", 0), "delivered": s.get("delivered", 0),
                "open_rate": round(s.get("opened", 0) / sent * 100, 1),
                "click_rate": round(s.get("clicked", 0) / sent * 100, 1),
                "revenue": s.get("revenue", 0),
                "revenue_per_recipient": round(s.get("revenue", 0) / sent, 4),
                "variant": s.get("variant"),
            })
        totals = {
            "sent": sum(m["sent"] for m in messages),
            "delivered": sum(m["delivered"] for m in messages),
            "opened": sum(s.get("opened", 0) for s in sends),
            "clicked": sum(s.get("clicked", 0) for s in sends),
            "revenue": round(sum(s.get("revenue", 0) for s in sends), 2),
        }
        totals["open_rate"] = round(totals["opened"] / max(totals["sent"], 1) * 100, 1)
        totals["click_rate"] = round(totals["clicked"] / max(totals["sent"], 1) * 100, 1)
        return {"status": "ok", "flows": structure, "messages": messages, "totals": totals,
                "flow_count": len(structure), "message_count": len(messages)}

    # ------------------------------------------------------- campaign dive
    async def _campaign_deep_dive(self, p: dict[str, Any]) -> dict[str, Any]:
        """Creative + subject next to open/click/revenue, products, new vs returning, A/B."""
        tenant = p.get("tenant_id", "")
        campaign_id = p.get("campaign_id", "")
        sends = [s for s in self._sends.load()
                 if s.get("tenant_id") == tenant and (not campaign_id or s.get("campaign_id") == campaign_id)]
        sends.sort(key=lambda x: x.get("sent_at", ""), reverse=True)
        rows = []
        products: dict[str, dict[str, Any]] = {}
        variants: dict[str, dict[str, Any]] = {}
        first_time = returning = 0
        for s in sends:
            sent = max(s.get("sent", 0), 1)
            rows.append({
                "send_id": s["send_id"], "sent_at": s.get("sent_at"), "subject": s.get("subject"),
                "preview_text": s.get("preview_text"), "channel": s.get("channel"),
                "sent": s.get("sent", 0),
                "open_rate": round(s.get("opened", 0) / sent * 100, 1),
                "click_rate": round(s.get("clicked", 0) / sent * 100, 1),
                "revenue": s.get("revenue", 0),
                "revenue_per_recipient": round(s.get("revenue", 0) / sent, 4),
                "variant": s.get("variant"),
            })
            for prod in s.get("products", []):
                name = prod.get("name", "product")
                cur = products.setdefault(name, {"name": name, "units": 0, "revenue": 0.0})
                cur["units"] += int(prod.get("units", 0))
                cur["revenue"] = round(cur["revenue"] + float(prod.get("revenue", 0)), 2)
            if s.get("variant"):
                v = variants.setdefault(s["variant"], {"variant": s["variant"], "sent": 0, "opened": 0, "clicked": 0, "revenue": 0.0})
                v["sent"] += s.get("sent", 0); v["opened"] += s.get("opened", 0)
                v["clicked"] += s.get("clicked", 0); v["revenue"] = round(v["revenue"] + s.get("revenue", 0), 2)
            first_time += s.get("first_time_buyers", 0)
            returning += s.get("returning_buyers", 0)
        for v in variants.values():
            v["open_rate"] = round(v["opened"] / max(v["sent"], 1) * 100, 1)
            v["conversion_rate"] = round(v["clicked"] / max(v["sent"], 1) * 100, 1)
        total_revenue = round(sum(r["revenue"] for r in rows), 2)
        total_sent = sum(r["sent"] for r in rows)
        return {
            "status": "ok", "campaign_id": campaign_id,
            "sends": rows, "send_count": len(rows),
            "products": sorted(products.values(), key=lambda x: x["revenue"], reverse=True),
            "variants": list(variants.values()),
            "buyers": {"first_time": first_time, "returning": returning,
                       "first_time_share": round(first_time / max(first_time + returning, 1) * 100, 1)},
            "totals": {"sent": total_sent, "revenue": total_revenue,
                        "revenue_per_recipient": round(total_revenue / max(total_sent, 1), 4)},
        }

    # ------------------------------------------------------ message timing
    async def _message_timing(self, p: dict[str, Any]) -> dict[str, Any]:
        """Revenue per recipient by weekday x hour; static vs recipient-local separately."""
        tenant = p.get("tenant_id", "")
        sends = [s for s in self._sends.load() if s.get("tenant_id") == tenant]
        grid: dict[str, dict[str, dict[str, Any]]] = {"static": {}, "recipient_local": {}}
        subjects: dict[str, dict[str, Any]] = {}
        for s in sends:
            ts = s.get("sent_at", "")
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                continue
            day = WEEKDAYS[dt.weekday()]
            hour = dt.hour
            bucket = grid.setdefault(s.get("send_mode", "static"), {})
            cell = bucket.setdefault(f"{day}|{hour}", {"day": day, "hour": hour, "sent": 0, "revenue": 0.0, "recipients": 0})
            cell["sent"] += s.get("sent", 0)
            cell["revenue"] = round(cell["revenue"] + s.get("revenue", 0), 2)
            cell["recipients"] += max(s.get("sent", 0), 1)
            if s.get("subject"):
                sub = subjects.setdefault(s["subject"], {"subject": s["subject"], "sent": 0, "opened": 0, "revenue": 0.0})
                sub["sent"] += s.get("sent", 0)
                sub["opened"] += s.get("opened", 0)
                sub["revenue"] = round(sub["revenue"] + s.get("revenue", 0), 2)
        out_modes = {}
        for mode, bucket in grid.items():
            cells = list(bucket.values())
            for c in cells:
                c["revenue_per_recipient"] = round(c["revenue"] / max(c["recipients"], 1), 4)
            best = max(cells, key=lambda x: x["revenue_per_recipient"]) if cells else None
            worst = min(cells, key=lambda x: x["revenue_per_recipient"]) if cells else None
            out_modes[mode] = {"cells": cells, "best_slot": best, "weakest_slot": worst,
                                "sends_analysed": len(cells),
                                "recipients": sum(c["recipients"] for c in cells)}
        ranked = sorted(subjects.values(), key=lambda x: x["opened"] / max(x["sent"], 1), reverse=True)
        for s in ranked:
            s["open_rate"] = round(s["opened"] / max(s["sent"], 1) * 100, 1)
        return {"status": "ok", "days": WEEKDAYS, "modes": out_modes,
                "subjects_ranked": ranked[:20]}

    # ------------------------------------------------------- deliverability
    async def _deliverability_report(self, p: dict[str, Any]) -> dict[str, Any]:
        """Score + history, per-provider rates, and the biggest offenders."""
        tenant = p.get("tenant_id", "")
        recs = [r for r in self._deliverability.load() if r.get("tenant_id") == tenant]
        providers: dict[str, dict[str, Any]] = {}
        history: dict[str, list] = {}
        for r in recs:
            prov = r.get("provider", "unknown")
            cur = providers.setdefault(prov, {"provider": prov, "sent": 0, "bounced": 0, "spam": 0,
                                             "unsubscribed": 0, "delivered": 0})
            cur["sent"] += r.get("sent", 0); cur["bounced"] += r.get("bounced", 0)
            cur["spam"] += r.get("spam", 0); cur["unsubscribed"] += r.get("unsubscribed", 0)
            cur["delivered"] += r.get("delivered", 0)
            history.setdefault(prov, []).append({"at": r.get("at"), "bounced": r.get("bounced", 0)})
        for cur in providers.values():
            sent = max(cur["sent"], 1)
            cur["bounce_rate"] = round(cur["bounced"] / sent * 100, 2)
            cur["spam_rate"] = round(cur["spam"] / sent * 100, 2)
            cur["unsub_rate"] = round(cur["unsubscribed"] / sent * 100, 2)
            cur["delivered_rate"] = round(cur["delivered"] / sent * 100, 2)
            cur["history"] = sorted(history.get(cur["provider"], []), key=lambda x: x.get("at", ""))
        # overall score: delivered minus penalties
        total_sent = sum(c["sent"] for c in providers.values())
        total_bounced = sum(c["bounced"] for c in providers.values())
        total_spam = sum(c["spam"] for c in providers.values())
        delivered = sum(c["delivered"] for c in providers.values())
        score = 100
        if total_sent:
            score = round((delivered / total_sent) * 100 - (total_bounced / total_sent) * 100 * 2
                          - (total_spam / total_sent) * 100 * 3, 1)
        offenders = sorted([c for c in providers.values() if c["bounce_rate"] >= 1 or c["spam_rate"] >= 0.1],
                           key=lambda x: x["bounce_rate"] + x["spam_rate"], reverse=True)
        return {"status": "ok", "score": max(0.0, score), "providers": list(providers.values()),
                "biggest_offender": offenders[0] if offenders else None,
                "offenders": offenders, "history_points": len(recs)}

    async def _by_provider(self, p: dict[str, Any]) -> dict[str, Any]:
        """Compact provider view used by the agency roster (worst bounce rate)."""
        r = await self._deliverability_report(p)
        providers = r.get("providers", [])
        worst = max(providers, key=lambda x: x.get("bounce_rate", 0)) if providers else None
        return {"status": "ok", "worst_bounce_rate": worst.get("bounce_rate") if worst else None,
                "worst_provider": worst.get("provider") if worst else None,
                "score": r.get("score")}


__all__ = ["PerformanceAnalytics", "WEEKDAYS"]
