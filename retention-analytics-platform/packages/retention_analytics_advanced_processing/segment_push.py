"""Push segments back to marketing platforms to activate them (Klaviyo and friends).

Hiro ships "push segments to Klaviyo to act on them". We close the loop the same
way: take a computed segment (at-risk customers, due-soon services, ...) and
sync it into the platform as a list/segment so the platform can act on it.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from typing import Any

import structlog

from retention_analytics_core.service_registry import ServiceRegistry
from retention_analytics_advanced.customer_intel import _JsonStore

logger = structlog.get_logger(__name__)

# platform -> (env keys, endpoint template, payload builder key)
PUSH_TARGETS = {
    "klaviyo": {
        "keys": ["KLAVIYO_PRIVATE_API_KEY"],
        "create_list": "https://a.klaviyo.com/api/lists/",
        "add_profiles": "https://a.klaviyo.com/api/bulk-import-jobs/",
    },
    "attentive": {
        "keys": ["ATTENTIVE_API_KEY"],
        "create_segment": "https://api.attentive.com/v2/segments",
    },
    "omnisend": {
        "keys": ["OMNISEND_API_KEY", "OMNISEND_STORE_ID"],
        "create_segment": "https://api.omnisend.com/v3/segments",
    },
    "sendlane": {
        "keys": ["SENDLANE_API_KEY"],
        "create_segment": "https://api.sendlane.com/api/v1/segments",
    },
    "postscript": {
        "keys": ["POSTSCRIPT_API_KEY"],
        "create_segment": "https://api.postscript.io/segments",
    },
}


class SegmentPushService:
    """Push a computed segment into a marketing platform so it can be acted on."""

    def __init__(self, registry: ServiceRegistry) -> None:
        self.registry = registry
        self._pushes = _JsonStore("segment_pushes.json")

    def register(self) -> None:
        reg = self.registry.register("connectors.segment_push", version="1.0.0", metadata={"domain": "integrations", "type": "activation"})
        reg.actions["targets"] = self._targets
        reg.actions["push"] = self._push
        reg.actions["history"] = self._history

    async def _targets(self, p: dict[str, Any]) -> dict[str, Any]:
        rows = []
        for name, spec in PUSH_TARGETS.items():
            missing = [k for k in spec["keys"] if not os.environ.get(k)]
            rows.append({"platform": name, "configured": not missing, "missing_keys": missing})
        return {"status": "ok", "targets": rows}

    async def _push(self, p: dict[str, Any]) -> dict[str, Any]:
        """Push a segment's members into a platform.

        Body: {platform, segment_id or criteria, name, tenant_id}
        """
        platform = p.get("platform", "")
        tenant = p.get("tenant_id", "")
        if platform not in PUSH_TARGETS:
            return {"status": "unknown_platform", "targets": sorted(PUSH_TARGETS)}
        spec = PUSH_TARGETS[platform]
        missing = [k for k in spec["keys"] if not os.environ.get(k)]
        if missing:
            return {"status": "no_credentials", "platform": platform, "missing_keys": missing,
                    "hint": f"set {', '.join(missing)} to enable push-back"}

        # Resolve the segment -> member emails
        members: list[dict[str, Any]] = []
        segment_id = p.get("segment_id", "")
        criteria = p.get("criteria") or {}
        if segment_id or criteria:
            try:
                r = await self.registry.invoke("segmentation.advanced", "preview", {
                    "tenant_id": tenant, "criteria": criteria, "limit": 5000})
                members = r.get("members", [])
            except Exception as exc:
                logger.warning("segment_push.resolve_failed", error=str(exc))
        elif p.get("members"):
            members = p["members"]

        emails = [m.get("email") for m in members if m.get("email")]
        name = p.get("name") or segment_id or f"Snapford segment {datetime.now(UTC):%Y-%m-%d %H:%M}"

        try:
            result = await self._push_to_platform(platform, spec, name, members, emails)
        except Exception as exc:
            logger.warning("segment_push.failed", platform=platform, error=str(exc))
            return {"status": "error", "platform": platform, "error": str(exc)}

        record = {
            "push_id": f"push-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            "platform": platform, "tenant_id": tenant, "name": name,
            "segment_id": segment_id, "members": len(emails),
            "result": result, "pushed_at": datetime.now(UTC).isoformat(),
        }
        self._pushes.upsert("push_id", record)
        return {"status": "ok", "push": record}

    async def _push_to_platform(self, platform: str, spec: dict[str, Any], name: str,
                                members: list[dict[str, Any]], emails: list[str]) -> dict[str, Any]:
        from shared.http_client.resilient_http_client import ResilientHTTPClient

        client = ResilientHTTPClient()
        key = next(os.environ[k] for k in spec["keys"] if os.environ.get(k))

        if platform == "klaviyo":
            headers = {"Authorization": f"Klaviyo-API-Key {key}", "revision": "2024-10-15",
                       "Content-Type": "application/json"}
            list_payload = {"data": {"type": "list", "attributes": {"name": name}}}
            created = await client.post(spec["create_list"], headers=headers, json=list_payload)
            list_id = ""
            if isinstance(created, dict):
                list_id = (created.get("data") or {}).get("id", "")
            # Bulk import profiles into that list
            profiles = [{
                "type": "profile",
                "attributes": {"email": m.get("email"),
                               "properties": {"Name": m.get("name", ""), "Plan": m.get("plan", ""),
                                              "MRR": m.get("mrr", 0),
                                              "Health": m.get("health_score"),
                                              "NextServiceDue": m.get("next_due_date")}},
                "relationships": {"list": {"data": {"type": "list", "id": list_id}}},
            } for m in members if m.get("email")]
            job = await client.post(spec["add_profiles"], headers=headers,
                                    json={"data": {"type": "bulk-import-job",
                                                   "attributes": {"profiles": {"data": profiles}}}})
            return {"list_id": list_id, "profiles_pushed": len(profiles),
                    "job_id": (job.get("data") or {}).get("id", "") if isinstance(job, dict) else ""}

        # generic segment create for the other platforms
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        payload = {"name": name, "emails": emails}
        resp = await client.post(spec["create_segment"], headers=headers, json=payload)
        return {"segment_created": True, "members": len(emails),
                "response": resp if isinstance(resp, dict) else str(resp)[:200]}

    async def _history(self, p: dict[str, Any]) -> dict[str, Any]:
        tenant = p.get("tenant_id", "")
        rows = [r for r in self._pushes.load() if not tenant or r.get("tenant_id") == tenant]
        rows.sort(key=lambda x: x.get("pushed_at", ""), reverse=True)
        return {"status": "ok", "pushes": rows, "count": len(rows)}


__all__ = ["SegmentPushService", "PUSH_TARGETS"]
