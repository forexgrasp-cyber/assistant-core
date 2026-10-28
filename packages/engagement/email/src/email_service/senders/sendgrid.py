"""
SendGrid email sender implementation.
"""

from __future__ import annotations

import sendgrid
from sendgrid.helpers.mail import (
    Mail,
    Email,
    To,
    Content,
    Attachment,
    FileContent,
    FileName,
    FileType,
    Disposition,
    Header,
)
from typing import Any, Dict, List, Optional
import base64

from .base import EmailSender, SendResult, BatchSendResult


class SendGridSender(EmailSender):
    """SendGrid email sender."""

    provider_name = "sendgrid"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = config.get("api_key")
        self.client = sendgrid.SendGridAPIClient(api_key=self.api_key)

    async def send(
        self,
        to_email: str,
        to_name: Optional[str],
        from_email: str,
        from_name: str,
        subject: str,
        html_content: str,
        text_content: Optional[str],
        reply_to: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SendResult:
        """Send a single email via SendGrid."""
        try:
            from_email_obj = Email(from_email, from_name)
            to_email_obj = To(to_email, to_name or "")

            mail = Mail(
                from_email=from_email_obj,
                to_emails=to_email_obj,
                subject=subject,
                html_content=Content("text/html", html_content),
            )

            if text_content:
                mail.add_content(Content("text/plain", text_content))

            if reply_to:
                mail.reply_to = Email(reply_to)

            # Custom headers
            if headers:
                for key, value in headers.items():
                    mail.add_header(Header(key, value))

            # Categories for tracking
            if metadata:
                for key, value in metadata.items():
                    if isinstance(value, str):
                        mail.add_category(key, value)

            response = self.client.send(mail)

            return SendResult(
                success=200 <= response.status_code < 300,
                provider_message_id=response.headers.get("X-Message-Id"),
                recipient=to_email,
                metadata={"provider": "sendgrid", "status_code": response.status_code},
            )

        except Exception as e:
            return SendResult(
                success=False,
                error=f"SendGrid error: {str(e)}",
                recipient=to_email,
            )

    async def send_batch(
        self,
        messages: List[Dict[str, Any]],
    ) -> BatchSendResult:
        """Send multiple emails via SendGrid (uses personalization)."""
        if not messages:
            return BatchSendResult(total=0, successful=0, failed=0, results=[])

        # Use first message as base
        base = messages[0]
        mail = Mail(
            from_email=Email(base["from_email"], base.get("from_name", "")),
            subject=base["subject"],
            html_content=Content("text/html", base["html_content"]),
        )

        if base.get("text_content"):
            mail.add_content(Content("text/plain", base["text_content"]))

        if base.get("reply_to"):
            mail.reply_to = Email(base["reply_to"])

        # Add all recipients as personalizations
        for msg in messages:
            to_email = msg["to_email"]
            to_name = msg.get("to_name")
            personalization = mail.personalizations[0] if mail.personalizations else None
            
            if personalization is None or len(mail.personalizations) >= 1000:
                # Create new personalization
                from sendgrid.helpers.mail import Personalization
                personalization = Personalization()
                mail.add_personalization(personalization)

            personalization.add_to(To(to_email, to_name or ""))
            
            if msg.get("metadata"):
                for key, value in msg["metadata"].items():
                    if isinstance(value, str):
                        personalization.add_custom_arg(key, value)

        try:
            response = self.client.send(mail)
            
            results = []
            for msg in messages:
                results.append(SendResult(
                    success=200 <= response.status_code < 300,
                    provider_message_id=response.headers.get("X-Message-Id"),
                    recipient=msg["to_email"],
                    metadata={"provider": "sendgrid", "status_code": response.status_code},
                ))

            successful = sum(1 for r in results if r.success)
            return BatchSendResult(
                total=len(messages),
                successful=successful,
                failed=len(messages) - successful,
                results=results,
            )

        except Exception as e:
            results = [SendResult(
                success=False,
                error=f"SendGrid batch error: {str(e)}",
                recipient=msg["to_email"],
            ) for msg in messages]
            return BatchSendResult(
                total=len(messages),
                successful=0,
                failed=len(messages),
                results=results,
            )

    async def verify_domain(self, domain: str) -> bool:
        """Check if domain is authenticated in SendGrid."""
        try:
            response = self.client.client.whitelabel.domains.get()
            domains = response.body if hasattr(response, 'body') else []
            return any(d.get("domain") == domain and d.get("valid") for d in domains)
        except Exception:
            return False

    async def get_sending_stats(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get sending statistics from SendGrid."""
        try:
            response = self.client.client.stats.get(
                query_params={
                    "start_date": start_date,
                    "end_date": end_date,
                    "aggregated_by": "day",
                }
            )
            return {"provider": "sendgrid", "stats": response.body}
        except Exception as e:
            return {"error": str(e)}

    async def handle_webhook(self, payload: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process SendGrid webhook events."""
        events = []

        for event in payload:
            event_type = event.get("event")
            sg_message_id = event.get("sg_message_id")
            email = event.get("email")

            if event_type == "bounce":
                events.append({
                    "event_type": "bounced",
                    "provider_message_id": sg_message_id,
                    "recipient_email": email,
                    "bounce_type": event.get("type", "").lower(),
                    "bounce_reason": event.get("reason"),
                    "timestamp": event.get("timestamp"),
                    "metadata": {"smtp_id": event.get("smtp-id")},
                })

            elif event_type == "spam_report":
                events.append({
                    "event_type": "complained",
                    "provider_message_id": sg_message_id,
                    "recipient_email": email,
                    "timestamp": event.get("timestamp"),
                    "metadata": {},
                })

            elif event_type == "delivered":
                events.append({
                    "event_type": "delivered",
                    "provider_message_id": sg_message_id,
                    "recipient_email": email,
                    "timestamp": event.get("timestamp"),
                    "metadata": {"response": event.get("response")},
                })

            elif event_type == "open":
                events.append({
                    "event_type": "opened",
                    "provider_message_id": sg_message_id,
                    "recipient_email": email,
                    "timestamp": event.get("timestamp"),
                    "metadata": {"useragent": event.get("useragent"), "ip": event.get("ip")},
                })

            elif event_type == "click":
                events.append({
                    "event_type": "clicked",
                    "provider_message_id": sg_message_id,
                    "recipient_email": email,
                    "click_url": event.get("url"),
                    "timestamp": event.get("timestamp"),
                    "metadata": {"useragent": event.get("useragent"), "ip": event.get("ip")},
                })

            elif event_type == "unsubscribe":
                events.append({
                    "event_type": "unsubscribed",
                    "provider_message_id": sg_message_id,
                    "recipient_email": email,
                    "timestamp": event.get("timestamp"),
                    "metadata": {},
                })

        return events