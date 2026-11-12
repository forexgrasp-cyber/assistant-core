"""Experiments, sequences, catalog, walls, journeys, attribution, anomaly detection,
pricing experiments, QBR generation. All universal services."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from retention_analytics_core.repository import data_root
from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced.customer_intel import _JsonStore

logger = structlog.get_logger(__name__)


class ABTestingService:
    """A/B test campaigns and offers: split a segment, run variants, compare.

    Mirrors Gainsight A/B testing and ProfitWell pricing experiments.
    """

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._experiments = _JsonStore("experiments.json")

    def register(self) -> None:
        reg = self.registry.register("experiments.ab", version="1.0.0", metadata={"domain": "experiments", "type": "platform"})
        reg.actions["create"] = self._create
        reg.actions["list"] = self._list
        reg.actions["get"] = self._get
        reg.actions["record_result"] = self._record
        reg.actions["analyze"] = self._analyze
        reg.actions["annotate"] = self._annotate

    async def _create(self, p: dict[str, Any]) -> dict[str, Any]:
        variants = p.get("variants", [])
        if len(variants) < 2:
            variants = [
                {"id": "A", "name": "control", "content": p.get("control_content", "")},
                {"id": "B", "name": "variant", "content": p.get("variant_content", "")},
            ]
        exp = {
            "experiment_id": f"exp-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "name": p.get("name", ""),
            "hypothesis": p.get("hypothesis", ""),
            "metric": p.get("metric", "conversion_rate"),
            "variants": variants,
            "split": float(p.get("split", 0.5)),
            "status": "running",
            "results": {v["id"]: {"sent": 0, "converted": 0} for v in variants},
            "notes": [],
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._experiments.upsert("experiment_id", exp)
        return {"status": "created", "experiment": exp}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        return {"status": "ok", "experiments": [e for e in self._experiments.load() if e.get("tenant_id") == tenant]}

    async def _get(self, p: dict[str, Any]) -> dict[str, Any]:
        for e in self._experiments.load():
            if e.get("experiment_id") == p.get("experiment_id"):
                return {"status": "ok", "experiment": e}
        return {"status": "not_found"}

    async def _record(self, p: dict[str, Any]) -> dict[str, Any]:
        """Record a variant outcome: sent + converted counts."""
        data = self._experiments.load()
        for e in data:
            if e.get("experiment_id") == p.get("experiment_id"):
                vid = p.get("variant_id", "A")
                bucket = e.setdefault("results", {}).setdefault(vid, {"sent": 0, "converted": 0})
                bucket["sent"] += int(p.get("sent", 0))
                bucket["converted"] += int(p.get("converted", 0))
                self._experiments.save(data)
                return {"status": "recorded", "results": e["results"]}
        return {"status": "not_found"}

    async def _analyze(self, p: dict[str, Any]) -> dict[str, Any]:
        """Compare variant conversion rates, flag the winner."""
        r = await self._get(p)
        if r["status"] != "ok":
            return r
        e = r["experiment"]
        rows = []
        for vid, res in e.get("results", {}).items():
            sent = res.get("sent", 0)
            conv = res.get("converted", 0)
            rate = (conv / sent) if sent else 0.0
            rows.append({"variant_id": vid, "sent": sent, "converted": conv, "conversion_rate": round(rate * 100, 2)})
        rows.sort(key=lambda x: x["conversion_rate"], reverse=True)
        winner = rows[0] if rows and rows[0]["conversion_rate"] > 0 else None
        lift = None
        if len(rows) >= 2 and rows[1]["conversion_rate"] > 0:
            lift = round((rows[0]["conversion_rate"] - rows[1]["conversion_rate"]) / rows[1]["conversion_rate"] * 100, 1)
        return {"status": "ok", "experiment_id": e["experiment_id"], "metric": e.get("metric"),
                "variants": rows, "winner": winner, "lift_pct": lift}

    async def _annotate(self, p: dict[str, Any]) -> dict[str, Any]:
        """Trial Insights: add a note to a campaign/experiment to track impact."""
        data = self._experiments.load()
        for e in data:
            if e.get("experiment_id") == p.get("experiment_id"):
                note = {"note": p.get("note", ""), "at": datetime.now(UTC).isoformat(), "metric_delta": p.get("metric_delta")}
                e.setdefault("notes", []).append(note)
                self._experiments.save(data)
                return {"status": "annotated", "notes": e["notes"]}
        return {"status": "not_found"}


class SequenceService:
    """Multi-touch drip sequences (email/SMS/push over time).

    Mirrors Gainsight email sequences and ChurnZero Journeys.
    """

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._sequences = _JsonStore("sequences.json")

    def register(self) -> None:
        reg = self.registry.register("automation.sequences", version="1.0.0", metadata={"domain": "automation", "type": "platform"})
        reg.actions["create"] = self._create
        reg.actions["list"] = self._list
        reg.actions["get"] = self._get
        reg.actions["enroll"] = self._enroll
        reg.actions["advance"] = self._advance

    async def _create(self, p: dict[str, Any]) -> dict[str, Any]:
        seq = {
            "sequence_id": f"seq-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "name": p.get("name", ""),
            "steps": p.get("steps", []),  # [{delay_days, channel, template, subject, body}]
            "status": "active",
            "enrollments": [],
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._sequences.upsert("sequence_id", seq)
        return {"status": "created", "sequence": seq}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        return {"status": "ok", "sequences": [s for s in self._sequences.load() if s.get("tenant_id") == tenant]}

    async def _get(self, p: dict[str, Any]) -> dict[str, Any]:
        for s in self._sequences.load():
            if s.get("sequence_id") == p.get("sequence_id"):
                return {"status": "ok", "sequence": s}
        return {"status": "not_found"}

    async def _enroll(self, p: dict[str, Any]) -> dict[str, Any]:
        """Enroll a customer into a sequence; returns the first step to send now."""
        data = self._sequences.load()
        for s in data:
            if s.get("sequence_id") == p.get("sequence_id"):
                enroll = {
                    "enrollment_id": f"enr-{uuid.uuid4().hex[:12]}",
                    "customer_id": p.get("customer_id", ""),
                    "customer_email": p.get("customer_email", ""),
                    "current_step": 0,
                    "started_at": datetime.now(UTC).isoformat(),
                    "next_step_at": datetime.now(UTC).isoformat(),
                    "status": "active",
                    "sent_steps": [],
                }
                s.setdefault("enrollments", []).append(enroll)
                self._sequences.save(data)
                first = s.get("steps", [{}])[0] if s.get("steps") else {}
                return {"status": "enrolled", "enrollment": enroll, "first_step": first}
        return {"status": "not_found"}

    async def _advance(self, p: dict[str, Any]) -> dict[str, Any]:
        """Advance an enrollment to its next step (or complete it)."""
        data = self._sequences.load()
        for s in data:
            for e in s.get("enrollments", []):
                if e.get("enrollment_id") == p.get("enrollment_id"):
                    steps = s.get("steps", [])
                    idx = int(e.get("current_step", 0))
                    if idx >= len(steps):
                        e["status"] = "completed"
                        self._sequences.save(data)
                        return {"status": "completed", "enrollment": e}
                    e.setdefault("sent_steps", []).append(idx)
                    e["current_step"] = idx + 1
                    delay = int(steps[idx].get("delay_days", 0))
                    e["next_step_at"] = (datetime.now(UTC) + timedelta(days=delay)).isoformat()
                    if e["current_step"] >= len(steps):
                        e["status"] = "completed"
                    self._sequences.save(data)
                    nxt = steps[e["current_step"]] if e["current_step"] < len(steps) else None
                    return {"status": "ok", "enrollment": e, "next_step": nxt}
        return {"status": "not_found"}


class CatalogService:
    """Product + offer catalog for cross-sell and upsell. Churnkey cancel-flow offers."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._products = _JsonStore("catalog_products.json")
        self._offers = _JsonStore("catalog_offers.json")

    def register(self) -> None:
        reg = self.registry.register("catalog", version="1.0.0", metadata={"domain": "commerce", "type": "platform"})
        reg.actions["add_product"] = self._add_product
        reg.actions["list_products"] = self._list_products
        reg.actions["add_offer"] = self._add_offer
        reg.actions["list_offers"] = self._list_offers
        reg.actions["recommend_cross_sell"] = self._recommend

    async def _add_product(self, p: dict[str, Any]) -> dict[str, Any]:
        prod = {
            "product_id": p.get("product_id") or f"prod-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "name": p.get("name", ""),
            "description": p.get("description", ""),
            "price": float(p.get("price", 0)),
            "billing": p.get("billing", "one_time"),  # one_time | recurring
            "category": p.get("category", ""),
            "tags": p.get("tags", []),
            "complements": p.get("complements", []),
        }
        self._products.upsert("product_id", prod)
        return {"status": "created", "product": prod}

    async def _list_products(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        return {"status": "ok", "products": [x for x in self._products.load() if x.get("tenant_id") == tenant]}

    async def _add_offer(self, p: dict[str, Any]) -> dict[str, Any]:
        offer = {
            "offer_id": f"offer-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "name": p.get("name", ""),
            "type": p.get("type", "discount"),  # discount | cross_sell | pause | downgrade | annual | free_trial
            "product_id": p.get("product_id"),
            "discount_pct": float(p.get("discount_pct", 0)),
            "duration_days": int(p.get("duration_days", 0)),
            "conditions": p.get("conditions", {}),
            "message": p.get("message", ""),
            "active": True,
        }
        self._offers.upsert("offer_id", offer)
        return {"status": "created", "offer": offer}

    async def _list_offers(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        return {"status": "ok", "offers": [o for o in self._offers.load() if o.get("tenant_id") == tenant and o.get("active")]}

    async def _recommend(self, p: dict[str, Any]) -> dict[str, Any]:
        """Recommend cross-sell for a customer based on their plan/products/tags."""
        tenant = p.get("tenant_id", "")
        customer = p.get("customer", {})
        products = [x for x in self._products.load() if x.get("tenant_id") == tenant]
        owned = set(customer.get("products", []) or [])
        tags = set(customer.get("tags", []) or [])
        scored = []
        for prod in products:
            if prod["product_id"] in owned:
                continue
            score = 0.0
            if prod.get("category") and prod["category"] == customer.get("plan"):
                score += 0.4
            if tags and tags & set(prod.get("tags", [])):
                score += 0.3
            if prod.get("complements") and customer.get("plan") in prod["complements"]:
                score += 0.3
            if score > 0:
                scored.append({"product": prod, "score": round(score, 2)})
        scored.sort(key=lambda x: x["score"], reverse=True)
        return {"status": "ok", "recommendations": scored[:5]}


class WallsService:
    """Pause Wall and Payment Wall: gate features until a condition clears.

    Mirrors Churnkey Pause Wall / Payment Wall.
    """

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._walls = _JsonStore("walls.json")

    def register(self) -> None:
        reg = self.registry.register("walls", version="1.0.0", metadata={"domain": "engagement", "type": "platform"})
        reg.actions["create"] = self._create
        reg.actions["check"] = self._check
        reg.actions["resolve"] = self._resolve
        reg.actions["list"] = self._list

    async def _create(self, p: dict[str, Any]) -> dict[str, Any]:
        wall = {
            "wall_id": f"wall-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "customer_id": p.get("customer_id", ""),
            "type": p.get("type", "payment"),  # payment | pause
            "reason": p.get("reason", ""),
            "amount_due": float(p.get("amount_due", 0)),
            "resume_at": p.get("resume_at"),
            "gated_features": p.get("gated_features", []),
            "message": p.get("message", ""),
            "active": True,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._walls.upsert("wall_id", wall)
        return {"status": "created", "wall": wall}

    async def _check(self, p: dict[str, Any]) -> dict[str, Any]:
        """Check whether a customer is walled and which features are blocked."""
        cust = p.get("customer_id", "")
        active = [w for w in self._walls.load() if w.get("customer_id") == cust and w.get("active")]
        if not active:
            return {"status": "ok", "walled": False, "gated_features": []}
        wall = active[0]
        return {"status": "ok", "walled": True, "wall": wall, "gated_features": wall.get("gated_features", []),
                "message": wall.get("message", "")}

    async def _resolve(self, p: dict[str, Any]) -> dict[str, Any]:
        data = self._walls.load()
        for w in data:
            if w.get("wall_id") == p.get("wall_id") or (w.get("customer_id") == p.get("customer_id") and w.get("active")):
                w["active"] = False
                w["resolved_at"] = datetime.now(UTC).isoformat()
                w["resolution"] = p.get("resolution", "")
                self._walls.save(data)
                return {"status": "resolved", "wall": w}
        return {"status": "not_found"}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        return {"status": "ok", "walls": [w for w in self._walls.load() if w.get("tenant_id") == tenant]}


class JourneyService:
    """Multi-stage customer journeys with stage tracking. Gainsight Journey Orchestrator."""

    STAGES = ["onboarding", "adoption", "value_realized", "renewal", "expansion", "advocacy"]

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._journeys = _JsonStore("journeys.json")

    def register(self) -> None:
        reg = self.registry.register("journeys", version="1.0.0", metadata={"domain": "automation", "type": "platform"})
        reg.actions["create"] = self._create
        reg.actions["list"] = self._list
        reg.actions["set_stage"] = self._set_stage
        reg.actions["get"] = self._get
        reg.actions["stage_distribution"] = self._distribution

    async def _create(self, p: dict[str, Any]) -> dict[str, Any]:
        journey = {
            "journey_id": f"jr-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "name": p.get("name", ""),
            "stages": p.get("stages", self.STAGES),
            "stage_goals": p.get("stage_goals", {}),
            "customers": {},
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._journeys.upsert("journey_id", journey)
        return {"status": "created", "journey": journey}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        return {"status": "ok", "journeys": [j for j in self._journeys.load() if j.get("tenant_id") == tenant]}

    async def _get(self, p: dict[str, Any]) -> dict[str, Any]:
        for j in self._journeys.load():
            if j.get("journey_id") == p.get("journey_id"):
                return {"status": "ok", "journey": j}
        return {"status": "not_found"}

    async def _set_stage(self, p: dict[str, Any]) -> dict[str, Any]:
        data = self._journeys.load()
        for j in data:
            if j.get("journey_id") == p.get("journey_id"):
                stage = p.get("stage", "")
                j.setdefault("customers", {})[p.get("customer_id", "")] = {"stage": stage, "at": datetime.now(UTC).isoformat()}
                self._journeys.save(data)
                return {"status": "ok", "customer_id": p.get("customer_id"), "stage": stage}
        return {"status": "not_found"}

    async def _distribution(self, p: dict[str, Any]) -> dict[str, Any]:
        r = await self._get(p)
        if r["status"] != "ok":
            return r
        j = r["journey"]
        dist: dict[str, int] = {s: 0 for s in j.get("stages", [])}
        for c in j.get("customers", {}).values():
            dist[c.get("stage", "unknown")] = dist.get(c.get("stage", "unknown"), 0) + 1
        return {"status": "ok", "journey_id": j["journey_id"], "distribution": dist, "total": len(j.get("customers", {}))}


class AttributionService:
    """Attribute retention/savings to campaigns and touchpoints. Gainsight attribution."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._touchpoints = _JsonStore("touchpoints.json")
        self._outcomes = _JsonStore("attribution_outcomes.json")

    def register(self) -> None:
        reg = self.registry.register("analytics.attribution", version="1.0.0", metadata={"domain": "analytics", "type": "platform"})
        reg.actions["record_outcome"] = self._record
        reg.actions["for_customer"] = self._for_customer
        reg.actions["campaign_impact"] = self._campaign_impact

    async def _record(self, p: dict[str, Any]) -> dict[str, Any]:
        rec = {
            "id": f"attr-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "customer_id": p.get("customer_id", ""),
            "campaign_id": p.get("campaign_id", ""),
            "outcome": p.get("outcome", "retained"),  # retained | churned | recovered | converted
            "value": float(p.get("value", 0)),
            "at": datetime.now(UTC).isoformat(),
        }
        self._outcomes.upsert("id", rec)
        return {"status": "recorded", "outcome": rec}

    async def _for_customer(self, p: dict[str, Any]) -> dict[str, Any]:
        cust = p.get("customer_id", "")
        touches = [t for t in self._touchpoints.load() if t.get("customer_id") == cust]
        outcomes = [o for o in self._outcomes.load() if o.get("customer_id") == cust]
        return {"status": "ok", "customer_id": cust, "touchpoints": touches, "outcomes": outcomes}

    async def _campaign_impact(self, p: dict[str, Any]) -> dict[str, Any]:
        """Aggregate saved revenue and save rate per campaign."""
        tenant = p.get("tenant_id", "")
        outcomes = [o for o in self._outcomes.load() if o.get("tenant_id") == tenant]
        by_campaign: dict[str, dict[str, Any]] = {}
        for o in outcomes:
            cid = o.get("campaign_id") or "unattributed"
            b = by_campaign.setdefault(cid, {"campaign_id": cid, "total": 0, "retained": 0, "churned": 0, "value_saved": 0.0})
            b["total"] += 1
            if o.get("outcome") in ("retained", "recovered", "converted"):
                b["retained"] += 1
                b["value_saved"] += float(o.get("value", 0))
            else:
                b["churned"] += 1
        for b in by_campaign.values():
            b["save_rate"] = round(b["retained"] / b["total"] * 100, 1) if b["total"] else 0
            b["value_saved"] = round(b["value_saved"], 2)
        return {"status": "ok", "campaigns": list(by_campaign.values())}


class AnomalyDetectionService:
    """Detect metric anomalies vs trailing average. Advanced alerting."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry

    def register(self) -> None:
        reg = self.registry.register("analytics.anomaly", version="1.0.0", metadata={"domain": "analytics", "type": "ml"})
        reg.actions["detect"] = self._detect

    async def _detect(self, p: dict[str, Any]) -> dict[str, Any]:
        series = p.get("series", [])
        threshold_pct = float(p.get("threshold_pct", 20))
        if len(series) < 4:
            return {"status": "ok", "anomalies": [], "note": "need at least 4 points"}
        values = [float(v) for v in series]
        baseline = values[:-1]
        avg = sum(baseline) / len(baseline)
        current = values[-1]
        anomalies = []
        if avg != 0:
            deviation = (current - avg) / abs(avg) * 100
            if abs(deviation) >= threshold_pct:
                anomalies.append({"point": current, "baseline_avg": round(avg, 2),
                                  "deviation_pct": round(deviation, 1),
                                  "direction": "spike" if deviation > 0 else "drop",
                                  "severity": "critical" if abs(deviation) >= threshold_pct * 2 else "warning"})
        for i in range(1, len(values)):
            window = values[max(0, i - 7):i]
            if len(window) < 3:
                continue
            wavg = sum(window) / len(window)
            if wavg == 0:
                continue
            dev = (values[i] - wavg) / abs(wavg) * 100
            if abs(dev) >= threshold_pct:
                anomalies.append({"index": i, "value": values[i], "baseline_avg": round(wavg, 2),
                                  "deviation_pct": round(dev, 1), "direction": "spike" if dev > 0 else "drop",
                                  "severity": "critical" if abs(dev) >= threshold_pct * 2 else "warning"})
        return {"status": "ok", "metric": p.get("metric", ""), "anomalies": anomalies, "count": len(anomalies)}


class PricingExperimentService:
    """Test price points against audience. ProfitWell pricing experiments."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._tests = _JsonStore("pricing_experiments.json")

    def register(self) -> None:
        reg = self.registry.register("experiments.pricing", version="1.0.0", metadata={"domain": "experiments", "type": "platform"})
        reg.actions["create"] = self._create
        reg.actions["list"] = self._list
        reg.actions["record_result"] = self._record
        reg.actions["analyze"] = self._analyze

    async def _create(self, p: dict[str, Any]) -> dict[str, Any]:
        test = {
            "test_id": f"ptest-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "name": p.get("name", ""),
            "price_points": p.get("price_points", []),
            "audience_size": int(p.get("audience_size", 0)),
            "results": {str(pt): {"exposed": 0, "converted": 0} for pt in p.get("price_points", [])},
            "created_at": datetime.now(UTC).isoformat(),
        }
        self._tests.upsert("test_id", test)
        return {"status": "created", "test": test}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        return {"status": "ok", "tests": [t for t in self._tests.load() if t.get("tenant_id") == tenant]}

    async def _record(self, p: dict[str, Any]) -> dict[str, Any]:
        data = self._tests.load()
        for t in data:
            if t.get("test_id") == p.get("test_id"):
                key = str(p.get("price_point"))
                b = t.setdefault("results", {}).setdefault(key, {"exposed": 0, "converted": 0})
                b["exposed"] += int(p.get("exposed", 0))
                b["converted"] += int(p.get("converted", 0))
                self._tests.save(data)
                return {"status": "recorded", "results": t["results"]}
        return {"status": "not_found"}

    async def _analyze(self, p: dict[str, Any]) -> dict[str, Any]:
        data = self._tests.load()
        for t in data:
            if t.get("test_id") == p.get("test_id"):
                rows = []
                for price, res in t.get("results", {}).items():
                    exposed = res.get("exposed", 0)
                    conv = res.get("converted", 0)
                    rate = (conv / exposed) if exposed else 0
                    rows.append({"price": float(price), "exposed": exposed, "converted": conv,
                                 "conversion_rate": round(rate * 100, 2),
                                 "revenue_per_exposed": round(float(price) * conv / exposed, 2) if exposed else 0})
                best = max(rows, key=lambda r: r["revenue_per_exposed"]) if rows else None
                return {"status": "ok", "test_id": t["test_id"], "results": rows, "best_price": best}
        return {"status": "not_found"}


class QBRService:
    """Generate quarterly business review content from account data. Gainsight QBRs."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._profiles = _JsonStore("customer_profiles.json")
        self._touchpoints = _JsonStore("touchpoints.json")

    def register(self) -> None:
        reg = self.registry.register("cs.qbr", version="1.0.0", metadata={"domain": "cs_ops", "type": "reporting"})
        reg.actions["generate"] = self._generate
        reg.actions["list"] = self._list

    async def _generate(self, p: dict[str, Any]) -> dict[str, Any]:
        cust = p.get("customer_id", "")
        prof = next((x for x in self._profiles.load() if x.get("id") == cust), {})
        touches = [t for t in self._touchpoints.load() if t.get("customer_id") == cust]
        period = p.get("period", "Q4")
        sections = [
            {"heading": "Account overview", "content": f"{prof.get('name', 'Customer')} on {prof.get('plan', 'n/a')} plan — MRR ${prof.get('mrr', 0)}, health {prof.get('health_score', 0)}/100."},
            {"heading": "Usage & outcomes", "content": f"Service next due: {prof.get('next_due_date') or 'n/a'} ({prof.get('days_until_due')} days). LTV ${prof.get('ltv', 0)}."},
            {"heading": "Touchpoints this period", "content": f"{len(touches)} touchpoints logged: " + (", ".join(t.get("type", "") for t in touches[:8]) or "none")},
            {"heading": "Risks", "content": "Health score below 60" if prof.get("health_score", 100) < 60 else "No critical risks identified"},
            {"heading": "Next steps", "content": "; ".join(p.get("next_steps", ["Continue quarterly success review"]))},
        ]
        qbr = {
            "qbr_id": f"qbr-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "customer_id": cust,
            "period": period,
            "sections": sections,
            "generated_at": datetime.now(UTC).isoformat(),
        }
        self._path = data_root() / "qbrs.json"
        store = _JsonStore("qbrs.json")
        store.upsert("qbr_id", qbr)
        return {"status": "generated", "qbr": qbr}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        store = _JsonStore("qbrs.json")
        return {"status": "ok", "qbrs": [q for q in store.load() if q.get("tenant_id") == tenant]}


__all__ = ["ABTestingService", "SequenceService", "CatalogService", "WallsService", "JourneyService", "AttributionService", "AnomalyDetectionService", "PricingExperimentService", "QBRService"]
