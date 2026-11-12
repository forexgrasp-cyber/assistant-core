"""Predictive send time, ML churn scoring, deliverability, customer portal.

All canonical capabilities come from shared-canonical-services:
  - shared.predictive_sendtime.sendtime_service.SendTimeService
  - shared.predictive.churn (churn_risk, ltv_projection_cents, rfm_metrics)
  - shared.deliverability.service.DeliverabilityService
  - shared.customer_portal.service.CustomerPortalService
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


class SendTimeService:
    """Optimal send time per customer (shared.predictive_sendtime) + campaign batch planning."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._plans = _JsonStore("sendtime_plans.json")

    def register(self) -> None:
        reg = self.registry.register("sendtime.optimize", version="1.0.0", metadata={"domain": "engagement", "type": "ml"})
        reg.actions["recommend"] = self._recommend
        reg.actions["batch"] = self._batch
        reg.actions["record_engagement"] = self._engage
        reg.actions["best_hours"] = self._best_hours
        reg.actions["plan_campaign"] = self._plan

    def _svc(self):
        from shared.predictive_sendtime.sendtime_service import SendTimeService as Shared

        return Shared()

    async def _recommend(self, p: dict[str, Any]) -> dict[str, Any]:
        email = p.get("email", "")
        rec = self._svc().get_recommendation(email)
        return {"status": "ok", "email": email, "recommendation": rec}

    async def _batch(self, p: dict[str, Any]) -> dict[str, Any]:
        emails = p.get("emails", [])
        recs = self._svc().get_batch_recommendations(emails)
        return {"status": "ok", "count": len(recs), "recommendations": recs}

    async def _engage(self, p: dict[str, Any]) -> dict[str, Any]:
        r = self._svc().record_engagement(p.get("email", ""), p.get("opened_at"), p.get("clicked_at"))
        return {"status": "ok", "result": r}

    async def _best_hours(self, p: dict[str, Any]) -> dict[str, Any]:
        hours = self._svc().get_best_send_hours()
        return {"status": "ok", "best_hours": hours}

    async def _plan(self, p: dict[str, Any]) -> dict[str, Any]:
        """Plan a campaign send schedule using per-recipient optimal times."""
        recipients = p.get("recipients", [])
        svc = self._svc()
        planned = []
        for r in recipients:
            rec = svc.get_recommendation(r.get("email", ""))
            planned.append({"email": r.get("email", ""), "customer_id": r.get("customer_id", ""),
                            "send_at": rec, "segment": r.get("segment", "")})
        plan = {"plan_id": f"stp-{uuid.uuid4().hex[:12]}", "tenant_id": p.get("tenant_id", ""),
                "campaign_id": p.get("campaign_id", ""), "planned": planned,
                "created_at": datetime.now(UTC).isoformat()}
        self._plans.upsert("plan_id", plan)
        return {"status": "ok", "plan": plan}


