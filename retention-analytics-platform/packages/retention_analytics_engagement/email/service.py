"""Email engagement service.

Exposes actions: send, track_open, track_click, suppress. These are invoked by
workflows (e.g. a churn-prevention flow sends an email, then tracks engagement).

Delivery is persist-then-flush: the message is written to the canonical email
outbox (``shared.email_outbox.EmailOutbox``) and the send receipt plus the
engagement events are persisted per tenant, so a message survives a restart
and the engagement counters are computed from real records.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from retention_analytics_core.repository import data_root, new_id, repository_for

from retention_analytics_engagement.base import EngagementService

logger = structlog.get_logger(__name__)


class EmailService(EngagementService):
    def __init__(self, registry, version: str = "0.1.0") -> None:
        super().__init__("email", registry, version)
        self.register_action("send", self._send)
        self.register_action("track_open", self._track_open)
        self.register_action("track_click", self._track_click)
        self.register_action("suppress", self._suppress)
        self._outbox: Any = None

    def _get_outbox(self) -> Any:
        if self._outbox is None:
            from shared.email_outbox import EmailOutbox

            self._outbox = EmailOutbox(str(data_root() / "email_outbox.db"))
        return self._outbox

    def _tenant(self, payload: dict[str, Any]) -> str:
        return str(payload.get("tenant_id") or "default")

    async def _send(self, payload: dict[str, Any]) -> dict[str, Any]:
        to = payload.get("to")
        subject = payload.get("subject")
        body = payload.get("body")
        html = payload.get("html")
        tenant_id = self._tenant(payload)

        if not to or not subject:
            return self.fail("email requires 'to' and 'subject'")

        if await self._is_suppressed(str(to), tenant_id):
            return {
                "status": "suppressed",
                "message_id": None,
                "to": to,
                "channel": "email",
                "reason": "recipient_suppressed",
            }

        message_id = new_id("msg")
        outbox_item_id = self._get_outbox().enqueue(
            to_addr=str(to),
            subject=str(subject),
            body_text=str(body or ""),
            body_html=html,
        )

        receipt = {
            "status": "queued",
            "message_id": message_id,
            "outbox_item_id": outbox_item_id,
            "to": to,
            "subject": subject,
            "channel": "email",
            "tenant_id": tenant_id,
            "queued_at": datetime.now(UTC).isoformat(),
            "opens": 0,
            "clicks": 0,
        }
        await repository_for("email_messages", tenant_id).save(message_id, receipt)
        logger.info(
            "email.send",
            to=to,
            subject=subject,
            message_id=message_id,
            tenant_id=tenant_id,
        )
        return {
            "status": "queued",
            "message_id": message_id,
            "outbox_item_id": outbox_item_id,
            "to": to,
            "channel": "email",
        }

    async def _track_open(self, payload: dict[str, Any]) -> dict[str, Any]:
        message_id = payload.get("message_id")
        tenant_id = self._tenant(payload)
        repo = repository_for("email_messages", tenant_id)
        receipt = await repo.load(str(message_id)) if message_id else None
        if receipt is None:
            return self.fail("unknown message_id")
        receipt["opens"] = int(receipt.get("opens", 0)) + 1
        receipt["last_opened_at"] = datetime.now(UTC).isoformat()
        await repo.save(str(message_id), receipt)
        logger.info("email.track_open", message_id=message_id, tenant_id=tenant_id)
        return {
            "status": "tracked",
            "message_id": message_id,
            "event": "open",
            "opens": receipt["opens"],
        }

    async def _track_click(self, payload: dict[str, Any]) -> dict[str, Any]:
        message_id = payload.get("message_id")
        url = payload.get("url")
        tenant_id = self._tenant(payload)
        repo = repository_for("email_messages", tenant_id)
        receipt = await repo.load(str(message_id)) if message_id else None
        if receipt is None:
            return self.fail("unknown message_id")
        receipt["clicks"] = int(receipt.get("clicks", 0)) + 1
        receipt.setdefault("click_urls", []).append(url)
        receipt["last_clicked_at"] = datetime.now(UTC).isoformat()
        await repo.save(str(message_id), receipt)
        logger.info("email.track_click", message_id=message_id, url=url, tenant_id=tenant_id)
        return {
            "status": "tracked",
            "message_id": message_id,
            "event": "click",
            "url": url,
            "clicks": receipt["clicks"],
        }

    async def _suppress(self, payload: dict[str, Any]) -> dict[str, Any]:
        email = payload.get("email")
        reason = payload.get("reason", "unsubscribed")
        tenant_id = self._tenant(payload)
        if not email:
            return self.fail("email is required")
        suppression_id = new_id("sup")
        record = {
            "suppression_id": suppression_id,
            "email": email,
            "reason": reason,
            "tenant_id": tenant_id,
            "suppressed_at": datetime.now(UTC).isoformat(),
        }
        await repository_for("email_suppressions", tenant_id).save(suppression_id, record)
        logger.info("email.suppress", email=email, reason=reason, tenant_id=tenant_id)
        return {"status": "suppressed", "email": email, "reason": reason}

    async def _is_suppressed(self, email: str, tenant_id: str) -> bool:
        repo = repository_for("email_suppressions", tenant_id)
        for _suppression_id, record in await repo.list_all():
            if str(record.get("email", "")).lower() == str(email).lower():
                return True
        return False


__all__ = ["EmailService"]
