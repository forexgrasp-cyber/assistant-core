"""SMS engagement service.

Exposes actions: send, track_delivery, opt_out. Wired into workflows the same
way as email so a single retention flow can use email + SMS together.

Every send and delivery receipt is persisted per tenant so delivery stats are
computed from real records instead of in-memory state.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from retention_analytics_core.repository import new_id, repository_for

from retention_analytics_engagement.base import EngagementService

logger = structlog.get_logger(__name__)


class SmsService(EngagementService):
    def __init__(self, registry, version: str = "0.1.0") -> None:
        super().__init__("sms", registry, version)
        self.register_action("send", self._send)
        self.register_action("track_delivery", self._track_delivery)
        self.register_action("opt_out", self._opt_out)

    def _tenant(self, payload: dict[str, Any]) -> str:
        return str(payload.get("tenant_id") or "default")

    async def _send(self, payload: dict[str, Any]) -> dict[str, Any]:
        to = payload.get("to")
        body = payload.get("body")
        tenant_id = self._tenant(payload)

        if not to or not body:
            return self.fail("sms requires 'to' and 'body'")

        message_id = new_id("sms")
        receipt = {
            "message_id": message_id,
            "to": to,
            "body": body,
            "channel": "sms",
            "tenant_id": tenant_id,
            "status": "sent",
            "delivered": False,
            "queued_at": datetime.now(UTC).isoformat(),
        }
        await repository_for("sms_messages", tenant_id).save(message_id, receipt)
        logger.info("sms.send", to=to, message_id=message_id, tenant_id=tenant_id)
        return {
            "status": "sent",
            "message_id": message_id,
            "to": to,
            "channel": "sms",
        }

    async def _track_delivery(self, payload: dict[str, Any]) -> dict[str, Any]:
        message_id = payload.get("message_id")
        tenant_id = self._tenant(payload)
        repo = repository_for("sms_messages", tenant_id)
        receipt = await repo.load(str(message_id)) if message_id else None
        if receipt is None:
            return self.fail("unknown message_id")
        receipt["delivered"] = True
        receipt["status"] = "delivered"
        receipt["delivered_at"] = datetime.now(UTC).isoformat()
        await repo.save(str(message_id), receipt)
        logger.info("sms.track_delivery", message_id=message_id, tenant_id=tenant_id)
        return {"status": "delivered", "message_id": message_id}

    async def _opt_out(self, payload: dict[str, Any]) -> dict[str, Any]:
        phone = payload.get("phone")
        tenant_id = self._tenant(payload)
        if not phone:
            return self.fail("phone is required")
        suppression_id = new_id("sup")
        record = {
            "suppression_id": suppression_id,
            "phone": phone,
            "reason": payload.get("reason", "opted_out"),
            "tenant_id": tenant_id,
            "suppressed_at": datetime.now(UTC).isoformat(),
        }
        await repository_for("sms_suppressions", tenant_id).save(suppression_id, record)
        logger.info("sms.opt_out", phone=phone, tenant_id=tenant_id)
        return {"status": "opted_out", "phone": phone}


__all__ = ["SmsService"]
