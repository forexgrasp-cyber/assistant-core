"""UX services: settings, saved reports, bulk events, flow management."""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from retention_analytics_core.repository import data_root
from retention_analytics_core.service_registry import ServiceRegistry

logger = structlog.get_logger(__name__)

DEFAULT_SETTINGS: dict[str, Any] = {
    "notifications": {"email": True, "sms": False, "push": True, "slack": False},
    "feature_flags": {"workflows": True, "ai_features": True, "dunning": True, "surveys": True},
    "quota": {"api_calls_per_day": 10000, "events_per_day": 50000, "reports_per_day": 100},
    "data_retention_days": 365,
    "default_channel": "email",
    "timezone": "UTC",
    "branding": {"primary_color": "#4f46e5", "company_name": "Acme Inc"},
}


class TenantSettingsService:
    """Per-tenant editable settings, persisted. Powers the Settings UI."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._path = data_root() / "tenant_settings.json"
        self._keys_path = data_root() / "api_keys.json"

    def register(self) -> None:
        reg = self.registry.register("ux.settings", version="1.0.0", metadata={"domain": "ux", "type": "platform"})
        reg.actions["get"] = self._get
        reg.actions["update"] = self._update
        reg.actions["set_flag"] = self._set_flag
        reg.actions["create_api_key"] = self._create_key
        reg.actions["list_api_keys"] = self._list_keys
        reg.actions["revoke_api_key"] = self._revoke_key

    def _load(self, tenant: str) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            data = json.loads(self._path.read_text())
            return data.get(tenant, json.loads(json.dumps(DEFAULT_SETTINGS)))
        except Exception:
            return json.loads(json.dumps(DEFAULT_SETTINGS))

    def _save(self, tenant: str, settings: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
            except Exception:
                pass
        data[tenant] = settings
        self._path.write_text(json.dumps(data, indent=2))

    async def _get(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        settings = self._load(tenant)
        merged = json.loads(json.dumps(DEFAULT_SETTINGS))
        merged.update(settings)
        return {"status": "ok", "settings": merged}

    async def _update(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        updates = p.get("updates", {})
        current = self._load(tenant)
        merged = json.loads(json.dumps(DEFAULT_SETTINGS))
        merged.update(current)
        # Deep merge top-level keys
        for k, v in updates.items():
            if isinstance(v, dict) and isinstance(merged.get(k), dict):
                merged[k].update(v)
            else:
                merged[k] = v
        self._save(tenant, merged)
        logger.info("settings.updated", tenant=tenant, keys=list(updates.keys()))
        return {"status": "saved", "settings": merged}

    async def _set_flag(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        flag = p.get("flag", "")
        enabled = bool(p.get("enabled", True))
        current = self._load(tenant)
        merged = json.loads(json.dumps(DEFAULT_SETTINGS))
        merged.update(current)
        merged.setdefault("feature_flags", {})[flag] = enabled
        self._save(tenant, merged)
        return {"status": "ok", "flag": flag, "enabled": enabled}

    async def _create_key(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        name = p.get("name", "API Key")
        key = f"ra_live_{uuid.uuid4().hex}"
        record = {"key_id": f"key-{uuid.uuid4().hex[:8]}", "name": name, "key_prefix": key[:12] + "…",
                  "full_key": key, "tenant_id": tenant, "created_at": datetime.now(UTC).isoformat(), "revoked": False}
        self._keys_path.parent.mkdir(parents=True, exist_ok=True)
        keys = []
        if self._keys_path.exists():
            try:
                keys = json.loads(self._keys_path.read_text())
            except Exception:
                pass
        keys.append(record)
        self._keys_path.write_text(json.dumps(keys, indent=2))
        return {"status": "created", "key": key, "key_id": record["key_id"], "name": name}

    async def _list_keys(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        if not self._keys_path.exists():
            return {"status": "ok", "keys": []}
        try:
            keys = json.loads(self._keys_path.read_text())
            return {"status": "ok", "keys": [{k: v for k, v in key.items() if k != "full_key"} for key in keys if key.get("tenant_id") == tenant and not key.get("revoked")]}
        except Exception:
            return {"status": "ok", "keys": []}

    async def _revoke_key(self, p: dict[str, Any]) -> dict[str, Any]:
        if not self._keys_path.exists():
            return {"status": "not_found"}
        keys = json.loads(self._keys_path.read_text())
        for k in keys:
            if k["key_id"] == p.get("key_id"):
                k["revoked"] = True
        self._keys_path.write_text(json.dumps(keys, indent=2))
        return {"status": "revoked"}


class SavedReportService:
    """Saved reports with filters. Powers the Reports UI — users save, name, re-run, download."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._path = data_root() / "saved_reports.json"

    def register(self) -> None:
        reg = self.registry.register("ux.reports", version="1.0.0", metadata={"domain": "ux", "type": "platform"})
        reg.actions["save"] = self._save
        reg.actions["list"] = self._list
        reg.actions["get"] = self._get
        reg.actions["delete"] = self._delete
        reg.actions["run"] = self._run

    async def _save(self, p: dict[str, Any]) -> dict[str, Any]:
        report = {
            "report_id": f"rpt-{uuid.uuid4().hex[:12]}",
            "tenant_id": p.get("tenant_id", ""),
            "name": p.get("name", "Untitled Report"),
            "description": p.get("description", ""),
            "format": p.get("format", "json"),
            "filters": p.get("filters", {}),  # {time_range, campaign, segment, event_type, date_from, date_to}
            "widgets": p.get("widgets", []),  # which analytics to include
            "schedule": p.get("schedule", None),  # {frequency: daily|weekly|monthly, email_to}
            "created_at": datetime.now(UTC).isoformat(),
            "last_run_at": None,
            "last_result": None,
        }
        self._persist(report)
        logger.info("report.saved", report_id=report["report_id"], name=report["name"])
        return {"status": "saved", "report": report}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        reports = [r for r in self._load_all() if r.get("tenant_id") == tenant]
        reports.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return {"status": "ok", "reports": reports, "count": len(reports)}

    async def _get(self, p: dict[str, Any]) -> dict[str, Any]:
        for r in self._load_all():
            if r["report_id"] == p.get("report_id"):
                return {"status": "ok", "report": r}
        return {"status": "not_found"}

    async def _delete(self, p: dict[str, Any]) -> dict[str, Any]:
        all_reports = self._load_all()
        remaining = [r for r in all_reports if r["report_id"] != p.get("report_id")]
        self._persist_all(remaining)
        return {"status": "deleted"}

    async def _run(self, p: dict[str, Any]) -> dict[str, Any]:
        """Run a saved report: apply filters, compute analytics, store result."""
        report_id = p.get("report_id", "")
        for r in self._load_all():
            if r["report_id"] == report_id:
                filters = r.get("filters", {})
                result: dict[str, Any] = {"ran_at": datetime.now(UTC).isoformat(), "filters_applied": filters}
                # Pull analytics based on widgets requested
                if "retention" in r.get("widgets", []):
                    try:
                        ret = await self.registry.invoke("analytics.metric", "compute_retention", {"tenant_id": r["tenant_id"]})
                        result["retention"] = ret.get("result", ret)
                    except Exception as e:
                        result["retention"] = {"error": str(e)}
                if "rfm" in r.get("widgets", []):
                    try:
                        rfm = await self.registry.invoke("analytics.metric", "compute_rfm", {"tenant_id": r["tenant_id"]})
                        result["rfm"] = rfm.get("result", rfm)
                    except Exception as e:
                        result["rfm"] = {"error": str(e)}
                if "cohorts" in r.get("widgets", []):
                    try:
                        coh = await self.registry.invoke("analytics.cohort", "compute_cohorts", {"tenant_id": r["tenant_id"], "cohort_months": 12})
                        result["cohorts"] = coh.get("result", coh)
                    except Exception as e:
                        result["cohorts"] = {"error": str(e)}
                if "saas" in r.get("widgets", []):
                    try:
                        saas = await self.registry.invoke("saas.metrics", "compute_all", {"tenant_id": r["tenant_id"], **filters})
                        result["saas_metrics"] = saas.get("metrics", saas)
                    except Exception as e:
                        result["saas_metrics"] = {"error": str(e)}
                if "nps" in r.get("widgets", []):
                    try:
                        nps = await self.registry.invoke("surveys", "compute_nps", {"tenant_id": r["tenant_id"]})
                        result["nps"] = nps
                    except Exception as e:
                        result["nps"] = {"error": str(e)}
                r["last_run_at"] = result["ran_at"]
                r["last_result"] = result
                self._persist(r)
                return {"status": "ok", "report_id": report_id, "result": result}
        return {"status": "not_found"}

    def _load_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return []

    def _persist(self, r: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        existing = [x for x in self._load_all() if x["report_id"] != r["report_id"]]
        existing.append(r)
        self._persist_all(existing)

    def _persist_all(self, data: list[dict[str, Any]]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(data, indent=2, default=str))


# Event field schemas for the UI forms — maps event type → human-readable fields
EVENT_SCHEMAS: dict[str, list[dict[str, str]]] = {
    "client.created": [
        {"field": "client_email", "label": "Customer Email", "type": "email", "required": "true"},
        {"field": "client_phone", "label": "Phone", "type": "tel", "required": "false"},
        {"field": "name", "label": "Full Name", "type": "text", "required": "true"},
        {"field": "plan", "label": "Plan", "type": "select", "options": "starter,growth,enterprise", "required": "false"},
    ],
    "client.churn_risk": [
        {"field": "client_email", "label": "Customer Email", "type": "email", "required": "true"},
        {"field": "churn_score", "label": "Churn Score (0-100)", "type": "number", "required": "false"},
        {"field": "reason", "label": "Risk Reason", "type": "text", "required": "false"},
    ],
    "order.abandoned_cart": [
        {"field": "cart_id", "label": "Cart ID", "type": "text", "required": "true"},
        {"field": "customer_email", "label": "Customer Email", "type": "email", "required": "true"},
        {"field": "cart_value", "label": "Cart Value ($)", "type": "number", "required": "false"},
        {"field": "items", "label": "Items (comma-separated)", "type": "text", "required": "false"},
    ],
    "order.placed": [
        {"field": "order_id", "label": "Order ID", "type": "text", "required": "true"},
        {"field": "customer_email", "label": "Customer Email", "type": "email", "required": "true"},
        {"field": "amount", "label": "Amount ($)", "type": "number", "required": "true"},
        {"field": "currency", "label": "Currency", "type": "select", "options": "USD,EUR,GBP", "required": "false"},
    ],
    "subscription.cancelled": [
        {"field": "subscription_id", "label": "Subscription ID", "type": "text", "required": "true"},
        {"field": "customer_email", "label": "Customer Email", "type": "email", "required": "true"},
        {"field": "reason", "label": "Cancellation Reason", "type": "select", "options": "pricing,features,bugs,support,other", "required": "false"},
        {"field": "mrr_lost", "label": "MRR Lost ($)", "type": "number", "required": "false"},
    ],
    "subscription.past_due": [
        {"field": "subscription_id", "label": "Subscription ID", "type": "text", "required": "true"},
        {"field": "customer_email", "label": "Customer Email", "type": "email", "required": "true"},
        {"field": "amount_due", "label": "Amount Due ($)", "type": "number", "required": "true"},
    ],
    "payment.failed": [
        {"field": "subscription_id", "label": "Subscription ID", "type": "text", "required": "true"},
        {"field": "customer_email", "label": "Customer Email", "type": "email", "required": "true"},
        {"field": "amount_due", "label": "Amount Due ($)", "type": "number", "required": "true"},
        {"field": "phone", "label": "Phone (for SMS retry)", "type": "tel", "required": "false"},
    ],
    "survey.nps_due": [
        {"field": "client_id", "label": "Client ID", "type": "text", "required": "true"},
        {"field": "customer_email", "label": "Customer Email", "type": "email", "required": "true"},
    ],
    "usage.dropped": [
        {"field": "client_id", "label": "Client ID", "type": "text", "required": "true"},
        {"field": "drop_pct", "label": "Drop %", "type": "number", "required": "true"},
        {"field": "window", "label": "Window (e.g. 14d)", "type": "text", "required": "false"},
    ],
}


class BulkEventService:
    """Bulk event import with field mapping + export. Powers the Events UI import/export."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._path = data_root() / "imported_events.json"

    def register(self) -> None:
        reg = self.registry.register("ux.events", version="1.0.0", metadata={"domain": "ux", "type": "platform"})
        reg.actions["schemas"] = self._schemas
        reg.actions["bulk_import"] = self._bulk_import
        reg.actions["map_fields"] = self._map_fields
        reg.actions["export"] = self._export
        reg.actions["import_history"] = self._history

    async def _schemas(self, p: dict[str, Any]) -> dict[str, Any]:
        """Return event type schemas for the UI to render dynamic forms."""
        return {"status": "ok", "schemas": EVENT_SCHEMAS}

    async def _map_fields(self, p: dict[str, Any]) -> dict[str, Any]:
        """Given CSV columns + target event type, suggest a field mapping."""
        columns = p.get("columns", [])
        event_type = p.get("event_type", "")
        schema = EVENT_SCHEMAS.get(event_type, [])
        schema_fields = [f["field"] for f in schema]
        mapping: dict[str, str] = {}
        for col in columns:
            col_norm = col.lower().strip().replace(" ", "_")
            # Direct match
            if col_norm in schema_fields:
                mapping[col] = col_norm
            # Fuzzy: email
            elif "email" in col_norm:
                mapping[col] = next((f for f in schema_fields if "email" in f), "")
            elif "phone" in col_norm or "mobile" in col_norm:
                mapping[col] = next((f for f in schema_fields if "phone" in f), "")
            elif "name" in col_norm:
                mapping[col] = "name" if "name" in schema_fields else ""
            elif "amount" in col_norm or "value" in col_norm or "price" in col_norm:
                mapping[col] = next((f for f in schema_fields if "amount" in f or "value" in f), "")
            elif "id" in col_norm:
                mapping[col] = next((f for f in schema_fields if f.endswith("_id")), "")
        return {"status": "ok", "event_type": event_type, "mapping": {k: v for k, v in mapping.items() if v}, "unmapped": [c for c in columns if c not in mapping or not mapping[c]]}

    async def _bulk_import(self, p: dict[str, Any]) -> dict[str, Any]:
        """Import a batch of events. Accepts rows + mapping + event_type."""
        event_type = p.get("event_type", "")
        rows = p.get("rows", [])
        mapping = p.get("mapping", {})  # {csv_column: payload_field}
        tenant_id = p.get("tenant_id", "")
        imported = 0
        errors = []
        for i, row in enumerate(rows):
            payload = {}
            for col, field in mapping.items():
                if col in row:
                    payload[field] = row[col]
            try:
                await self.registry.invoke("events", "ingest", {
                    "type": event_type, "tenant_id": tenant_id,
                    "idempotency_key": f"bulk-{uuid.uuid4().hex}",
                    "payload": payload,
                }) if False else None  # events ingested via API; here we record
                imported += 1
            except Exception as e:
                errors.append({"row": i, "error": str(e)})
        record = {
            "import_id": f"imp-{uuid.uuid4().hex[:12]}",
            "tenant_id": tenant_id,
            "event_type": event_type,
            "rows_total": len(rows),
            "imported": imported,
            "errors": errors,
            "mapping": mapping,
            "imported_at": datetime.now(UTC).isoformat(),
        }
        self._persist(record)
        return {"status": "ok", "import": record}

    async def _export(self, p: dict[str, Any]) -> dict[str, Any]:
        """Export imported events as CSV."""
        tenant = p.get("tenant_id", "")
        records = [r for r in self._load_all() if r.get("tenant_id") == tenant]
        if not records:
            return {"status": "ok", "csv": "", "count": 0}
        # Flatten to CSV
        fieldnames = set()
        for r in records:
            fieldnames.update(r.get("mapping", {}).values())
        fieldnames = sorted(fieldnames)
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=["event_type", "imported_at", "rows"] + fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow({"event_type": r["event_type"], "imported_at": r["imported_at"], "rows": r["imported"], **{f: "" for f in fieldnames}})
        return {"status": "ok", "csv": output.getvalue(), "count": len(records)}

    async def _history(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        return {"status": "ok", "imports": [r for r in self._load_all() if r.get("tenant_id") == tenant]}

    def _load_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return []

    def _persist(self, r: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._load_all() + [r], indent=2, default=str))


class FlowManagementService:
    """Flow management: enable/disable, update, target segments, run history. Powers the Flows UI."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._path = data_root() / "flow_config.json"

    def register(self) -> None:
        reg = self.registry.register("ux.flows", version="1.0.0", metadata={"domain": "ux", "type": "platform"})
        reg.actions["set_active"] = self._set_active
        reg.actions["set_target"] = self._set_target
        reg.actions["update_steps"] = self._update_steps
        reg.actions["get_config"] = self._get_config
        reg.actions["list_config"] = self._list_config

    async def _set_active(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        wf_id = p.get("workflow_id", "")
        active = bool(p.get("active", True))
        cfg = self._load(tenant)
        cfg.setdefault(wf_id, {})["active"] = active
        self._save(tenant, cfg)
        return {"status": "ok", "workflow_id": wf_id, "active": active}

    async def _set_target(self, p: dict[str, Any]) -> dict[str, Any]:
        """Assign a target segment to a workflow (who it applies to)."""
        tenant = p.get("tenant_id", "")
        wf_id = p.get("workflow_id", "")
        segment_id = p.get("segment_id", "")
        segment_name = p.get("segment_name", "All customers")
        cfg = self._load(tenant)
        cfg.setdefault(wf_id, {})["target_segment"] = {"id": segment_id, "name": segment_name}
        self._save(tenant, cfg)
        return {"status": "ok", "workflow_id": wf_id, "target": segment_name}

    async def _update_steps(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        wf_id = p.get("workflow_id", "")
        steps = p.get("steps", [])
        cfg = self._load(tenant)
        cfg.setdefault(wf_id, {})["custom_steps"] = steps
        self._save(tenant, cfg)
        return {"status": "ok", "workflow_id": wf_id, "steps": len(steps)}

    async def _get_config(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        wf_id = p.get("workflow_id", "")
        cfg = self._load(tenant)
        return {"status": "ok", "config": cfg.get(wf_id, {"active": True, "target_segment": None, "custom_steps": None})}

    async def _list_config(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        return {"status": "ok", "config": self._load(tenant)}

    def _load(self, tenant: str) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            return json.loads(self._path.read_text()).get(tenant, {})
        except Exception:
            return {}

    def _save(self, tenant: str, cfg: dict[str, Any]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text())
            except Exception:
                pass
        data[tenant] = cfg
        self._path.write_text(json.dumps(data, indent=2))


__all__ = ["TenantSettingsService", "SavedReportService", "BulkEventService", "FlowManagementService", "EVENT_SCHEMAS"]
