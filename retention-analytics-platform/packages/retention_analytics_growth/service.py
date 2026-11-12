"""Growth services: health scoring, dunning, surveys, forecasting, segmentation.

Each registers with the service registry so workflows and the API can invoke them.
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


class HealthScoringService:
    """Customer health score (0-100) from usage, support, and payment signals.

    Mirrors ChurnZero ChurnScores / Vitally Health Scores.
    """

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._path = data_root() / "health_scores.json"

    def register(self) -> None:
        reg = self.registry.register("health.scoring", version="1.0.0", metadata={"domain": "growth", "type": "platform"})
        reg.actions["compute"] = self._compute
        reg.actions["get"] = self._get
        reg.actions["list_low"] = self._list_low

    async def _compute(self, payload: dict[str, Any]) -> dict[str, Any]:
        tenant_id = payload.get("tenant_id", "")
        client_id = payload.get("client_id", "")
        usage_score = float(payload.get("usage_score", 50))
        support_score = float(payload.get("support_score", 50))
        payment_score = float(payload.get("payment_score", 100))
        engagement_score = float(payload.get("engagement_score", 50))
        score = round(usage_score * 0.35 + engagement_score * 0.25 + support_score * 0.2 + payment_score * 0.2, 1)
        if score >= 80:
            tier = "healthy"
        elif score >= 50:
            tier = "at_risk"
        else:
            tier = "critical"
        record = {
            "client_id": client_id,
            "tenant_id": tenant_id,
            "score": score,
            "tier": tier,
            "components": {
                "usage": usage_score,
                "engagement": engagement_score,
                "support": support_score,
                "payment": payment_score,
            },
            "computed_at": datetime.now(UTC).isoformat(),
        }
        self._persist(record)
        logger.info("health.score.computed", client_id=client_id, score=score, tier=tier)
        return {"status": "computed", "result": record}

    async def _get(self, payload: dict[str, Any]) -> dict[str, Any]:
        records = self._load_all(payload.get("tenant_id", ""))
        client_id = payload.get("client_id", "")
        for r in records:
            if r.get("client_id") == client_id:
                return {"status": "ok", "result": r}
        return {"status": "not_found"}

    async def _list_low(self, payload: dict[str, Any]) -> dict[str, Any]:
        threshold = float(payload.get("threshold", 50))
        records = [r for r in self._load_all(payload.get("tenant_id", "")) if r.get("score", 100) < threshold]
        return {"status": "ok", "at_risk_clients": records, "count": len(records)}

    def _load_all(self, tenant_id: str) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            data = json.loads(self._path.read_text())
            return [r for r in data if r.get("tenant_id") == tenant_id]
        except Exception:
            return []

    def _persist(self, record: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        existing = []
        if self._path.exists():
            try:
                existing = json.loads(self._path.read_text())
            except Exception:
                existing = []
        existing = [r for r in existing if not (r.get("client_id") == record["client_id"] and r.get("tenant_id") == record["tenant_id"])]
        existing.append(record)
        self._path.write_text(json.dumps(existing, indent=2, default=str))


class DunningService:
    """Payment failure recovery: retry schedule + escalating omnichannel campaign.

    Mirrors Baremetrics Recover / Churnkey Payment Recovery.
    """

    RETRY_SCHEDULE = [1, 3, 5, 7, 10]  # days between retries

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._path = data_root() / "dunning.json"

    def register(self) -> None:
        reg = self.registry.register("dunning", version="1.0.0", metadata={"domain": "growth", "type": "platform"})
        reg.actions["start_campaign"] = self._start
        reg.actions["schedule_retry"] = self._schedule_retry
        reg.actions["get_campaign"] = self._get
        reg.actions["list_active"] = self._list_active

    async def _start(self, payload: dict[str, Any]) -> dict[str, Any]:
        campaign = {
            "campaign_id": f"dun-{uuid.uuid4().hex[:12]}",
            "tenant_id": payload.get("tenant_id", ""),
            "subscription_id": payload.get("subscription_id", ""),
            "customer_email": payload.get("customer_email", ""),
            "amount_due": payload.get("amount_due", 0),
            "attempts": [],
            "status": "active",
            "started_at": datetime.now(UTC).isoformat(),
        }
        self._persist(campaign)
        logger.info("dunning.campaign.started", campaign_id=campaign["campaign_id"])
        return {"status": "started", "campaign": campaign, "retry_schedule_days": self.RETRY_SCHEDULE}

    async def _schedule_retry(self, payload: dict[str, Any]) -> dict[str, Any]:
        campaign_id = payload.get("campaign_id", "")
        attempt = payload.get("attempt", 1)
        days = self.RETRY_SCHEDULE[min(attempt - 1, len(self.RETRY_SCHEDULE) - 1)]
        next_retry = (datetime.now(UTC) + timedelta(days=days)).isoformat()
        return {
            "status": "scheduled",
            "campaign_id": campaign_id,
            "attempt": attempt,
            "next_retry_at": next_retry,
            "channel": "email" if attempt <= 2 else ("email+sms" if attempt <= 4 else "email+sms+push"),
        }

    async def _get(self, payload: dict[str, Any]) -> dict[str, Any]:
        for c in self._load_all():
            if c["campaign_id"] == payload.get("campaign_id"):
                return {"status": "ok", "campaign": c}
        return {"status": "not_found"}

    async def _list_active(self, payload: dict[str, Any]) -> dict[str, Any]:
        tenant_id = payload.get("tenant_id", "")
        active = [c for c in self._load_all() if c.get("tenant_id") == tenant_id and c.get("status") == "active"]
        return {"status": "ok", "campaigns": active, "count": len(active)}

    def _load_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return []

    def _persist(self, campaign: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        existing = self._load_all()
        existing = [c for c in existing if c["campaign_id"] != campaign["campaign_id"]]
        existing.append(campaign)
        self._path.write_text(json.dumps(existing, indent=2, default=str))


class SurveyService:
    """NPS / CES / CSAT surveys. Mirrors ChurnZero Surveys / Vitally NPS."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._path = data_root() / "surveys.json"

    def register(self) -> None:
        reg = self.registry.register("surveys", version="1.0.0", metadata={"domain": "growth", "type": "platform"})
        reg.actions["send_nps"] = self._send_nps
        reg.actions["send_csat"] = self._send_csat
        reg.actions["record_response"] = self._record
        reg.actions["compute_nps"] = self._compute_nps
        reg.actions["list_responses"] = self._list

    async def _send_nps(self, payload: dict[str, Any]) -> dict[str, Any]:
        survey = {
            "survey_id": f"nps-{uuid.uuid4().hex[:12]}",
            "type": "nps",
            "tenant_id": payload.get("tenant_id", ""),
            "client_id": payload.get("client_id", ""),
            "customer_email": payload.get("customer_email", ""),
            "question": "How likely are you to recommend us to a friend or colleague? (0-10)",
            "sent_at": datetime.now(UTC).isoformat(),
            "status": "sent",
        }
        self._persist(survey)
        return {"status": "sent", "survey": survey}

    async def _send_csat(self, payload: dict[str, Any]) -> dict[str, Any]:
        survey = {
            "survey_id": f"csat-{uuid.uuid4().hex[:12]}",
            "type": "csat",
            "tenant_id": payload.get("tenant_id", ""),
            "client_id": payload.get("client_id", ""),
            "customer_email": payload.get("customer_email", ""),
            "question": payload.get("question", "How satisfied are you with your recent experience? (1-5)"),
            "sent_at": datetime.now(UTC).isoformat(),
            "status": "sent",
        }
        self._persist(survey)
        return {"status": "sent", "survey": survey}

    async def _record(self, payload: dict[str, Any]) -> dict[str, Any]:
        survey_id = payload.get("survey_id", "")
        score = payload.get("score", 0)
        comment = payload.get("comment", "")
        all_surveys = self._load_all()
        for s in all_surveys:
            if s["survey_id"] == survey_id:
                s["status"] = "responded"
                s["score"] = score
                s["comment"] = comment
                s["responded_at"] = datetime.now(UTC).isoformat()
                self._persist_all(all_surveys)
                return {"status": "recorded", "score": score}
        return {"status": "not_found"}

    async def _compute_nps(self, payload: dict[str, Any]) -> dict[str, Any]:
        tenant_id = payload.get("tenant_id", "")
        responses = [s for s in self._load_all() if s.get("tenant_id") == tenant_id and s.get("type") == "nps" and s.get("status") == "responded"]
        if not responses:
            return {"status": "ok", "nps": None, "responses": 0}
        promoters = sum(1 for r in responses if r.get("score", 0) >= 9)
        detractors = sum(1 for r in responses if r.get("score", 0) <= 6)
        nps = round((promoters - detractors) / len(responses) * 100, 1)
        return {"status": "ok", "nps": nps, "responses": len(responses), "promoters": promoters, "detractors": detractors}

    async def _list(self, payload: dict[str, Any]) -> dict[str, Any]:
        tenant_id = payload.get("tenant_id", "")
        return {"status": "ok", "surveys": [s for s in self._load_all() if s.get("tenant_id") == tenant_id]}

    def _load_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return []

    def _persist(self, survey: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        existing = self._load_all()
        existing.append(survey)
        self._persist_all(existing)

    def _persist_all(self, data: list[dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2, default=str))


class ForecastingService:
    """MRR / revenue forecasting. Mirrors Baremetrics Forecasting."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def register(self) -> None:
        reg = self.registry.register("forecasting", version="1.0.0", metadata={"domain": "growth", "type": "platform"})
        reg.actions["forecast_mrr"] = self._forecast
        reg.actions["project_arr"] = self._project_arr

    async def _forecast(self, payload: dict[str, Any]) -> dict[str, Any]:
        current_mrr = float(payload.get("current_mrr", 0))
        monthly_growth_rate = float(payload.get("monthly_growth_rate", 0.05))
        churn_rate = float(payload.get("monthly_churn_rate", 0.03))
        months = int(payload.get("months", 12))
        net_rate = monthly_growth_rate - churn_rate
        forecast = []
        mrr = current_mrr
        for m in range(1, months + 1):
            mrr = mrr * (1 + net_rate)
            forecast.append({"month": m, "mrr": round(mrr, 2)})
        return {
            "status": "ok",
            "current_mrr": current_mrr,
            "forecast": forecast,
            "projected_mrr_12m": forecast[-1]["mrr"] if forecast else 0,
        }

    async def _project_arr(self, payload: dict[str, Any]) -> dict[str, Any]:
        current_mrr = float(payload.get("current_mrr", 0))
        result = await self._forecast({**payload, "months": 12})
        return {"status": "ok", "current_arr": current_mrr * 12, "projected_arr_12m": result["projected_mrr_12m"] * 12}


class SegmentationService:
    """Dynamic customer segmentation. Mirrors Baremetrics/Churnkey Segmentation."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._path = data_root() / "segments.json"

    def register(self) -> None:
        reg = self.registry.register("segmentation", version="1.0.0", metadata={"domain": "growth", "type": "platform"})
        reg.actions["define_segment"] = self._define
        reg.actions["assign"] = self._assign
        reg.actions["list_segments"] = self._list
        reg.actions["get_members"] = self._members

    async def _define(self, payload: dict[str, Any]) -> dict[str, Any]:
        segment = {
            "segment_id": payload.get("segment_id", f"seg-{uuid.uuid4().hex[:12]}"),
            "name": payload.get("name", ""),
            "tenant_id": payload.get("tenant_id", ""),
            "criteria": payload.get("criteria", {}),
            "created_at": datetime.now(UTC).isoformat(),
        }
        segments = self._load_all()
        segments = [s for s in segments if s["segment_id"] != segment["segment_id"]]
        segments.append(segment)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(segments, indent=2, default=str))
        return {"status": "defined", "segment": segment}

    async def _assign(self, payload: dict[str, Any]) -> dict[str, Any]:
        segment_id = payload.get("segment_id", "")
        client_id = payload.get("client_id", "")
        return {"status": "assigned", "segment_id": segment_id, "client_id": client_id}

    async def _list(self, payload: dict[str, Any]) -> dict[str, Any]:
        tenant_id = payload.get("tenant_id", "")
        return {"status": "ok", "segments": [s for s in self._load_all() if s.get("tenant_id") == tenant_id]}

    async def _members(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "segment_id": payload.get("segment_id", ""), "members": []}

    def _load_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return []


