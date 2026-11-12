"""Data transfer: CSV/JSON import + export for customers, campaigns, and any dataset.

Customers page gets a real import (CSV with column mapping) and export.
Extends the events bulk-import pattern to all major datasets.
"""

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
from retention_analytics_advanced.customer_intel import _JsonStore

logger = structlog.get_logger(__name__)


class DataTransferService:
    """Import/export customers, campaigns, and more as CSV/JSON."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._imports = _JsonStore("data_imports.json")

    def register(self) -> None:
        reg = self.registry.register("data.transfer", version="1.0.0", metadata={"domain": "platform", "type": "io"})
        reg.actions["import_customers"] = self._import_customers
        reg.actions["export_customers"] = self._export_customers
        reg.actions["export_campaigns"] = self._export_campaigns
        reg.actions["import_campaigns"] = self._import_campaigns
        reg.actions["suggest_mapping"] = self._suggest_mapping
        reg.actions["history"] = self._history

    async def _suggest_mapping(self, p: dict[str, Any]) -> dict[str, Any]:
        """Suggest CSV column -> customer field mapping (fuzzy, like events)."""
        columns = p.get("columns", [])
        fields = ["id", "name", "email", "phone", "plan", "mrr", "ltv", "health_score",
                  "last_service_date", "service_interval_days", "service_name", "attributes"]
        mapping: dict[str, str] = {}
        for col in columns:
            c = col.lower().strip().replace(" ", "_")
            if c in fields:
                mapping[col] = c
            elif "email" in c or "e-mail" in c:
                mapping[col] = "email"
            elif "phone" in c or "mobile" in c:
                mapping[col] = "phone"
            elif "name" in c:
                mapping[col] = "name"
            elif c in ("value", "amount", "price"):
                mapping[col] = "mrr"
            elif "plan" in c or "tier" in c:
                mapping[col] = "plan"
            elif "service" in c and "date" in c:
                mapping[col] = "last_service_date"
            elif "interval" in c:
                mapping[col] = "service_interval_days"
            elif "due" in c:
                mapping[col] = "last_service_date"
        return {"status": "ok", "mapping": mapping, "unmapped": [c for c in columns if c not in mapping]}

    async def _import_customers(self, p: dict[str, Any]) -> dict[str, Any]:
        """Import customers from CSV text + mapping. Creates/updates customer profiles."""
        csv_text = p.get("csv", "")
        mapping = p.get("mapping", {})
        tenant = p.get("tenant_id", "")
        reader = csv.DictReader(io.StringIO(csv_text))
        columns = reader.fieldnames or []
        if not mapping:
            mapping = (await self._suggest_mapping({"columns": columns}))["mapping"]
        created = updated = 0
        errors = []
        profiles = _JsonStore("customer_profiles.json")
        existing = {x.get("id"): x for x in profiles.load()}
        for i, row in enumerate(reader):
            data: dict[str, Any] = {"tenant_id": tenant}
            for col, field in mapping.items():
                if col in row and row[col] != "":
                    v: Any = row[col]
                    if field in ("mrr", "ltv", "health_score", "service_interval_days"):
                        try:
                            v = float(v) if field != "service_interval_days" else int(float(v))
                        except ValueError:
                            pass
                    data[field] = v
            cid = data.get("id") or data.get("email") or f"imp-{uuid.uuid4().hex[:10]}"
            data["id"] = cid
            data["updated_at"] = datetime.now(UTC).isoformat()
            # compute due fields if service fields present
            from retention_analytics_advanced.customer_intel import compute_due
            data["next_due_date"], data["days_until_due"] = compute_due(
                data.get("last_service_date"), int(data.get("service_interval_days") or 0))
            if cid in existing:
                updated += 1
            else:
                created += 1
            existing[cid] = data
        profiles.save(list(existing.values()))
        rec = {"import_id": f"imp-{uuid.uuid4().hex[:12]}", "tenant_id": tenant,
               "dataset": "customers", "created": created, "updated": updated,
               "rows": created + updated, "errors": errors, "mapping": mapping,
               "imported_at": datetime.now(UTC).isoformat()}
        self._imports.upsert("import_id", rec)
        logger.info("customers.imported", created=created, updated=updated)
        return {"status": "ok", "import": rec}

    async def _export_customers(self, p: dict[str, Any]) -> dict[str, Any]:
        """Export customers as CSV or JSON."""
        tenant = p.get("tenant_id", "")
        fmt = p.get("format", "csv")
        profiles = [x for x in _JsonStore("customer_profiles.json").load() if x.get("tenant_id") == tenant]
        if fmt == "json":
            return {"status": "ok", "format": "json", "count": len(profiles), "data": profiles}
        if not profiles:
            return {"status": "ok", "format": "csv", "csv": "", "count": 0}
        keys = ["id", "name", "email", "phone", "plan", "mrr", "ltv", "health_score",
                "service_name", "last_service_date", "service_interval_days", "next_due_date", "days_until_due"]
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=keys, extrasaction="ignore")
        w.writeheader()
        for pr in profiles:
            w.writerow(pr)
        return {"status": "ok", "format": "csv", "csv": out.getvalue(), "count": len(profiles)}

    async def _export_campaigns(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        fmt = p.get("format", "csv")
        camps = [c for c in _JsonStore("campaigns.json").load() if c.get("tenant_id") == tenant]
        if fmt == "json":
            return {"status": "ok", "format": "json", "count": len(camps), "data": camps}
        if not camps:
            return {"status": "ok", "format": "csv", "csv": "", "count": 0}
        keys = ["campaign_id", "name", "goal", "status", "segment", "flows", "schedule", "success_metrics", "created_at"]
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=keys)
        w.writeheader()
        for c in camps:
            row = dict(c)
            for k in ("segment", "flows", "schedule", "success_metrics"):
                if k in row:
                    row[k] = json.dumps(row[k])
            w.writerow({k: row.get(k, "") for k in keys})
        return {"status": "ok", "format": "csv", "csv": out.getvalue(), "count": len(camps)}

    async def _import_campaigns(self, p: dict[str, Any]) -> dict[str, Any]:
        """Import campaign definitions from CSV/JSON rows."""
        tenant = p.get("tenant_id", "")
        rows = p.get("rows", [])
        camps = _JsonStore("campaigns.json")
        created = 0
        for row in rows:
            camp = {
                "campaign_id": f"camp-{uuid.uuid4().hex[:12]}",
                "tenant_id": tenant,
                "name": row.get("name", "Imported"),
                "goal": row.get("goal", "reduce_churn"),
                "segment": json.loads(row["segment"]) if isinstance(row.get("segment"), str) and row.get("segment") else {"id": "all", "name": "All", "criteria": {}},
                "flows": json.loads(row["flows"]) if isinstance(row.get("flows"), str) and row.get("flows") else [],
                "schedule": {"type": "once"},
                "success_metrics": json.loads(row["success_metrics"]) if isinstance(row.get("success_metrics"), str) and row.get("success_metrics") else [],
                "status": "draft",
                "created_at": datetime.now(UTC).isoformat(),
                "runs": [], "results": None,
            }
            camps.upsert("campaign_id", camp)
            created += 1
        return {"status": "ok", "created": created}

    async def _history(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        return {"status": "ok", "imports": [i for i in self._imports.load() if i.get("tenant_id") == tenant]}


__all__ = ["DataTransferService"]
