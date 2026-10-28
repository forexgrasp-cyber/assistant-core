"""
AWS SES email sender implementation.
"""

from __future__ import annotations

import boto3
from botocore.exceptions import ClientError
from typing import Any, Dict, List, Optional

from .base import EmailSender, SendResult, BatchSendResult


class SESSender(EmailSender):
    """AWS Simple Email Service sender."""

    provider_name = "ses"

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.region = config.get("region", "us-east-1")
        self.access_key = config.get("access_key")
        self.secret_key = config.get("secret_key")
        self.configuration_set = config.get("configuration_set")

        session = boto3.Session(
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region,
        )
        self.client = session.client("sesv2")

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
        """Send a single email via SES."""
        try:
            destination = {
                "ToAddresses": [self._format_address(to_email, to_name)],
            }

            if reply_to:
                destination["ReplyToAddresses"] = [reply_to]

            content = {
                "Simple": {
                    "Subject": {"Data": subject, "Charset": "UTF-8"},
                    "Body": {
                        "Html": {"Data": html_content, "Charset": "UTF-8"},
                    },
                }
            }

            if text_content:
                content["Simple"]["Body"]["Text"] = {"Data": text_content, "Charset": "UTF-8"}

            email_tags = []
            if metadata:
                for key, value in metadata.items():
                    if isinstance(value, str):
                        email_tags.append({"Name": key, "Value": value})

            params = {
                "FromEmailAddress": self._format_address(from_email, from_name),
                "Destination": destination,
                "Content": content,
            }

            if self.configuration_set:
                params["ConfigurationSetName"] = self.configuration_set

            if email_tags:
                params["EmailTags"] = email_tags

            if headers:
                params["Headers"] = [
                    {"Name": k, "Value": v} for k, v in headers.items()
                ]

            response = self.client.send_email(**params)

            return SendResult(
                success=True,
                provider_message_id=response.get("MessageId"),
                recipient=to_email,
                metadata={"provider": "ses", "request_id": response.get("ResponseMetadata", {}).get("RequestId")},
            )

        except ClientError as e:
            error_code = e.response["Error"]["Code"]
            error_message = e.response["Error"]["Message"]
            return SendResult(
                success=False,
                error=f"SES Error ({error_code}): {error_message}",
                recipient=to_email,
            )
        except Exception as e:
            return SendResult(
                success=False,
                error=f"Unexpected error: {str(e)}",
                recipient=to_email,
            )

    async def send_batch(
        self,
        messages: List[Dict[str, Any]],
    ) -> BatchSendResult:
        """Send multiple emails via SES (uses bulk API if available)."""
        results = []
        successful = 0
        failed = 0

        for msg in messages:
            result = await self.send(**msg)
            results.append(result)
            if result.success:
                successful += 1
            else:
                failed += 1

        return BatchSendResult(
            total=len(messages),
            successful=successful,
            failed=failed,
            results=results,
        )

    async def verify_domain(self, domain: str) -> bool:
        """Check if domain is verified in SES."""
        try:
            response = self.client.get_domain_verification_attributes(
                DomainNames=[domain]
            )
            attrs = response.get("DomainVerificationAttributes", {})
            return attrs.get(domain, {}).get("VerificationStatus") == "Success"
        except ClientError:
            return False

    async def get_sending_stats(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get sending statistics from SES."""
        try:
            # SES doesn't have a direct stats API for date ranges
            # Would need to use CloudWatch metrics or event publishing
            return {
                "provider": "ses",
                "note": "Use CloudWatch for detailed metrics",
            }
        except Exception as e:
            return {"error": str(e)}

    async def handle_webhook(self, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Process SES webhook (SNS notification)."""
        events = []

        # SES sends via SNS, so payload is wrapped
        if "Message" in payload:
            import json
            try:
                message = json.loads(payload["Message"])
                payload = message
            except json.JSONDecodeError:
                pass

        event_type = payload.get("eventType")

        if event_type == "Bounce":
            bounce = payload.get("bounce", {})
            for recipient in bounce.get("bouncedRecipients", []):
                events.append({
                    "event_type": "bounced",
                    "provider_message_id": payload.get("mail", {}).get("messageId"),
                    "recipient_email": recipient.get("emailAddress"),
                    "bounce_type": bounce.get("bounceType", "").lower(),
                    "bounce_sub_type": bounce.get("bounceSubType"),
                    "timestamp": payload.get("mail", {}).get("timestamp"),
                    "metadata": {"diagnosticCode": recipient.get("diagnosticCode")},
                })

        elif event_type == "Complaint":
            complaint = payload.get("complaint", {})
            for recipient in complaint.get("complainedRecipients", []):
                events.append({
                    "event_type": "complained",
                    "provider_message_id": payload.get("mail", {}).get("messageId"),
                    "recipient_email": recipient.get("emailAddress"),
                    "timestamp": payload.get("mail", {}).get("timestamp"),
                    "metadata": {"feedbackId": complaint.get("feedbackId")},
                })

        elif event_type == "Delivery":
            delivery = payload.get("delivery", {})
            events.append({
                "event_type": "delivered",
                "provider_message_id": payload.get("mail", {}).get("messageId"),
                "recipient_email": delivery.get("recipients", [None])[0],
                "timestamp": delivery.get("timestamp"),
                "metadata": {"smtpResponse": delivery.get("smtpResponse")},
            })

        elif event_type in ("Open", "Click"):
            # These require configuration set with event publishing
            mail = payload.get("mail", {})
            events.append({
                "event_type": event_type.lower(),
                "provider_message_id": mail.get("messageId"),
                "recipient_email": mail.get("destination", [None])[0],
                "timestamp": payload.get(event_type.lower(), {}).get("timestamp"),
                "metadata": payload.get(event_type.lower(), {}),
            })

        return events

    def _format_address(self, email: str, name: Optional[str]) -> str:
        if name:
            return f"{name} <{email}>"
        return email