class InAppMessagingService:
    """In-app messages, walkthroughs, banners. Mirrors ChurnZero In-app communications / WalkThroughs."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._path = data_root() / "inapp_messages.json"

    def register(self) -> None:
        reg = self.registry.register("inapp.messaging", version="1.0.0", metadata={"domain": "growth", "type": "platform"})
        reg.actions["send_banner"] = self._banner
        reg.actions["start_walkthrough"] = self._walkthrough
        reg.actions["list_active"] = self._list

    async def _banner(self, payload: dict[str, Any]) -> dict[str, Any]:
        msg = {
            "message_id": f"ban-{uuid.uuid4().hex[:12]}",
            "type": "banner",
            "tenant_id": payload.get("tenant_id", ""),
            "client_id": payload.get("client_id", ""),
            "title": payload.get("title", ""),
            "body": payload.get("body", ""),
            "cta": payload.get("cta", {}),
            "sent_at": datetime.now(UTC).isoformat(),
        }
        self._persist(msg)
        return {"status": "sent", "message": msg}

    async def _walkthrough(self, payload: dict[str, Any]) -> dict[str, Any]:
        msg = {
            "message_id": f"wt-{uuid.uuid4().hex[:12]}",
            "type": "walkthrough",
            "tenant_id": payload.get("tenant_id", ""),
            "client_id": payload.get("client_id", ""),
            "steps": payload.get("steps", []),
            "sent_at": datetime.now(UTC).isoformat(),
        }
        self._persist(msg)
        return {"status": "started", "walkthrough": msg}

    async def _list(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "messages": self._load_all()}

    def _load_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return []

    def _persist(self, msg: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        existing = self._load_all()
        existing.append(msg)
        self._path.write_text(json.dumps(existing, indent=2, default=str))


__all__ = [
    "HealthScoringService",
    "DunningService",
    "SurveyService",
    "ForecastingService",
    "SegmentationService",
    "InAppMessagingService",
]
