"""Universal preset catalog: industry bundles that can be applied to ANY business.

A preset is NOT a structural vertical — it is a shortcut bundle of
(customer record fields, segments, flows, campaigns, sequences, templates,
benchmark industry, service schedule). Apply it to any industry where the
customer data supports the fields; ignore it and build your own.

The engine underneath is fully universal: every feature works on any customer
record fields the tenant has.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from retention_analytics_core.repository import data_root
from retention_analytics_core.service_registry import ServiceRegistry

logger = structlog.get_logger(__name__)

PRESETS: dict[str, dict[str, Any]] = {
    "automotive": {
        "name": "Auto Service & Maintenance",
        "description": "Oil changes, tire rotations, inspections — remind customers when service is due and win back overdue customers.",
        "benchmarks": "automotive",
        "customer_fields": {
            "vehicle_make": "string", "vehicle_model": "string", "vehicle_year": "number",
            "mileage": "number", "last_service_date": "date", "service_interval_days": "number",
            "service_name": "string", "next_due_date": "date",
        },
        "segments": [
            {"name": "Oil change due soon", "criteria": {"days_until_due": {"lte": 7, "gte": 0}}},
            {"name": "Service overdue", "criteria": {"days_until_due": {"lt": 0}}},
            {"name": "High mileage customers", "criteria": {"mileage": {"gt": 50000}}},
        ],
        "campaigns": [
            {"name": "Oil change reminder", "goal": "reactivate", "segment": "Oil change due soon",
             "flows": ["service-due-reminder"], "schedule": {"type": "daily"},
             "metrics": ["reactivation_rate"], "message": "Your oil change is due on {next_due_date}. Book now."},
            {"name": "Overdue service win-back", "goal": "reactivate", "segment": "Service overdue",
             "flows": ["service-overdue", "win-back"], "schedule": {"type": "daily"},
             "metrics": ["reactivation_rate"], "message": "Your {service_name} was due on {next_due_date}. Let's get you back on the road."},
        ],
        "sequences": [
            {"name": "Oil change 3-touch", "steps": [
                {"delay_days": 0, "channel": "email", "subject": "Your oil change is coming up", "body": "Book now to avoid engine wear."},
                {"delay_days": 3, "channel": "sms", "subject": "", "body": "Reminder: oil change due soon. Reply to book."},
                {"delay_days": 7, "channel": "email", "subject": "Last reminder - oil change", "body": "We still have slots this week."},
            ]},
        ],
    },
    "beauty": {
        "name": "Beauty & Spa Memberships",
        "description": "Treatments, facials, memberships — keep clients coming back on schedule.",
        "benchmarks": "beauty",
        "customer_fields": {
            "preferred_treatment": "string", "last_appointment_date": "date",
            "treatment_interval_days": "number", "service_name": "string",
            "membership_tier": "string", "next_due_date": "date",
        },
        "segments": [
            {"name": "Treatment due", "criteria": {"days_until_due": {"lte": 10, "gte": 0}}},
            {"name": "Lapsed members", "criteria": {"days_until_due": {"lt": -21}}},
            {"name": "VIP tier", "criteria": {"membership_tier": "vip"}},
        ],
        "campaigns": [
            {"name": "Treatment due reminder", "goal": "reactivate", "segment": "Treatment due",
             "flows": ["service-due-reminder"], "schedule": {"type": "daily"},
             "metrics": ["reactivation_rate"], "message": "Your {service_name} is due on {next_due_date}. Reserve your slot."},
            {"name": "Lapsed member win-back", "goal": "reactivate", "segment": "Lapsed members",
             "flows": ["win-back", "reactivation"], "schedule": {"type": "weekly"},
             "metrics": ["reactivation_rate", "mrr_won_back"], "message": "We miss you! 25% off your next treatment."},
        ],
        "sequences": [
            {"name": "Lapsed member 4-touch", "steps": [
                {"delay_days": 0, "channel": "email", "subject": "We miss your glow", "body": "Come back for 25% off."},
                {"delay_days": 5, "channel": "sms", "subject": "", "body": "25% off your next treatment - reply YES to book."},
                {"delay_days": 12, "channel": "email", "subject": "Your personal offer expires soon", "body": "Your 25% offer expires in 3 days."},
                {"delay_days": 21, "channel": "push", "subject": "", "body": "We saved a spot for you."},
            ]},
        ],
    },
    "fitness": {
        "name": "Fitness & Gym Memberships",
        "description": "Class packs, memberships, inactivity — re-engage members who stop showing up.",
        "benchmarks": "fitness",
        "customer_fields": {
            "membership_type": "string", "last_visit_date": "date",
            "visit_interval_days": "number", "classes_remaining": "number",
            "service_name": "string", "next_due_date": "date",
        },
        "segments": [
            {"name": "Membership renews soon", "criteria": {"days_until_due": {"lte": 7, "gte": 0}}},
            {"name": "Inactive 14+ days", "criteria": {"days_until_due": {"lt": -14}}},
            {"name": "Low class credits", "criteria": {"classes_remaining": {"lt": 3}}},
        ],
        "campaigns": [
            {"name": "Renewal reminder", "goal": "reduce_churn", "segment": "Membership renews soon",
             "flows": ["renewal-reminder"], "schedule": {"type": "daily"},
             "metrics": ["renewal_rate"], "message": "Your membership renews on {next_due_date}."},
            {"name": "Inactive member re-engagement", "goal": "reactivate", "segment": "Inactive 14+ days",
             "flows": ["usage-drop-alert", "reactivation"], "schedule": {"type": "weekly"},
             "metrics": ["reactivation_rate"], "message": "We miss you at the gym! Come back this week."},
        ],
        "sequences": [
            {"name": "Win-back 3-touch", "steps": [
                {"delay_days": 0, "channel": "push", "subject": "", "body": "Your membership is paused too long - come back free."},
                {"delay_days": 3, "channel": "email", "subject": "Free week waiting", "body": "Your first week back is on us."},
                {"delay_days": 10, "channel": "sms", "subject": "", "body": "Free week still open. Reply to claim."},
            ]},
        ],
    },
    "saas": {
        "name": "SaaS Subscriptions",
        "description": "Trials, onboarding, dunning, expansion, churn prevention.",
        "benchmarks": "saas",
        "customer_fields": {
            "plan": "string", "mrr": "number", "seats": "number", "trial_end_date": "date",
            "renewal_date": "date", "service_interval_days": "number", "next_due_date": "date",
        },
        "segments": [
            {"name": "Trial ending", "criteria": {"trial_end_date": {"lte": 7}}},
            {"name": "At risk", "criteria": {"health_score": {"lt": 50}}},
            {"name": "Expansion ready", "criteria": {"seats": {"gt": 10}}},
        ],
        "campaigns": [
            {"name": "Trial conversion", "goal": "activate_trials", "segment": "Trial ending",
             "flows": ["trial-conversion"], "schedule": {"type": "daily"},
             "metrics": ["conversion_rate"], "message": "Your trial ends soon — convert and keep your data."},
            {"name": "Churn prevention", "goal": "reduce_churn", "segment": "At risk",
             "flows": ["churn-prevention", "health-score-alert"], "schedule": {"type": "weekly"},
             "metrics": ["retention", "churn_rate"], "message": "We want to help — here's what's new."},
        ],
        "sequences": [
            {"name": "Onboarding 5-touch", "steps": [
                {"delay_days": 0, "channel": "email", "subject": "Welcome aboard", "body": "Let's set up your workspace."},
                {"delay_days": 2, "channel": "email", "subject": "Quick start guide", "body": "3 steps to value."},
                {"delay_days": 7, "channel": "email", "subject": "Book a setup call", "body": "Free onboarding session."},
                {"delay_days": 14, "channel": "push", "subject": "", "body": "Your team hasn't logged in yet."},
                {"delay_days": 30, "channel": "email", "subject": "Still need help?", "body": "Book a 15-min consult."},
            ]},
        ],
    },
    "healthcare": {
        "name": "Healthcare & Appointments",
        "description": "Appointment reminders, no-show reduction, care-plan adherence.",
        "benchmarks": "healthcare",
        "customer_fields": {
            "patient_name": "string", "last_appointment_date": "date",
            "appointment_interval_days": "number", "care_plan": "string",
            "provider": "string", "next_due_date": "date",
        },
        "segments": [
            {"name": "Appointment due", "criteria": {"days_until_due": {"lte": 3, "gte": 0}}},
            {"name": "Overdue care plan", "criteria": {"days_until_due": {"lt": -7}}},
        ],
        "campaigns": [
            {"name": "Appointment reminder", "goal": "reactivate", "segment": "Appointment due",
             "flows": ["service-due-reminder"], "schedule": {"type": "daily"},
             "metrics": ["reactivation_rate"], "message": "Your appointment is on {next_due_date}. Reply to confirm."},
        ],
        "sequences": [
            {"name": "Appointment 3-touch", "steps": [
                {"delay_days": 0, "channel": "email", "subject": "Appointment coming up", "body": "Please confirm."},
                {"delay_days": 1, "channel": "sms", "subject": "", "body": "Reminder: appointment on {next_due_date}. Reply C to confirm."},
                {"delay_days": 2, "channel": "sms", "subject": "", "body": "We still have slots today. Reply to book."},
            ]},
        ],
    },
    "ecommerce": {
        "name": "Ecommerce & Subscriptions",
        "description": "Cart recovery, replenishment reminders, subscription upsell.",
        "benchmarks": "ecommerce",
        "customer_fields": {
            "average_order_value": "number", "last_purchase_date": "date",
            "replenishment_interval_days": "number", "cart_id": "string",
            "service_name": "string", "next_due_date": "date",
        },
        "segments": [
            {"name": "Replenishment due", "criteria": {"days_until_due": {"lte": 5, "gte": 0}}},
            {"name": "Lapsed buyers", "criteria": {"days_until_due": {"lt": -60}}},
        ],
        "campaigns": [
            {"name": "Replenishment reminder", "goal": "reactivate", "segment": "Replenishment due",
             "flows": ["service-due-reminder"], "schedule": {"type": "daily"},
             "metrics": ["reactivation_rate"], "message": "Time to reorder your {service_name}."},
            {"name": "Lapsed buyer win-back", "goal": "reactivate", "segment": "Lapsed buyers",
             "flows": ["win-back", "reactivation"], "schedule": {"type": "weekly"},
             "metrics": ["reactivation_rate"], "message": "We saved your favorites — 15% off."},
        ],
        "sequences": [],
    },
}


class PresetCatalogService:
    """Browse and apply universal industry presets (not structural verticals)."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._path = data_root() / "applied_presets.json"

    def register(self) -> None:
        reg = self.registry.register("presets", version="1.0.0", metadata={"domain": "platform", "type": "catalog"})
        reg.actions["list"] = self._list
        reg.actions["get"] = self._get
        reg.actions["apply"] = self._apply
        reg.actions["applied"] = self._applied

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok", "presets": [
            {"id": k, "name": v["name"], "description": v["description"],
             "segments": len(v.get("segments", [])), "campaigns": len(v.get("campaigns", [])),
             "sequences": len(v.get("sequences", [])), "fields": len(v.get("customer_fields", {})),
             "note": "Applies to ANY business whose customer records have these fields"}
            for k, v in PRESETS.items()
        ], "count": len(PRESETS)}

    async def _get(self, p: dict[str, Any]) -> dict[str, Any]:
        pid = p.get("preset_id", "")
        if pid not in PRESETS:
            return {"status": "not_found"}
        return {"status": "ok", "preset": {"id": pid, **PRESETS[pid]}}

    async def _apply(self, p: dict[str, Any]) -> dict[str, Any]:
        """Apply a preset: create its segments, campaigns, sequences. Purely additive —
        the tenant can edit, combine with other presets, or ignore them entirely."""
        pid = p.get("preset_id", "")
        preset = PRESETS.get(pid)
        if not preset:
            return {"status": "not_found"}
        tenant_id = p.get("tenant_id", "")

        created_segments, created_campaigns, created_sequences = [], [], []
        # Segments
        try:
            seg = await self.registry.invoke("segmentation", "define_segment", {
                "tenant_id": tenant_id, "segment_id": f"{pid}-{(preset.get('segments') or [{}])[0].get('name', 'default')[:20] if preset.get('segments') else 'default'}",
                "name": f"{preset['name']}", "criteria": {},
            })
            created_segments.append(seg)
        except Exception as e:
            logger.warning("preset.segment_failed", error=str(e))
        # Campaign templates (as draft campaigns users can then configure)
        for c in preset.get("campaigns", []):
            try:
                camp = await self.registry.invoke("campaigns", "create", {
                    "tenant_id": tenant_id, "name": f"{c['name']}", "description": c.get("message", ""),
                    "goal": c.get("goal", "reduce_churn"),
                    "segment": {"id": c.get("segment", ""), "name": c.get("segment", ""), "criteria": next((s.get("criteria", {}) for s in preset.get("segments", []) if s.get("name") == c.get("segment")), {})},
                    "flows": c.get("flows", []), "schedule": c.get("schedule", {"type": "once"}),
                    "success_metrics": c.get("metrics", []),
                })
                created_campaigns.append(camp)
            except Exception as e:
                logger.warning("preset.campaign_failed", error=str(e))
        # Sequences
        for s in preset.get("sequences", []):
            try:
                seq = await self.registry.invoke("automation.sequences", "create", {
                    "tenant_id": tenant_id, "name": s.get("name", "Sequence"), "steps": s.get("steps", []),
                })
                created_sequences.append(seq)
            except Exception as e:
                logger.warning("preset.sequence_failed", error=str(e))

        record = {
            "application_id": f"preset-{uuid.uuid4().hex[:12]}",
            "tenant_id": tenant_id,
            "preset_id": pid,
            "segments_created": len(created_segments),
            "campaigns_created": len(created_campaigns),
            "sequences_created": len(created_sequences),
            "customer_fields": preset.get("customer_fields", {}),
            "benchmark_industry": preset.get("benchmarks"),
            "applied_at": datetime.now(UTC).isoformat(),
        }
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = []
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
            except Exception:
                pass
        data.append(record)
        self._path.write_text(json.dumps(data, indent=2, default=str))
        return {"status": "applied", "application": record}

    async def _applied(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        data = []
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
            except Exception:
                pass
        return {"status": "ok", "applications": [a for a in data if a.get("tenant_id") == tenant]}


__all__ = ["PresetCatalogService", "PRESETS"]
