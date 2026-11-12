"""Chart/metric annotations — notes tied to a metric + date (Baremetrics Trial Insights style)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import structlog

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced.customer_intel import _JsonStore

logger = structlog.get_logger(__name__)


class AnnotationService:
    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._notes = _JsonStore("metric_annotations.json")

    def register(self) -> None:
        reg = self.registry.register("analytics.annotations", version="1.0.0", metadata={"domain": "analytics", "type": "collaboration"})
        reg.actions["create"] = self._create
        reg.actions["list"] = self._list
        reg.actions["delete"] = self._delete

    async def _create(self, p: dict[str, Any]) -> dict[str, Any]:
        note = {
            "annotation_id": f"ann-{uuid.uuid4().hex[:10]}",
            "tenant_id": p.get("tenant_id", ""),
            "metric": p.get("metric", ""),
            "note": p.get("note", ""),
            "author": p.get("author", ""),
            "at": p.get("at", datetime.now(UTC).isoformat()),
            "color": p.get("color", "indigo"),
        }
        self._notes.upsert("annotation_id", note)
        return {"status": "created", "annotation": note}

    async def _list(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        metric = p.get("metric")
        rows = [n for n in self._notes.load() if n.get("tenant_id") == tenant and (not metric or n.get("metric") == metric)]
        rows.sort(key=lambda x: x.get("at", ""), reverse=True)
        return {"status": "ok", "annotations": rows, "count": len(rows)}

    async def _delete(self, p: dict[str[str, Any]]) -> dict[str, Any]:  # type: ignore[valid-type]
        self._notes.save([n for n in self._notes.load() if n.get("annotation_id") != p.get("annotation_id")])
        return {"status": "deleted"}


__all__ = ["AnnotationService"]
