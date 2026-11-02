"""
Notifications — thin adapter over the canonical communications stack.

Channel send/retry/circuit-breaker logic is canonical
(``shared.communications``); platform only builds marketplace-shaped
messages and persists delivery records (Notification ORM).

    EmailChannel/EmailConfig       SMTP send (canonical)
    TelegramChannel/...            other channels as configured
    NotificationRepository         in-app inbox records

Env (canonical): SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASSWORD or
EmailConfig fields POSTED via marketplace config.
"""

from __future__ import annotations

from typing import Any

import structlog

from shared.communications import (
    ChannelType,
    EmailChannel,
    EmailConfig,
    MessageType,
    OutgoingMessage,
)

from marketplace.database.repositories import NotificationRepository
from marketplace.models import Notification

__all__ = [
    "NotificationService",
    "TEMPLATES",
]

log = structlog.get_logger(__name__)

from marketplace.config import settings as _settings

TEMPLATES: dict[str, str] = {
    "match_proposed": "You have a new VA match proposal — review it on your dashboard.",
    "match_accepted": "A match was accepted. Technical interview preparation starts next.",
    "placement_fee_due": "Placement fee invoice is ready. Payment unlocks onboarding.",
    "onboarding_progress": "The tailored onboarding plan has a new completed stage.",
    "monthly_fee_due": "Monthly platform fee for this month is billed now.",
    "delivery_delivered": "A deliverable has been marked as delivered for review.",
    "delivery_revision": "The deliverable you requested needs revision. See details.",
}


def _default_email_channel() -> EmailChannel:
    """Canonical EmailChannel configured from platform settings."""
    config = EmailConfig(
        channel_type=ChannelType.EMAIL,
        name="va-matching-email",
        smtp_host=_settings.SMTP_HOST or "localhost",
        smtp_port=_settings.SMTP_PORT,
        smtp_username=_settings.SMTP_USER or "",
        smtp_password=_settings.SMTP_PASSWORD or "",
        from_email=_settings.EMAIL_FROM,
        from_name=_settings.EMAIL_FROM_NAME,
    )
    return EmailChannel(config)


class NotificationService:
    """In-app notifications always; email delivery via the canonical channel."""

    def __init__(
        self,
        email: EmailChannel | None = None,
        notification_repo: NotificationRepository | None = None,
    ):
        self.email: EmailChannel = email or _default_email_channel()
        self._repo = notification_repo  # lazy-bound with a session per call

    # ── in-app ──────────────────────────────────────────────────────────

    async def deliver_user_notification(
        self,
        session: Any,
        *,
        user_id: str,
        kind: str,
        payload: dict[str, Any] | None = None,
        title: str | None = None,
        body: str | None = None,
    ) -> Notification | None:
        """Persist an in-app notification row for a user."""
        notification = Notification(
            user_id=user_id,
            type=kind,
            title=title or kind.replace("_", " ").title(),
            message=body or TEMPLATES.get(kind, kind),
            data=payload or {},
        )
        session.add(notification)
        await session.flush()
        return notification

    # ── email (canonical channel) ──────────────────────────────────────

    async def send_email(
        self,
        *,
        user_email: str,
        kind: str,
        payload: dict[str, Any] | None = None,
        subject_override: str | None = None,
    ) -> dict[str, Any]:
        """Send an email through the canonical EmailChannel (reliable send)."""
        body = TEMPLATES.get(kind, "Direct notification")
        if payload:
            body += "\n\nDetails: " + ", ".join(
                f"{k}={v}" for k, v in payload.items()
            )
        message = OutgoingMessage(
            content=body,
            message_type=MessageType.TEXT,
            customer_contact=user_email,
            metadata={
                "kind": kind,
                "subject": subject_override
                or f"VA Matching — {kind.replace('_', ' ').title()}",
            },
        )
        result = await self.email.send_reliable(message)
        return {"kind": kind, "result": result}

    # ── combined ────────────────────────────────────────────────────────

    async def notify_user(
        self,
        session: Any,
        *,
        user_id: str,
        email: str | None,
        kind: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """In-app notification always; email as best effort."""
        await self.deliver_user_notification(
            session, user_id=user_id, kind=kind, payload=payload
        )
        email_result: dict[str, Any] = {}
        if email:
            try:
                email_result = await self.send_email(
                    user_email=email, kind=kind, payload=payload
                )
            except Exception as exc:  # noqa: BLE001 — email failures must not break events
                log.warning("notify_email_failed", kind=kind, error=str(exc))
        return {"kind": kind, "email": email_result}
