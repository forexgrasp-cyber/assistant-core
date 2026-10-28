"""
Engagement API endpoints: Email, SMS, Push, Flows, Templates, Deliverability.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime
import structlog

from ...core.config import get_settings
from ...core.database import get_db
from ...core.security import get_current_active_user
from ...models import (
    User, EmailTemplate, EmailCampaign, EmailMessage,
    SMSTemplate, SMSCampaign, SMSMessage,
    PushTemplate, PushCampaign, PushMessage,
    FlowDefinition, FlowExecution, FlowNodeExecution,
    DeliverabilityConfig, DeliverabilityEvent, SuppressionList,
)

logger = structlog.get_logger()
router = APIRouter()

settings = get_settings()


# ── Email Templates ──────────────────────────────────────────────────────

@router.post("/email/templates", status_code=201)
async def create_email_template(
    template_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    template = EmailTemplate(
        client_id=current_user.default_client_id,
        name=template_data.get("name"),
        slug=template_data.get("slug") or template_data.get("name", "").lower().replace(" ", "-"),
        subject=template_data.get("subject", ""),
        preview_text=template_data.get("preview_text"),
        html_content=template_data.get("html_content", ""),
        text_content=template_data.get("text_content"),
        mjml_content=template_data.get("mjml_content"),
        variables=template_data.get("variables", []),
        category=template_data.get("category"),
        tags=template_data.get("tags", []),
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return {"id": str(template.id), "message": "Template created"}


@router.get("/email/templates")
async def list_email_templates(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(EmailTemplate).where(
        EmailTemplate.is_active == True
    )
    if current_user.default_client_id:
        query = query.where(EmailTemplate.client_id == current_user.default_client_id)
    if category:
        query = query.where(EmailTemplate.category == category)
    result = await db.execute(query.order_by(desc(EmailTemplate.updated_at)))
    templates = result.scalars().all()
    return [
        {
            "id": str(t.id),
            "name": t.name,
            "slug": t.slug,
            "subject": t.subject,
            "category": t.category,
            "version": t.version,
        }
        for t in templates
    ]


@router.get("/email/templates/{template_id}")
async def get_email_template(
    template_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EmailTemplate).where(EmailTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return {
        "id": str(template.id),
        "name": template.name,
        "slug": template.slug,
        "subject": template.subject,
        "preview_text": template.preview_text,
        "html_content": template.html_content,
        "text_content": template.text_content,
        "mjml_content": template.mjml_content,
        "variables": template.variables,
        "category": template.category,
        "version": template.version,
    }


# ── Email Campaigns ─────────────────────────────────────────────────────

@router.post("/email/campaigns", status_code=201)
async def create_email_campaign(
    campaign_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = EmailCampaign(
        client_id=current_user.default_client_id,
        template_id=campaign_data.get("template_id"),
        segment_id=campaign_data.get("segment_id"),
        name=campaign_data.get("name"),
        type=campaign_data.get("type", "regular"),
        subject=campaign_data.get("subject", ""),
        from_name=campaign_data.get("from_name", ""),
        from_email=campaign_data.get("from_email", ""),
        html_content=campaign_data.get("html_content", ""),
        text_content=campaign_data.get("text_content"),
        scheduled_at=datetime.fromisoformat(campaign_data["scheduled_at"]) if campaign_data.get("scheduled_at") else None,
        settings=campaign_data.get("settings", {}),
        tags=campaign_data.get("tags", []),
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return {"id": str(campaign.id), "message": "Campaign created"}


@router.get("/email/campaigns")
async def list_email_campaigns(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(EmailCampaign).where(EmailCampaign.is_deleted == False)
    if current_user.default_client_id:
        query = query.where(EmailCampaign.client_id == current_user.default_client_id)
    if status:
        query = query.where(EmailCampaign.status == status)
    query = query.order_by(desc(EmailCampaign.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    campaigns = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "subject": c.subject,
            "status": c.status,
            "type": c.type,
            "recipient_count": c.recipient_count,
            "sent_at": c.sent_at.isoformat() if c.sent_at else None,
            "scheduled_at": c.scheduled_at.isoformat() if c.scheduled_at else None,
            "created_at": c.created_at.isoformat(),
        }
        for c in campaigns
    ]


@router.post("/email/campaigns/{campaign_id}/send")
async def send_email_campaign(
    campaign_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EmailCampaign).where(EmailCampaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    if campaign.status not in ("draft", "scheduled"):
        raise HTTPException(status_code=400, detail=f"Cannot send campaign in status: {campaign.status}")
    campaign.status = "sending"
    campaign.sent_at = datetime.utcnow()
    await db.commit()
    # TODO: queue actual send job via Celery
    return {"message": "Campaign queued for sending"}


@router.get("/email/campaigns/{campaign_id}/stats")
async def get_campaign_stats(
    campaign_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(EmailCampaign).where(EmailCampaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    stats = await db.execute(
        select(
            func.count(EmailMessage.id).label("total"),
            func.count(EmailMessage.id).filter(EmailMessage.sent_at.isnot(None)).label("sent"),
            func.count(EmailMessage.id).filter(EmailMessage.delivered_at.isnot(None)).label("delivered"),
            func.count(EmailMessage.id).filter(EmailMessage.opened_at.isnot(None)).label("opened"),
            func.count(EmailMessage.id).filter(EmailMessage.clicked_at.isnot(None)).label("clicked"),
            func.count(EmailMessage.id).filter(EmailMessage.bounced_at.isnot(None)).label("bounced"),
            func.coalesce(func.sum(EmailMessage.revenue_attributed), 0).label("revenue"),
        ).where(EmailMessage.campaign_id == campaign_id)
    )
    s = stats.one()
    delivered = s.delivered or 0
    return {
        "campaign_id": campaign_id,
        "total": s.total or 0,
        "sent": s.sent or 0,
        "delivered": delivered,
        "opened": s.opened or 0,
        "clicked": s.clicked or 0,
        "bounced": s.bounced or 0,
        "open_rate": round((s.opened or 0) / max(delivered, 1) * 100, 2),
        "click_rate": round((s.clicked or 0) / max(delivered, 1) * 100, 2),
        "revenue": float(s.revenue or 0),
    }


# ── SMS Campaigns ────────────────────────────────────────────────────────

@router.post("/sms/campaigns", status_code=201)
async def create_sms_campaign(
    campaign_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = SMSCampaign(
        client_id=current_user.default_client_id,
        template_id=campaign_data.get("template_id"),
        segment_id=campaign_data.get("segment_id"),
        name=campaign_data.get("name"),
        content=campaign_data.get("content", ""),
        from_number=campaign_data.get("from_number", ""),
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return {"id": str(campaign.id), "message": "SMS campaign created"}


@router.post("/sms/campaigns/{campaign_id}/send")
async def send_sms_campaign(
    campaign_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SMSCampaign).where(SMSCampaign.id == campaign_id))
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    campaign.status = "sending"
    campaign.sent_at = datetime.utcnow()
    await db.commit()
    return {"message": "SMS campaign queued"}


# ── Push Campaigns ──────────────────────────────────────────────────────

@router.post("/push/campaigns", status_code=201)
async def create_push_campaign(
    campaign_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    campaign = PushCampaign(
        client_id=current_user.default_client_id,
        template_id=campaign_data.get("template_id"),
        segment_id=campaign_data.get("segment_id"),
        name=campaign_data.get("name"),
        title=campaign_data.get("title", ""),
        body=campaign_data.get("body", ""),
    )
    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return {"id": str(campaign.id), "message": "Push campaign created"}


# ── Flows ────────────────────────────────────────────────────────────────

@router.post("/flows", status_code=201)
async def create_flow(
    flow_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    flow = FlowDefinition(
        client_id=current_user.default_client_id,
        name=flow_data.get("name"),
        slug=flow_data.get("slug") or flow_data.get("name", "").lower().replace(" ", "-"),
        description=flow_data.get("description"),
        trigger_type=flow_data.get("trigger_type", "event"),
        trigger_config=flow_data.get("trigger_config", {}),
        nodes=flow_data.get("nodes", []),
        edges=flow_data.get("edges", []),
        viewport=flow_data.get("viewport"),
        settings=flow_data.get("settings", {}),
    )
    db.add(flow)
    await db.commit()
    await db.refresh(flow)
    return {"id": str(flow.id), "message": "Flow created"}


@router.get("/flows")
async def list_flows(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(FlowDefinition).where(FlowDefinition.is_deleted == False)
    if current_user.default_client_id:
        query = query.where(FlowDefinition.client_id == current_user.default_client_id)
    result = await db.execute(query.order_by(desc(FlowDefinition.updated_at)))
    flows = result.scalars().all()
    return [
        {
            "id": str(f.id),
            "name": f.name,
            "status": f.status,
            "trigger_type": f.trigger_type,
            "total_entries": f.total_entries,
            "total_completions": f.total_completions,
            "updated_at": f.updated_at.isoformat(),
        }
        for f in flows
    ]


@router.post("/flows/{flow_id}/publish")
async def publish_flow(
    flow_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(FlowDefinition).where(FlowDefinition.id == flow_id))
    flow = result.scalar_one_or_none()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    flow.status = "live"
    flow.published_at = datetime.utcnow()
    await db.commit()
    return {"message": "Flow published"}


@router.get("/flows/{flow_id}/analytics")
async def get_flow_analytics(
    flow_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    stats = await db.execute(
        select(
            func.count(FlowExecution.id).label("total"),
            func.count(FlowExecution.id).filter(FlowExecution.status == "completed").label("completed"),
            func.count(FlowExecution.id).filter(FlowExecution.status == "failed").label("failed"),
            func.coalesce(func.sum(FlowExecution.revenue_attributed), 0).label("revenue"),
        ).where(FlowExecution.flow_id == flow_id)
    )
    s = stats.one()
    return {
        "flow_id": flow_id,
        "total_executions": s.total or 0,
        "completed": s.completed or 0,
        "failed": s.failed or 0,
        "completion_rate": round((s.completed or 0) / max(s.total or 1, 1) * 100, 2),
        "revenue": float(s.revenue or 0),
    }


# ── Deliverability ────────────────────────────────────────────────────────

@router.get("/deliverability/stats")
async def get_deliverability_stats(
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from datetime import timedelta
    stats = await db.execute(
        select(
            func.count(DeliverabilityEvent.id).label("total"),
            func.count(DeliverabilityEvent.id).filter(DeliverabilityEvent.event_type == "delivered").label("delivered"),
            func.count(DeliverabilityEvent.id).filter(DeliverabilityEvent.event_type == "bounced").label("bounced"),
            func.count(DeliverabilityEvent.id).filter(DeliverabilityEvent.event_type == "complained").label("complained"),
        ).where(
            DeliverabilityEvent.timestamp >= datetime.utcnow() - timedelta(days=days)
        )
    )
    s = stats.one()
    total = s.total or 0
    return {
        "total_events": total,
        "delivered": s.delivered or 0,
        "bounced": s.bounced or 0,
        "complained": s.complained or 0,
        "bounce_rate": round((s.bounced or 0) / max(total, 1) * 100, 2),
        "complaint_rate": round((s.complained or 0) / max(total, 1) * 100, 2),
    }


@router.get("/suppression-list")
async def get_suppression_list(
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(SuppressionList)
        .where(SuppressionList.is_active == True)
        .order_by(desc(SuppressionList.created_at))
        .limit(limit)
    )
    entries = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "email": e.email,
            "reason": e.reason,
            "bounce_type": e.bounce_type,
            "created_at": e.created_at.isoformat(),
        }
        for e in entries
    ]