class MLChurnService:
    """Churn risk via shared.predictive.churn (canonical scoring) + our explainable engine."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def register(self) -> None:
        reg = self.registry.register("ai.churn_ml", version="1.0.0", metadata={"domain": "ai", "type": "ml"})
        reg.actions["score"] = self._score
        reg.actions["ltv"] = self._ltv
        reg.actions["rfm"] = self._rfm

    async def _score(self, p: dict[str, Any]) -> dict[str, Any]:
        from shared.predictive.churn import churn_risk

        metrics = {
            "orders": p.get("orders", 0),
            "order_count": p.get("order_count", 0),
            "total_spent": p.get("total_spent", 0),
            "days_since_last_order": p.get("days_since_last_order", 0),
            "recency_days": p.get("recency_days", p.get("days_since_last_order", 0)),
            "frequency": p.get("frequency", 0),
            "monetary": p.get("monetary", 0),
            "avg_order_value": p.get("avg_order_value", 0),
            "refunds": p.get("refunds", 0),
        }
        risk = churn_risk(metrics, engagement_recency_days=p.get("engagement_recency_days"))
        # Blend with our explainable health engine score for robustness
        try:
            eng = await self.registry.invoke("health.engine", "compute", {
                "tenant_id": p.get("tenant_id", ""), "client_id": p.get("client_id", ""),
                "usage_score": p.get("usage_score", 50), "engagement_score": p.get("engagement_score", 50),
                "open_tickets": p.get("open_tickets", 0), "payment_failures": p.get("payment_failures", 0)})
            health = eng.get("result", {}).get("score", 50)
        except Exception:
            health = 50
        ml_risk = (risk or 0) * 100
        blended = round((ml_risk * 0.6 + (100 - health) * 0.4), 1)
        return {"status": "ok", "result": {
            "client_id": p.get("client_id", ""),
            "ml_churn_risk": round(ml_risk, 1),
            "health_score": health,
            "blended_risk": blended,
            "risk_level": "critical" if blended >= 70 else "high" if blended >= 45 else "medium" if blended >= 25 else "low",
            "components": {"ml": round(ml_risk, 1), "health": health},
        }}

    async def _ltv(self, p: dict[str, Any]) -> dict[str, Any]:
        from shared.predictive.churn import ltv_projection_cents

        cents = ltv_projection_cents(p.get("metrics", {}), p.get("avg_order_value_cents", 0))
        return {"status": "ok", "ltv_cents": cents, "ltv": round((cents or 0) / 100, 2)}

    async def _rfm(self, p: dict[str, Any]) -> dict[str, Any]:
        from shared.predictive.churn import rfm_metrics

        m = rfm_metrics(p.get("orders", []))
        return {"status": "ok", "rfm": m}


class DeliverabilityService:
    """Email deliverability: warmup schedule, domain checks, blacklist checks (shared.deliverability)."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def register(self) -> None:
        reg = self.registry.register("email.deliverability", version="1.0.0", metadata={"domain": "engagement", "type": "platform"})
        reg.actions["warmup_schedule"] = self._warmup
        reg.actions["domain_check"] = self._domain
        reg.actions["blacklist_check"] = self._blacklist
        reg.actions["dns_instructions"] = self._dns

    def _svc(self):
        from shared.deliverability.service import DeliverabilityService as Shared

        return Shared()

    async def _warmup(self, p: dict[str, Any]) -> dict[str, Any]:
        sched = self._svc().get_warmup_schedule(p.get("daily_volume", 50), p.get("age_days", 0))
        return {"status": "ok", "schedule": sched}

    async def _domain(self, p: dict[str, Any]) -> dict[str, Any]:
        r = self._svc().check_domain(p.get("domain", ""))
        return {"status": "ok", "result": r}

    async def _blacklist(self, p: dict[str, Any]) -> dict[str, Any]:
        r = self._svc().check_blacklists(p.get("email", ""))
        return {"status": "ok", "result": r}

    async def _dns(self, p: dict[str, Any]) -> dict[str, Any]:
        r = self._svc().generate_dns_instructions(p.get("domain", ""))
        return {"status": "ok", "instructions": r}


class CustomerPortalService:
    """Customer-facing success center (shared.customer_portal): documents, DSAR requests, dashboard."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def register(self) -> None:
        reg = self.registry.register("success_center", version="1.0.0", metadata={"domain": "customers", "type": "platform"})
        reg.actions["register_customer"] = self._register
        reg.actions["dashboard"] = self._dashboard
        reg.actions["get_customer"] = self._get
        reg.actions["documents"] = self._documents
        reg.actions["upload_document"] = self._upload
        reg.actions["submit_dsar"] = self._dsar
        reg.actions["dsar_list"] = self._dsar_list

    def _svc(self):
        from shared.customer_portal.service import CustomerPortalService as Shared

        return Shared()

    async def _register(self, p: dict[str, Any]) -> dict[str, Any]:
        r = self._svc().register_customer(p.get("email", ""), p.get("name", ""), p.get("tenant_id", ""))
        return {"status": "ok", "result": r}

    async def _dashboard(self, p: dict[str, Any]) -> dict[str, Any]:
        r = self._svc().get_customer_dashboard(p.get("email", ""))
        return {"status": "ok", "result": r}

    async def _get(self, p: dict[str, Any]) -> dict[str, Any]:
        r = self._svc().get_customer(p.get("email", ""))
        return {"status": "ok", "result": r}

    async def _documents(self, p: dict[str, Any]) -> dict[str, Any]:
        r = self._svc().get_customer_documents(p.get("email", ""))
        return {"status": "ok", "result": r}

    async def _upload(self, p: dict[str, Any]) -> dict[str, Any]:
        r = self._svc().upload_document(p.get("email", ""), p.get("filename", ""), p.get("content", ""))
        return {"status": "ok", "result": r}

    async def _dsar(self, p: dict[str, Any]) -> dict[str, Any]:
        r = self._svc().submit_dsar_request(p.get("email", ""), p.get("request_type", "access"))
        return {"status": "ok", "result": r}

    async def _dsar_list(self, p: dict[str, Any]) -> dict[str, Any]:
        r = self._svc().get_customer_dsar_requests(p.get("email", ""))
        return {"status": "ok", "result": r}


__all__ = ["SendTimeService", "MLChurnService", "DeliverabilityService", "CustomerPortalService"]
