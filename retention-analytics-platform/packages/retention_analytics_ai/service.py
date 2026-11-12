"""AI services: predictive churn, feedback classification, offer recommendation.

Feature-weighted scoring (interpretable, no black-box model needed for v1).
Same interface a real ML model would plug into.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

import structlog

from retention_analytics_core.repository import data_root
from retention_analytics_core.service_registry import ServiceRegistry

logger = structlog.get_logger(__name__)

# Feature weights for churn risk (sum-normalized). Tunable per vertical.
CHURN_WEIGHTS = {
    "usage_drop": 0.30,
    "support_tickets": 0.20,
    "payment_failures": 0.25,
    "login_frequency": 0.15,
    "nps_score": 0.10,
}

FEEDBACK_CATEGORIES = {
    "pricing": ["price", "cost", "expensive", "cheap", "plan", "fee", "charge", "billing", "subscription cost"],
    "features": ["feature", "missing", "need", "wish", "would be nice", "add", "request", "lacks"],
    "bugs": ["bug", "broken", "error", "crash", "fails", "not working", "glitch", "issue"],
    "ux": ["confusing", "hard to use", "difficult", "ux", "ui", "interface", "navigation", "slow"],
    "support": ["support", "help", "response", "wait", "rude", "unhelpful", "agent"],
    "onboarding": ["onboarding", "setup", "getting started", "confused at first", "tutorial"],
    "performance": ["slow", "lag", "loading", "timeout", "performance", "speed"],
    "praise": ["love", "great", "awesome", "amazing", "thanks", "excellent", "fantastic"],
}

OFFER_TYPES = {
    "discount": {"trigger": "price_sensitive", "value": 0.20, "desc": "20% off next 3 months"},
    "pause": {"trigger": "temporary", "value": 0, "desc": "Pause subscription for 1-3 months"},
    "downgrade_save": {"trigger": "downgrading", "value": 0.15, "desc": "15% off current plan to stay"},
    "annual_switch": {"trigger": "loyal", "value": 0.17, "desc": "Switch to annual, save 2 months"},
    "seat_handoff": {"trigger": "unused_seats", "value": 0, "desc": "Transfer unused seats instead of cancelling"},
    "winback": {"trigger": "churned", "value": 0.30, "desc": "30% off to come back"},
}


class PredictiveChurnService:
    """Predict churn probability per client from usage/support/payment signals."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._path = data_root() / "churn_predictions.json"

    def register(self) -> None:
        reg = self.registry.register("ai.churn_predict", version="1.0.0", metadata={"domain": "ai", "type": "ml"})
        reg.actions["predict"] = self._predict
        reg.actions["predict_all"] = self._predict_all
        reg.actions["at_risk_list"] = self._at_risk

    def _score(self, features: dict[str, float]) -> float:
        total = 0.0
        wsum = 0.0
        for k, w in CHURN_WEIGHTS.items():
            if k in features:
                total += features[k] * w
                wsum += w
        return round(total / wsum if wsum > 0 else 0.0, 3)

    async def _predict(self, p: dict[str, Any]) -> dict[str, Any]:
        features = {
            "usage_drop": min(float(p.get("usage_drop_pct", 0)) / 100, 1.0),
            "support_tickets": min(int(p.get("open_tickets", 0)) / 5, 1.0),
            "payment_failures": min(int(p.get("payment_failures", 0)) / 3, 1.0),
            "login_frequency": 1.0 - min(float(p.get("logins_last_30d", 10)) / 10, 1.0),
            "nps_score": 1.0 - (float(p.get("nps_score", 8)) / 10),
        }
        prob = self._score(features)
        if prob >= 0.7:
            risk = "critical"
        elif prob >= 0.4:
            risk = "high"
        elif prob >= 0.2:
            risk = "medium"
        else:
            risk = "low"
        result = {
            "client_id": p.get("client_id", ""),
            "tenant_id": p.get("tenant_id", ""),
            "churn_probability": prob,
            "risk_level": risk,
            "features": features,
            "predicted_at": datetime.now(UTC).isoformat(),
        }
        self._persist(result)
        return {"status": "ok", "prediction": result}

    async def _predict_all(self, p: dict[str, Any]) -> dict[str, Any]:
        clients = p.get("clients", [])
        results = []
        for c in clients:
            r = await self._predict({**c, "tenant_id": p.get("tenant_id", "")})
            results.append(r["prediction"])
        return {"status": "ok", "predictions": results, "count": len(results)}

    async def _at_risk(self, p: dict[str, Any]) -> dict[str, Any]:
        threshold = float(p.get("threshold", 0.4))
        tenant = p.get("tenant_id", "")
        all_preds = self._load_all()
        at_risk = [x for x in all_preds if x.get("tenant_id") == tenant and x.get("churn_probability", 0) >= threshold]
        at_risk.sort(key=lambda x: x["churn_probability"], reverse=True)
        return {"status": "ok", "at_risk": at_risk, "count": len(at_risk)}

    def _load_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return []

    def _persist(self, r: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        existing = [x for x in self._load_all() if not (x.get("client_id") == r["client_id"] and x.get("tenant_id") == r["tenant_id"])]
        existing.append(r)
        self._path.write_text(json.dumps(existing, indent=2, default=str))


class FeedbackAIService:
    """Classify freeform feedback into categories, rank by MRR impact.

    Mirrors Churnkey Feedback AI / Customer Insights AI.
    """

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._path = data_root() / "feedback_classified.json"

    def register(self) -> None:
        reg = self.registry.register("ai.feedback", version="1.0.0", metadata={"domain": "ai", "type": "nlp"})
        reg.actions["classify"] = self._classify
        reg.actions["classify_batch"] = self._classify_batch
        reg.actions["themes"] = self._themes
        reg.actions["search"] = self._search

    def _classify_text(self, text: str) -> tuple[str, float]:
        text_lower = text.lower()
        best_cat, best_score = "general", 0.0
        for cat, keywords in FEEDBACK_CATEGORIES.items():
            score = sum(1 for kw in keywords if kw in text_lower) / len(keywords)
            if score > best_score:
                best_cat, best_score = cat, score
        if best_score == 0:
            return "general", 0.0
        return best_cat, round(min(best_score * 3, 1.0), 2)

    async def _classify(self, p: dict[str, Any]) -> dict[str, Any]:
        text = p.get("text", "")
        cat, confidence = self._classify_text(text)
        record = {
            "id": f"fb-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}",
            "tenant_id": p.get("tenant_id", ""),
            "client_id": p.get("client_id", ""),
            "text": text,
            "category": cat,
            "confidence": confidence,
            "mrr_impact": p.get("mrr", 0),
            "classified_at": datetime.now(UTC).isoformat(),
        }
        self._persist(record)
        return {"status": "ok", "classification": {k: record[k] for k in ("category", "confidence", "id")}}

    async def _classify_batch(self, p: dict[str, Any]) -> dict[str, Any]:
        items = p.get("items", [])
        results = []
        for item in items:
            r = await self._classify({**item, "tenant_id": p.get("tenant_id", "")})
            results.append(r["classification"])
        return {"status": "ok", "results": results, "count": len(results)}

    async def _themes(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        records = [r for r in self._load_all() if r.get("tenant_id") == tenant]
        by_cat: dict[str, dict[str, Any]] = {}
        for r in records:
            cat = r["category"]
            by_cat.setdefault(cat, {"count": 0, "mrr_impact": 0.0, "examples": []})
            by_cat[cat]["count"] += 1
            by_cat[cat]["mrr_impact"] += float(r.get("mrr_impact", 0))
            if len(by_cat[cat]["examples"]) < 3:
                by_cat[cat]["examples"].append(r["text"][:100])
        ranked = sorted(by_cat.items(), key=lambda x: x[1]["mrr_impact"], reverse=True)
        return {"status": "ok", "themes": [{"category": k, **v} for k, v in ranked]}

    async def _search(self, p: dict[str, Any]) -> dict[str, Any]:
        query = p.get("query", "").lower()
        tenant = p.get("tenant_id", "")
        records = [r for r in self._load_all() if r.get("tenant_id") == tenant and query in r.get("text", "").lower()]
        return {"status": "ok", "results": records[:20], "count": len(records)}

    def _load_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return []

    def _persist(self, r: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        existing = self._load_all()
        existing.append(r)
        self._path.write_text(json.dumps(existing, indent=2, default=str))


class OfferRecommendationService:
    """Recommend the best retention offer per client based on churn reason.

    Mirrors Churnkey Adaptive Offers / Dynamic Offers.
    """

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def register(self) -> None:
        reg = self.registry.register("ai.offers", version="1.0.0", metadata={"domain": "ai", "type": "recommendation"})
        reg.actions["recommend"] = self._recommend
        reg.actions["list_offers"] = self._list

    async def _recommend(self, p: dict[str, Any]) -> dict[str, Any]:
        reason = p.get("churn_reason", "general")
        risk = float(p.get("churn_probability", 0.5))
        mrr = float(p.get("mrr", 0))

        reason_map = {
            "pricing": "discount", "price": "discount", "too_expensive": "discount",
            "temporary": "pause", "going_on_vacation": "pause",
            "downgrade": "downgrade_save", "downgrading": "downgrade_save",
            "loyal": "annual_switch", "happy": "annual_switch",
            "unused_seats": "seat_handoff", "team_shrunk": "seat_handoff",
            "churned": "winback",
        }
        offer_key = reason_map.get(reason, "discount" if risk > 0.6 else "pause")
        offer = OFFER_TYPES[offer_key]
        # Higher risk + higher MRR → bigger discount
        if risk > 0.7 and mrr > 500:
            offer = {**offer, "value": min(offer["value"] + 0.10, 0.50), "desc": offer["desc"] + " (escalated)"}
        return {
            "status": "ok",
            "recommendation": {
                "offer_type": offer_key,
                "discount_pct": round(offer["value"] * 100, 1),
                "description": offer["desc"],
                "reason": reason,
                "churn_probability": risk,
                "expected_save_probability": round(min(0.9, 0.3 + (1 - risk) * 0.6), 2),
            },
        }

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "offers": {k: {"trigger": v["trigger"], "discount_pct": round(v["value"]*100, 1), "desc": v["desc"]} for k, v in OFFER_TYPES.items()}}


__all__ = ["PredictiveChurnService", "FeedbackAIService", "OfferRecommendationService"]
