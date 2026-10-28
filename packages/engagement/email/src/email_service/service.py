"""
Main Email Service - orchestrates campaigns, templates, sending, and tracking.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    EmailCampaign,
    EmailCampaignCreate,
    EmailCampaignUpdate,
    EmailTemplate,
    EmailTemplateCreate,
    EmailTemplateUpdate,
    EmailMessage,
    SendResult,
    BatchSendResult,
    CampaignStats,
    EmailEvent,
    MessageStatus,
    CampaignStatus,
    CampaignType,
)
from .senders.base import EmailSender
from .senders.ses import SESSender
from .senders.sendgrid import SendGridSender
from .templates.renderer import TemplateRenderer

logger = structlog.get_logger()


class EmailService:
    """Main email service for campaign management and sending."""

    def __init__(
        self,
        db: AsyncSession,
        sender: EmailSender,
        template_renderer: Optional[TemplateRenderer] = None,
        tracking_domain: str = "",
        default_from_email: str = "noreply@example.com",
        default_from_name: str = "Retention Platform",
    ):
        self.db = db
        self.sender = sender
        self.template_renderer = template_renderer or TemplateRenderer()
        self.tracking_domain = tracking_domain
        self.default_from_email = default_from_email
        self.default_from_name = default_from_name

    # ========================================================================
    # Campaign Management
    # ========================================================================

    async def create_campaign(
        self,
        client_id: UUID,
        data: EmailCampaignCreate,
        created_by: UUID,
    ) -> EmailCampaign:
        """Create a new email campaign."""
        campaign = EmailCampaign(
            id=uuid.uuid4(),
            client_id=client_id,
            created_by=created_by,
            **data.model_dump(),
        )
        self.db.add(campaign)
        await self.db.commit()
        await self.db.refresh(campaign)
        return campaign

    async def get_campaign(self, campaign_id: UUID, client_id: UUID) -> Optional[EmailCampaign]:
        """Get a campaign by ID."""
        result = await self.db.execute(
            select(EmailCampaign).where(
                and_(
                    EmailCampaign.id == campaign_id,
                    EmailCampaign.client_id == client_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_campaigns(
        self,
        client_id: UUID,
        status: Optional[CampaignStatus] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[EmailCampaign]:
        """List campaigns for a client."""
        query = select(EmailCampaign).where(EmailCampaign.client_id == client_id)
        if status:
            query = query.where(EmailCampaign.status == status)
        query = query.order_by(EmailCampaign.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_campaign(
        self,
        campaign_id: UUID,
        client_id: UUID,
        data: EmailCampaignUpdate,
    ) -> Optional[EmailCampaign]:
        """Update a campaign."""
        campaign = await self.get_campaign(campaign_id, client_id)
        if not campaign:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(campaign, key, value)

        campaign.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(campaign)
        return campaign

    async def delete_campaign(self, campaign_id: UUID, client_id: UUID) -> bool:
        """Delete a campaign (only if draft)."""
        campaign = await self.get_campaign(campaign_id, client_id)
        if not campaign or campaign.status != CampaignStatus.DRAFT:
            return False

        await self.db.delete(campaign)
        await self.db.commit()
        return True

    # ========================================================================
    # Sending
    # ========================================================================

    async def send_campaign(self, campaign_id: UUID, client_id: UUID) -> BatchSendResult:
        """Send a campaign to all recipients in its segment."""
        campaign = await self.get_campaign(campaign_id, client_id)
        if not campaign:
            raise ValueError("Campaign not found")

        if campaign.status not in (CampaignStatus.DRAFT, CampaignStatus.SCHEDULED):
            raise ValueError(f"Cannot send campaign with status: {campaign.status}")

        # Get recipients from segment
        recipients = await self._get_segment_recipients(campaign.segment_id, client_id)
        if not recipients:
            return BatchSendResult(total=0, successful=0, failed=0, results=[])

        # Update campaign status
        campaign.status = CampaignStatus.SENDING
        campaign.sent_at = datetime.utcnow()
        campaign.recipient_count = len(recipients)
        await self.db.commit()

        # Prepare messages
        messages = await self._prepare_messages(campaign, recipients)

        # Send in batches
        batch_size = 100
        all_results = []

        for i in range(0, len(messages), batch_size):
            batch = messages[i:i + batch_size]
            result = await self.sender.send_batch(batch)
            all_results.extend(result.results)

            # Update message records with provider IDs
            await self._update_message_provider_ids(batch, result.results)

        # Calculate stats
        successful = sum(1 for r in all_results if r.success)
        failed = len(all_results) - successful

        # Update campaign
        campaign.status = CampaignStatus.SENT if failed == 0 else CampaignStatus.FAILED
        campaign.completed_at = datetime.utcnow()
        await self.db.commit()

        return BatchSendResult(
            total=len(all_results),
            successful=successful,
            failed=failed,
            results=all_results,
        )

    async def test_send(
        self,
        campaign_id: UUID,
        client_id: UUID,
        test_emails: List[str],
    ) -> BatchSendResult:
        """Send a test email to specified addresses."""
        campaign = await self.get_campaign(campaign_id, client_id)
        if not campaign:
            raise ValueError("Campaign not found")

        messages = []
        for email in test_emails:
            html, text = self.template_renderer.render_message(
                EmailMessage(
                    id=uuid.uuid4(),
                    campaign_id=campaign.id,
                    client_id=client_id,
                    recipient_email=email,
                    recipient_name="Test User",
                    subject=campaign.subject,
                    html_content=campaign.html_content,
                    text_content=campaign.text_content,
                )
            )
            messages.append({
                "to_email": email,
                "to_name": "Test User",
                "from_email": campaign.from_email,
                "from_name": campaign.from_name,
                "subject": f"[TEST] {campaign.subject}",
                "html_content": html,
                "text_content": text,
                "reply_to": campaign.reply_to,
                "headers": {"X-Test-Send": "true"},
                "metadata": {"campaign_id": str(campaign.id), "test": True},
            })

        return await self.sender.send_batch(messages)

    async def schedule_campaign(
        self,
        campaign_id: UUID,
        client_id: UUID,
        send_at: datetime,
    ) -> Optional[EmailCampaign]:
        """Schedule a campaign for future sending."""
        campaign = await self.get_campaign(campaign_id, client_id)
        if not campaign:
            return None

        if campaign.status != CampaignStatus.DRAFT:
            raise ValueError("Only draft campaigns can be scheduled")

        campaign.status = CampaignStatus.SCHEDULED
        campaign.scheduled_at = send_at
        await self.db.commit()
        await self.db.refresh(campaign)
        return campaign

    async def cancel_scheduled_campaign(
        self,
        campaign_id: UUID,
        client_id: UUID,
    ) -> Optional[EmailCampaign]:
        """Cancel a scheduled campaign."""
        campaign = await self.get_campaign(campaign_id, client_id)
        if not campaign or campaign.status != CampaignStatus.SCHEDULED:
            return None

        campaign.status = CampaignStatus.DRAFT
        campaign.scheduled_at = None
        await self.db.commit()
        await self.db.refresh(campaign)
        return campaign

    # ========================================================================
    # Template Management
    # ========================================================================

    async def create_template(
        self,
        client_id: UUID,
        data: EmailTemplateCreate,
        created_by: UUID,
    ) -> EmailTemplate:
        """Create a new email template."""
        template = EmailTemplate(
            id=uuid.uuid4(),
            client_id=client_id,
            created_by=created_by,
            **data.model_dump(),
        )
        self.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def get_template(self, template_id: UUID, client_id: UUID) -> Optional[EmailTemplate]:
        """Get a template by ID."""
        result = await self.db.execute(
            select(EmailTemplate).where(
                and_(
                    EmailTemplate.id == template_id,
                    EmailTemplate.client_id == client_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_templates(
        self,
        client_id: UUID,
        category: Optional[str] = None,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[EmailTemplate]:
        """List templates for a client."""
        query = select(EmailTemplate).where(EmailTemplate.client_id == client_id)
        if category:
            query = query.where(EmailTemplate.category == category)
        if is_active is not None:
            query = query.where(EmailTemplate.is_active == is_active)
        query = query.order_by(EmailTemplate.updated_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update_template(
        self,
        template_id: UUID,
        client_id: UUID,
        data: EmailTemplateUpdate,
    ) -> Optional[EmailTemplate]:
        """Update a template (creates new version)."""
        template = await self.get_template(template_id, client_id)
        if not template:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(template, key, value)

        template.version += 1
        template.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(template)
        return template

    async def preview_template(
        self,
        template_id: UUID,
        client_id: UUID,
        sample_variables: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Preview a template with sample data."""
        template = await self.get_template(template_id, client_id)
        if not template:
            return None

        return self.template_renderer.preview_template(template, sample_variables)

    # ========================================================================
    # Tracking & Events
    # ========================================================================

    async def track_open(
        self,
        message_id: UUID,
        client_id: UUID,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Track an email open event."""
        message = await self._get_message(message_id, client_id)
        if not message or message.status in (MessageStatus.OPENED, MessageStatus.CLICKED):
            return False

        message.status = MessageStatus.OPENED
        message.opened_at = datetime.utcnow()
        if metadata:
            message.metadata.update(metadata)

        # Emit event for analytics pipeline
        await self._emit_event(EmailEvent(
            event_type="opened",
            client_id=client_id,
            campaign_id=message.campaign_id,
            flow_id=message.flow_id,
            template_id=message.template_id,
            message_id=message.id,
            recipient_email=message.recipient_email,
            recipient_id=message.recipient_id,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
            user_agent=metadata.get("user_agent") if metadata else None,
            ip=metadata.get("ip") if metadata else None,
        ))

        await self.db.commit()
        return True

    async def track_click(
        self,
        message_id: UUID,
        client_id: UUID,
        url: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Track a link click event."""
        message = await self._get_message(message_id, client_id)
        if not message:
            return False

        if message.status != MessageStatus.CLICKED:
            message.status = MessageStatus.CLICKED
            message.clicked_at = datetime.utcnow()
            message.click_url = url

        if metadata:
            message.metadata.update(metadata)

        await self._emit_event(EmailEvent(
            event_type="clicked",
            client_id=client_id,
            campaign_id=message.campaign_id,
            flow_id=message.flow_id,
            template_id=message.template_id,
            message_id=message.id,
            recipient_email=message.recipient_email,
            recipient_id=message.recipient_id,
            timestamp=datetime.utcnow(),
            click_url=url,
            metadata=metadata or {},
            user_agent=metadata.get("user_agent") if metadata else None,
            ip=metadata.get("ip") if metadata else None,
        ))

        await self.db.commit()
        return True

    async def handle_bounce(
        self,
        provider_message_id: str,
        client_id: UUID,
        bounce_data: Dict[str, Any],
    ) -> bool:
        """Handle a bounce notification from provider."""
        # Find message by provider ID
        result = await self.db.execute(
            select(EmailMessage).where(
                and_(
                    EmailMessage.client_id == client_id,
                    EmailMessage.provider_message_id == provider_message_id,
                )
            )
        )
        message = result.scalar_one_or_none()
        if not message:
            logger.warning("Bounce for unknown message", provider_message_id=provider_message_id)
            return False

        message.status = MessageStatus.BOUNCED
        message.bounced_at = datetime.utcnow()
        message.bounce_type = bounce_data.get("bounce_type")
        message.bounce_reason = bounce_data.get("bounce_reason")
        await self.db.commit()

        await self._emit_event(EmailEvent(
            event_type="bounced",
            client_id=client_id,
            campaign_id=message.campaign_id,
            flow_id=message.flow_id,
            template_id=message.template_id,
            message_id=message.id,
            recipient_email=message.recipient_email,
            recipient_id=message.recipient_id,
            timestamp=datetime.utcnow(),
            bounce_type=bounce_data.get("bounce_type"),
            bounce_reason=bounce_data.get("bounce_reason"),
        ))
        return True

    async def handle_complaint(
        self,
        provider_message_id: str,
        client_id: UUID,
        complaint_data: Dict[str, Any],
    ) -> bool:
        """Handle a spam complaint from provider."""
        result = await self.db.execute(
            select(EmailMessage).where(
                and_(
                    EmailMessage.client_id == client_id,
                    EmailMessage.provider_message_id == provider_message_id,
                )
            )
        )
        message = result.scalar_one_or_none()
        if not message:
            return False

        message.status = MessageStatus.COMPLAINED
        message.complained_at = datetime.utcnow()
        await self.db.commit()

        await self._emit_event(EmailEvent(
            event_type="complained",
            client_id=client_id,
            campaign_id=message.campaign_id,
            flow_id=message.flow_id,
            template_id=message.template_id,
            message_id=message.id,
            recipient_email=message.recipient_email,
            recipient_id=message.recipient_id,
            timestamp=datetime.utcnow(),
        ))
        return True

    async def handle_unsubscribe(
        self,
        provider_message_id: str,
        client_id: UUID,
        unsubscribe_data: Dict[str, Any],
    ) -> bool:
        """Handle an unsubscribe event."""
        result = await self.db.execute(
            select(EmailMessage).where(
                and_(
                    EmailMessage.client_id == client_id,
                    EmailMessage.provider_message_id == provider_message_id,
                )
            )
        )
        message = result.scalar_one_or_none()
        if not message:
            return False

        message.status = MessageStatus.UNSUBSCRIBED
        message.unsubscribed_at = datetime.utcnow()
        await self.db.commit()

        # Add to suppression list (would integrate with shared.suppression)
        await self._emit_event(EmailEvent(
            event_type="unsubscribed",
            client_id=client_id,
            campaign_id=message.campaign_id,
            flow_id=message.flow_id,
            template_id=message.template_id,
            message_id=message.id,
            recipient_email=message.recipient_email,
            recipient_id=message.recipient_id,
            timestamp=datetime.utcnow(),
        ))
        return True

    # ========================================================================
    # Analytics
    # ========================================================================

    async def get_campaign_stats(
        self,
        campaign_id: UUID,
        client_id: UUID,
    ) -> Optional[CampaignStats]:
        """Get aggregated statistics for a campaign."""
        campaign = await self.get_campaign(campaign_id, client_id)
        if not campaign:
            return None

        # Aggregate from messages
        result = await self.db.execute(
            select(
                func.count(EmailMessage.id).label("total"),
                func.sum(func.case((EmailMessage.status == MessageStatus.SENT, 1), else_=0)).label("sent"),
                func.sum(func.case((EmailMessage.status == MessageStatus.DELIVERED, 1), else_=0)).label("delivered"),
                func.sum(func.case((EmailMessage.status == MessageStatus.OPENED, 1), else_=0)).label("opened"),
                func.sum(func.case((EmailMessage.status == MessageStatus.CLICKED, 1), else_=0)).label("clicked"),
                func.sum(func.case((EmailMessage.status == MessageStatus.BOUNCED, 1), else_=0)).label("bounced"),
                func.sum(func.case((EmailMessage.status == MessageStatus.COMPLAINED, 1), else_=0)).label("complained"),
                func.sum(func.case((EmailMessage.status == MessageStatus.UNSUBSCRIBED, 1), else_=0)).label("unsubscribed"),
                func.sum(func.case((EmailMessage.status == MessageStatus.FAILED, 1), else_=0)).label("failed"),
                func.sum(EmailMessage.revenue_attributed).label("revenue"),
                func.sum(func.case((EmailMessage.revenue_attributed > 0, 1), else_=0)).label("orders"),
            ).where(
                and_(
                    EmailMessage.campaign_id == campaign_id,
                    EmailMessage.client_id == client_id,
                )
            )
        )
        row = result.first()

        if not row or row.total == 0:
            return CampaignStats(campaign_id=campaign_id)

        sent = row.sent or 0
        delivered = row.delivered or 0
        opened = row.opened or 0
        clicked = row.clicked or 0
        bounced = row.bounced or 0
        complained = row.complained or 0
        unsubscribed = row.unsubscribed or 0
        failed = row.failed or 0
        revenue = row.revenue or Decimal("0")
        orders = row.orders or 0

        return CampaignStats(
            campaign_id=campaign_id,
            sent=sent,
            delivered=delivered,
            opened=opened,
            clicked=clicked,
            bounced=bounced,
            complained=complained,
            unsubscribed=unsubscribed,
            failed=failed,
            delivery_rate=(delivered / sent * 100) if sent > 0 else 0,
            open_rate=(opened / delivered * 100) if delivered > 0 else 0,
            click_rate=(clicked / delivered * 100) if delivered > 0 else 0,
            bounce_rate=(bounced / sent * 100) if sent > 0 else 0,
            complaint_rate=(complained / delivered * 100) if delivered > 0 else 0,
            unsubscribe_rate=(unsubscribed / delivered * 100) if delivered > 0 else 0,
            attributed_revenue=revenue,
            attributed_orders=orders,
            revenue_per_recipient=(revenue / sent) if sent > 0 else Decimal("0"),
            roas=float(revenue) if revenue > 0 else 0,
        )

    # ========================================================================
    # Private Helpers
    # ========================================================================

    async def _get_segment_recipients(
        self,
        segment_id: Optional[UUID],
        client_id: UUID,
    ) -> List[Dict[str, Any]]:
        """Get recipients from a segment. Returns list of {email, name, customer_id}."""
        if not segment_id:
            return []

        # This would integrate with segments service
        # For now, return empty - implement based on segments package
        return []

    async def _prepare_messages(
        self,
        campaign: EmailCampaign,
        recipients: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Prepare message payloads for sending."""
        messages = []

        for recipient in recipients:
            email = recipient["email"]
            name = recipient.get("name")
            customer_id = recipient.get("customer_id")

            # Render template
            html, text = self.template_renderer.render_template(
                EmailTemplate(
                    id=campaign.template_id or uuid.uuid4(),
                    client_id=campaign.client_id,
                    subject=campaign.subject,
                    html_content=campaign.html_content,
                    text_content=campaign.text_content,
                    mjml_content=None,
                    variables=[],
                ),
                {
                    "email": email,
                    "first_name": name.split()[0] if name else "",
                    "last_name": " ".join(name.split()[1:]) if name and len(name.split()) > 1 else "",
                    "unsubscribe_url": f"{self.tracking_domain}/unsubscribe?email={email}&campaign={campaign.id}",
                    "preferences_url": f"{self.tracking_domain}/preferences?email={email}",
                    **(recipient.get("custom_fields", {})),
                },
                base_url=self.tracking_domain,
            )

            # Create message record
            message = EmailMessage(
                id=uuid.uuid4(),
                client_id=campaign.client_id,
                campaign_id=campaign.id,
                template_id=campaign.template_id,
                recipient_email=email,
                recipient_name=name,
                recipient_id=customer_id,
                subject=campaign.subject,
                html_content=html,
                text_content=text,
                headers={"List-Unsubscribe": f"<{self.tracking_domain}/unsubscribe?email={email}>"},
                metadata={
                    "campaign_id": str(campaign.id),
                    "template_variables": recipient.get("custom_fields", {}),
                },
            )
            self.db.add(message)

            messages.append({
                "to_email": email,
                "to_name": name,
                "from_email": campaign.from_email,
                "from_name": campaign.from_name,
                "subject": campaign.subject,
                "html_content": html,
                "text_content": text,
                "reply_to": campaign.reply_to,
                "headers": {"List-Unsubscribe": f"<{self.tracking_domain}/unsubscribe?email={email}>"},
                "metadata": {
                    "campaign_id": str(campaign.id),
                    "message_id": str(message.id),
                    "customer_id": str(customer_id) if customer_id else None,
                },
            })

        await self.db.flush()
        return messages

    async def _update_message_provider_ids(
        self,
        messages: List[Dict[str, Any]],
        results: List[SendResult],
    ):
        """Update message records with provider message IDs."""
        for msg, result in zip(messages, results):
            if result.success and result.provider_message_id:
                message_id = msg["metadata"].get("message_id")
                if message_id:
                    await self.db.execute(
                        select(EmailMessage).where(EmailMessage.id == UUID(message_id))
                    )
                    # Would update the record - simplified for brevity

    async def _get_message(self, message_id: UUID, client_id: UUID) -> Optional[EmailMessage]:
        """Get a message by ID."""
        result = await self.db.execute(
            select(EmailMessage).where(
                and_(
                    EmailMessage.id == message_id,
                    EmailMessage.client_id == client_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def _emit_event(self, event: EmailEvent):
        """Emit event to message bus for analytics pipeline."""
        # This would publish to Redis Streams or similar
        # For now, log it
        logger.info("email_event", event_type=event.event_type, message_id=str(event.message_id))