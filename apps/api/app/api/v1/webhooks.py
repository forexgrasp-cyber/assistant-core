"""
Webhook API endpoints: Ingress, Egress, DLQ, Signatures, Retries.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from datetime import datetime
import uuid
import structlog

from ...core.config import get_settings
from ...core.database import get_db
from ...core.security import get_current_active_user
from ...models import (
    WebhookEndpoint, WebhookEvent, WebhookDelivery, WebhookSignature,
    WebhookRetry, DeadLetterQueue
)

logger = structlog.get_logger()
router = APIRouter()

settings = get_settings()

@router.post("/endpoints", status_code=201)
async def create_webhook_endpoint(
    endpoint_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WebhookEndpoint
    
    endpoint = WebhookEndpoint(
        client_id=current_user.client_id,
        name=endpoint_data.get("name"),
        description=endpoint_data.get("description"),
        path=endpoint_data.get("path"),
        method=endpoint_data.get("method", "POST"),
        auth_type=endpoint_data.get("auth_type", "signature"),
        secret_encrypted=endpoint_data.get("secret"),
        required_headers=endpoint_data.get("required_headers", []),
        processor=endpoint_data.get("processor"),
        processor_config=endpoint_data.get("processor_config", {}),
        deduplication_enabled=endpoint_data.get("deduplication_enabled", True),
        deduplication_window_seconds=endpoint_data.get("deduplication_window_seconds", 300),
        response_template=endpoint_data.get("response_template"),
        response_status=endpoint_data.get("response_status", 200),
        retry_enabled=endpoint_data.get("retry_enabled", True),
        max_retries=endpoint_data.get("max_retries", 3),
        retry_backoff_seconds=endpoint_data.get("retry_backoff_seconds", 60),
        dlq_enabled=endpoint_data.get("dlq_enabled", True),
        alert_on_failure=endpoint_data.get("alert_on_failure", True),
        alert_threshold=endpoint_data.get("alert_threshold", 5),
        alert_window_minutes=endpoint_data.get("alert_window_minutes", 5),
        is_active=endpoint_data.get("is_active", True),
        is_paused=endpoint_data.get("is_paused", False),
    )
    db.add(endpoint)
    await db.commit()
    await db.refresh(endpoint)
    return {"id": str(endpoint.id), "message": "Webhook endpoint created"}

@router.get("/endpoints")
async def list_webhook_endpoints(
    processor: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WebhookEndpoint
    from sqlalchemy import desc
    
    query = select(WebhookEndpoint).where(WebhookEndpoint.client_id == current_user.client_id)
    
    if processor:
        query = query.where(WebhookEndpoint.processor == processor)
    if is_active is not None:
        query = query.where(WebhookEndpoint.is_active == is_active)
    
    result = await db.execute(query.order_by(desc(WebhookEndpoint.created_at)))
    endpoints = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "name": e.name,
            "path": e.path,
            "method": e.method,
            "processor": e.processor,
            "is_active": e.is_active,
            "total_requests": e.total_requests,
            "successful_requests": e.successful_requests,
            "failed_requests": e.failed_requests,
        }
        for e in endpoints
    ]

@router.get("/endpoints/{endpoint_id}")
async def get_webhook_endpoint(
    endpoint_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WebhookEndpoint
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.client_id == current_user.client_id
        )
    )
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    return {
        "id": str(endpoint.id),
        "name": endpoint.name,
        "path": endpoint.path,
        "method": endpoint.method,
        "auth_type": endpoint.auth_type,
        "processor": endpoint.processor,
        "is_active": endpoint.is_active,
        "total_requests": endpoint.total_requests,
        "successful_requests": endpoint.successful_requests,
        "failed_requests": endpoint.failed_requests,
        "dlq_count": endpoint.dlq_count,
    }

@router.patch("/endpoints/{endpoint_id}")
async def update_webhook_endpoint(
    endpoint_id: str,
    endpoint_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WebhookEndpoint
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.client_id == current_user.client_id
        )
    )
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    
    for field, value in endpoint_data.items():
        if hasattr(endpoint, field):
            setattr(endpoint, field, value)
    
    await db.commit()
    await db.refresh(endpoint)
    return {"message": "Webhook endpoint updated"}

@router.delete("/endpoints/{endpoint_id}", status_code=204)
async def delete_webhook_endpoint(
    endpoint_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WebhookEndpoint
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.client_id == current_user.client_id
        )
    )
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    await db.delete(endpoint)
    await db.commit()
    return Response(status_code=204)

@router.post("/events", status_code=202)
async def receive_webhook_event(
    endpoint_id: str,
    request: Request,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WebhookEvent, WebhookEndpoint
    import json
    
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == endpoint_id,
            WebhookEndpoint.client_id == current_user.client_id
        )
    )
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    
    body = await request.body()
    headers = dict(request.headers)
    query_params = dict(request.query_params)
    
    # Deduplication
    dedup_key = None
    if endpoint.deduplication_enabled:
        dedup_key = headers.get(endpoint.deduplication_key_header) or \
            json.loads(body).get(endpoint.deduplication_key_json_path)
    
    if endpoint.deduplication_enabled and dedup_key:
        existing = await db.execute(
            select(WebhookEvent).where(
                WebhookEvent.endpoint_id == endpoint_id,
                WebhookEvent.deduplication_key == dedup_key
            )
        )
        if existing.scalar_one_or_none():
            return {"status": "duplicate", "message": "Event already processed"}
    
    event = WebhookEvent(
        endpoint_id=endpoint.id,
        request_id=headers.get("x-request-id") or str(uuid.uuid4()),
        request_method=request.method,
        request_path=str(request.url.path),
        request_headers=headers,
        request_body=json.loads(body) if body else {},
        request_query=query_params,
        client_ip=request.client.host if request.client else None,
        deduplication_key=dedup_key,
    )
    db.add(event)
    await db.commit()
    
    return {"status": "accepted", "event_id": str(event.id)}

@router.get("/events")
async def list_webhook_events(
    endpoint_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WebhookEvent
    from sqlalchemy import desc
    
    query = select(WebhookEvent).where(WebhookEvent.client_id == current_user.client_id)
    
    if endpoint_id:
        query = query.where(WebhookEvent.endpoint_id == endpoint_id)
    if status:
        query = query.where(WebhookEvent.status == status)
    
    query = query.order_by(desc(WebhookEvent.received_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    events = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "endpoint_id": str(e.endpoint_id),
            "event_type": e.event_type,
            "status": e.status,
            "received_at": e.received_at.isoformat(),
            "processed_at": e.processed_at.isoformat() if e.processed_at else None,
        }
        for e in events
    ]

@router.post("/deliveries", status_code=202)
async def send_webhook_delivery(
    delivery_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WebhookDelivery, WebhookEndpoint
    
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == delivery_data.get("endpoint_id"),
            WebhookEndpoint.client_id == current_user.client_id
        )
    )
    endpoint = result.scalar_one_or_none()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    
    delivery = WebhookDelivery(
        endpoint_id=endpoint.id,
        event_id=delivery_data.get("event_id"),
        url=delivery_data.get("url"),
        method=delivery_data.get("method", "POST"),
        headers=delivery_data.get("headers", {}),
        body=delivery_data.get("body", {}),
        auth_type=delivery_data.get("auth_type"),
        auth_config=delivery_data.get("auth_config", {}),
        max_attempts=delivery_data.get("max_attempts", 3),
    )
    db.add(delivery)
    await db.commit()
    await db.refresh(delivery)
    
    return {"id": str(delivery.id), "message": "Delivery queued"}

@router.get("/deliveries")
async def list_deliveries(
    endpoint_id: Optional[str] = None,
    event_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WebhookDelivery
    from sqlalchemy import desc
    
    query = select(WebhookDelivery).where(WebhookDelivery.client_id == current_user.client_id)
    
    if endpoint_id:
        query = query.where(WebhookDelivery.endpoint_id == endpoint_id)
    if event_id:
        query = query.where(WebhookDelivery.event_id == event_id)
    if status:
        query = query.where(WebhookDelivery.status == status)
    
    query = query.order_by(desc(WebhookDelivery.queued_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    deliveries = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "endpoint_id": str(d.endpoint_id) if d.endpoint_id else None,
            "event_id": str(d.event_id) if d.event_id else None,
            "status": d.status,
            "attempt": d.attempt,
            "response_status": d.response_status,
            "queued_at": d.queued_at.isoformat(),
            "sent_at": d.sent_at.isoformat() if d.sent_at else None,
        }
        for d in deliveries
    ]

@router.get("/dlq")
async def list_dlq(
    endpoint_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import DeadLetterQueue
    from sqlalchemy import desc
    
    query = select(DeadLetterQueue).where(DeadLetterQueue.client_id == current_user.client_id)
    
    if endpoint_id:
        query = query.where(DeadLetterQueue.endpoint_id == endpoint_id)
    if status:
        query = query.where(DeadLetterQueue.status == status)
    
    query = query.order_by(desc(DeadLetterQueue.received_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    dlq_entries = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "endpoint_id": str(d.endpoint_id),
            "event_id": str(d.event_id),
            "failure_reason": d.failure_reason,
            "status": d.status,
            "attempt_count": d.attempt_count,
            "received_at": d.received_at.isoformat(),
        }
        for d in dlq_entries
    ]

@router.post("/dlq/{dlq_id}/replay")
async def replay_dlq(
    dlq_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import DeadLetterQueue, WebhookEvent
    result = await db.execute(
        select(DeadLetterQueue).where(
            DeadLetterQueue.id == dlq_id,
            DeadLetterQueue.client_id == current_user.client_id
        )
    )
    dlq = result.scalar_one_or_none()
    if not dlq:
        raise HTTPException(status_code=404, detail="DLQ entry not found")
    
    # Create new webhook event from DLQ
    new_event = WebhookEvent(
        endpoint_id=dlq.endpoint_id,
        request_id=dlq.request_id,
        request_method=dlq.request_method,
        request_path=dlq.request_path,
        request_headers=dlq.request_headers,
        request_body=dlq.request_body,
        request_query=dlq.request_query,
        client_ip=dlq.client_ip,
    )
    db.add(new_event)
    
    dlq.status = "replayed"
    dlq.replayed_at = datetime.utcnow()
    dlq.replayed_event_id = new_event.id
    await db.commit()
    
    return {"message": "Event replayed", "new_event_id": str(new_event.id)}

@router.get("/signatures")
async def list_signatures(
    endpoint_id: Optional[str] = None,
    event_id: Optional[str] = None,
    is_valid: Optional[bool] = None,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import WebhookSignature
    query = select(WebhookSignature).where(WebhookSignature.client_id == current_user.client_id)
    
    if endpoint_id:
        query = query.where(WebhookSignature.endpoint_id == endpoint_id)
    if event_id:
        query = query.where(WebhookSignature.event_id == event_id)
    if is_valid is not None:
        query = query.where(WebhookSignature.is_valid == is_valid)
    
    result = await db.execute(query.order_by(desc(WebhookSignature.verified_at)).limit(100))
    signatures = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "endpoint_id": str(s.endpoint_id),
            "event_id": str(s.event_id),
            "is_valid": s.is_valid,
            "algorithm": s.algorithm,
            "verified_at": s.verified_at.isoformat(),
        }
        for s in signatures
    ]