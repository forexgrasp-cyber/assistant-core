"""SaaS metrics service: MRR, ARR, GRR, NRR, LTV, CAC, ARPU, payback, logo retention.

All metrics computed from subscription/payment events. Matches the metric
coverage of Baremetrics, ChartMogul, and ProfitWell.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import structlog

from retention_analytics_core.repository import data_root
from retention_analytics_core.service_registry import ServiceRegistry

logger = structlog.get_logger(__name__)


class SaasMetricsService:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._path = data_root() / "saas_metrics.json"

    def register(self) -> None:
        reg = self.registry.register("saas.metrics", version="1.0.0", metadata={"domain": "analytics", "type": "platform"})
        for name in ("compute_mrr", "compute_arr", "compute_grr", "compute_nrr",
                      "compute_ltv", "compute_cac", "compute_arpu", "compute_payback",
                      "compute_logo_retention", "compute_expansion_mrr", "compute_contraction_mrr",
                      "compute_quick_ratio", "compute_all"):
            reg.actions[name] = getattr(self, f"_{name}")

    def _record_mrr_snapshot(self, tenant_id: str, mrr: float, breakdown: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = self._load()
        data.setdefault(tenant_id, []).append({
            "month": datetime.now(UTC).strftime("%Y-%m"),
            "mrr": mrr,
            "breakdown": breakdown,
            "recorded_at": datetime.now(UTC).isoformat(),
        })
        self._path.write_text(json.dumps(data, indent=2, default=str))

    async def _compute_mrr(self, p: dict[str, Any]) -> dict[str, Any]:
        """Monthly Recurring Revenue = sum of all active subscription MRR."""
        subs = p.get("subscriptions", [])
        mrr = sum(float(s.get("mrr", s.get("amount", 0) / 12 if s.get("interval") == "year" else s.get("amount", 0))) for s in subs if s.get("status") == "active")
        new_mrr = sum(float(s.get("mrr", s.get("amount", 0))) for s in subs if s.get("status") == "active" and s.get("is_new"))
        expansion = sum(float(s.get("expansion", 0)) for s in subs)
        contraction = sum(float(s.get("contraction", 0)) for s in subs)
        churned = sum(float(s.get("mrr", s.get("amount", 0))) for s in subs if s.get("status") == "cancelled" and s.get("churned_this_month"))
        result = {
            "mrr": round(mrr, 2),
            "new_mrr": round(new_mrr, 2),
            "expansion_mrr": round(expansion, 2),
            "contraction_mrr": round(contraction, 2),
            "churned_mrr": round(churned, 2),
            "net_new_mrr": round(new_mrr + expansion - contraction - churned, 2),
            "active_subscriptions": len([s for s in subs if s.get("status") == "active"]),
        }
        self._record_mrr_snapshot(p.get("tenant_id", ""), result["mrr"], result)
        return {"status": "ok", "metric": "mrr", "result": result}

    async def _compute_arr(self, p: dict[str, Any]) -> dict[str, Any]:
        mrr_r = await self._compute_mrr(p)
        return {"status": "ok", "metric": "arr", "result": {"arr": round(mrr_r["result"]["mrr"] * 12, 2), "mrr": mrr_r["result"]["mrr"]}}

    async def _compute_grr(self, p: dict[str, Any]) -> dict[str, Any]:
        """Gross Revenue Retention = (starting MRR - churned - contraction) / starting MRR."""
        starting = float(p.get("starting_mrr", 0))
        if starting == 0:
            return {"status": "ok", "metric": "grr", "result": {"grr": None, "reason": "starting_mrr is 0"}}
        churned = float(p.get("churned_mrr", 0))
        contraction = float(p.get("contraction_mrr", 0))
        grr = (starting - churned - contraction) / starting
        return {"status": "ok", "metric": "grr", "result": {"grr": round(grr * 100, 2), "grr_pct": f"{grr*100:.1f}%"}}

    async def _compute_nrr(self, p: dict[str, Any]) -> dict[str, Any]:
        """Net Revenue Retention = (starting + expansion - churned - contraction) / starting."""
        starting = float(p.get("starting_mrr", 0))
        if starting == 0:
            return {"status": "ok", "metric": "nrr", "result": {"nrr": None, "reason": "starting_mrr is 0"}}
        expansion = float(p.get("expansion_mrr", 0))
        churned = float(p.get("churned_mrr", 0))
        contraction = float(p.get("contraction_mrr", 0))
        nrr = (starting + expansion - churned - contraction) / starting
        return {"status": "ok", "metric": "nrr", "result": {"nrr": round(nrr * 100, 2), "nrr_pct": f"{nrr*100:.1f}%"}}

    async def _compute_ltv(self, p: dict[str, Any]) -> dict[str, Any]:
        """Lifetime Value = ARPU / monthly churn rate."""
        arpu = float(p.get("arpu", 0))
        churn = float(p.get("monthly_churn_rate", 0.03))
        if churn <= 0:
            churn = 0.001
        ltv = arpu / churn
        return {"status": "ok", "metric": "ltv", "result": {"ltv": round(ltv, 2), "arpu": arpu, "churn_rate": churn}}

    async def _compute_cac(self, p: dict[str, Any]) -> dict[str, Any]:
        """Customer Acquisition Cost = (sales + marketing spend) / new customers."""
        spend = float(p.get("sales_marketing_spend", 0))
        new_customers = int(p.get("new_customers", 0))
        cac = spend / new_customers if new_customers > 0 else None
        return {"status": "ok", "metric": "cac", "result": {"cac": round(cac, 2) if cac else None, "spend": spend, "new_customers": new_customers}}

    async def _compute_arpu(self, p: dict[str, Any]) -> dict[str, Any]:
        """Average Revenue Per User = MRR / active customers."""
        mrr = float(p.get("mrr", 0))
        customers = int(p.get("active_customers", 0))
        arpu = mrr / customers if customers > 0 else 0
        return {"status": "ok", "metric": "arpu", "result": {"arpu": round(arpu, 2), "mrr": mrr, "customers": customers}}

    async def _compute_payback(self, p: dict[str, Any]) -> dict[str, Any]:
        """CAC payback period (months) = CAC / (ARPU * gross margin)."""
        cac = float(p.get("cac", 0))
        arpu = float(p.get("arpu", 0))
        margin = float(p.get("gross_margin", 0.8))
        monthly = arpu * margin
        payback = cac / monthly if monthly > 0 else None
        return {"status": "ok", "metric": "payback", "result": {"payback_months": round(payback, 1) if payback else None, "cac": cac, "arpu": arpu, "margin": margin}}

    async def _compute_logo_retention(self, p: dict[str, Any]) -> dict[str, Any]:
        """Logo retention = (starting customers - churned logos) / starting customers."""
        starting = int(p.get("starting_customers", 0))
        churned = int(p.get("churned_customers", 0))
        if starting == 0:
            return {"status": "ok", "metric": "logo_retention", "result": {"rate": None}}
        rate = (starting - churned) / starting
        return {"status": "ok", "metric": "logo_retention", "result": {"rate": round(rate * 100, 2), "pct": f"{rate*100:.1f}%", "churned": churned, "starting": starting}}

    async def _compute_expansion_mrr(self, p: dict[str, Any]) -> dict[str, Any]:
        subs = p.get("subscriptions", [])
        exp = sum(float(s.get("expansion", 0)) for s in subs)
        return {"status": "ok", "metric": "expansion_mrr", "result": {"expansion_mrr": round(exp, 2)}}

    async def _compute_contraction_mrr(self, p: dict[str, Any]) -> dict[str, Any]:
        subs = p.get("subscriptions", [])
        con = sum(float(s.get("contraction", 0)) for s in subs)
        return {"status": "ok", "metric": "contraction_mrr", "result": {"contraction_mrr": round(con, 2)}}

    async def _compute_quick_ratio(self, p: dict[str, Any]) -> dict[str, Any]:
        """Quick ratio = (new + expansion MRR) / (churned + contraction MRR). >1 = growing."""
        new_mrr = float(p.get("new_mrr", 0))
        expansion = float(p.get("expansion_mrr", 0))
        churned = float(p.get("churned_mrr", 0))
        contraction = float(p.get("contraction_mrr", 0))
        denom = churned + contraction
        qr = (new_mrr + expansion) / denom if denom > 0 else None
        return {"status": "ok", "metric": "quick_ratio", "result": {"quick_ratio": round(qr, 2) if qr else None, "growing": bool(qr and qr > 1)}}

    async def _compute_all(self, p: dict[str, Any]) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for name in ("compute_mrr", "compute_arr", "compute_grr", "compute_nrr", "compute_ltv",
                      "compute_cac", "compute_arpu", "compute_payback", "compute_logo_retention", "compute_quick_ratio"):
            r = await getattr(self, f"_{name}")(p)
            results[r["metric"]] = r["result"]
        return {"status": "ok", "metrics": results, "computed_at": datetime.now(UTC).isoformat()}

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return {}


__all__ = ["SaasMetricsService"]
