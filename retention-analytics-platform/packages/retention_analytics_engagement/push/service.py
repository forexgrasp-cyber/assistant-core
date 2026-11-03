"""Push notification engagement service.

Exposes actions: send, track_open, register_device. Invoked by workflows for
mobile re-engagement.

Registered devices and notification receipts are persisted per tenant so
engagement stats survive a restart.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from retention_analytics_core.repository import new_id, repository_for

from retention_analytics_engagement.base import EngagementService

logger = structlog.get_logger(__name__)


class PushService(EngagementService):
    def __init__(self, registry, version: str = "0.1.0") -> None:
        super().__init__("push", registry, version)
        self.register_action("send", self._send)
        self.register_action("track_open", self._track_open)
        self.register_action("register_device", self._register_device)

    def _tenant(self, payload: dict[str, Any]) -> str:
        return str(payload.get("tenant_id") or "default")

    async def _send(self, payload: dict[str, Any]) -> dict[str, Any]:
        device_token = payload.get("device_token")
        title = payload.get("title")
        body = payload.get("body")
        tenant_id = self._tenant(payload)

        if not device_token or not title:
            return self.fail("push requires 'device_token' and 'title'")

        notification_id = new_id("push")
        receipt = {
            "notification_id": notification_id,
            "device_token": device_token,
            "title": title,
            "body": body,
            "channel": "push",
            "tenant_id": tenant_id,
            "status": "sent",
            "opens": 0,
            "queued_at": datetime.now(UTC).isoformat(),
        }
        await repository_for("push_notifications", tenant_id).save(notification_id, receipt)
        logger.info(
            "push.send",
            device_token=device_token,
            title=title,
            notification_id=notification_id,
            tenant_id=tenant_id,
        )
        return {
            "status": "sent",
            "notification_id": notification_id,
            "device_token": device_token,
            "channel": "push",
        }

    async def _track_open(self, payload: dict[str, Any]) -> dict[str, Any]:
        notification_id = payload.get("notification_id")
        tenant_id = self._tenant(payload)
        repo = repository_for("push_notifications", tenant_id)
        receipt = await repo.load(str(notification_id)) if notification_id else None
        if receipt is None:
            return self.fail("unknown notification_id")
        receipt["opens"] = int(receipt.get("opens", 0)) + 1
        receipt["last_opened_at"] = datetime.now(UTC).isoformat()
        await repo.save(str(notification_id), receipt)
        logger.info("push.track_open", notification_id=notification_id, tenant_id=tenant_id)
        return {
            "status": "tracked",
            "notification_id": notification_id,
            "event": "open",
            "opens": receipt["opens"],
        }

    async def _register_device(self, payload: dict[str, Any]) -> dict[str, Any]:
        device_token = payload.get("device_token")
        platform = payload.get("platform")
        tenant_id = self._tenant(payload)
        if not device_token:
            return self.fail("device_token is required")
        device_id = new_id("dev")
        record = {
            "device_id": device_id,
            "device_token": device_token,
            "platform": platform,
            "tenant_id": tenant_id,
            "registered_at": datetime.now(UTC).isoformat(),
        }
        await repository_for("push_devices", tenant_id).save(device_id, record)
        logger.info("push.register_device", device_token=device_token, platform=platform)
        return {
            "status": "registered",
            "device_id": device_id,
            "device_token": device_token,
            "platform": platform,
        }


__all__ = ["PushService"]
