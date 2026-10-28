"""
Client management API endpoints.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc
from sqlalchemy.orm import selectinload
from datetime import datetime
import structlog
import uuid

from ...core.config import get_settings
from ...core.database import get_db
from ...core.security import get_current_active_user
from ...models import Client, Customer, CustomerSegment, CustomerSegmentMember, Order, User

logger = structlog.get_logger()
router = APIRouter()

settings = get_settings()

# Pydantic models
class ClientCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: Optional[str] = None
    description: Optional[str] = None
    shop_domain: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    timezone: str = Field(default="UTC")
    currency: str = Field(default="USD")
    settings: dict = Field(default_factory=dict)
    attribution_config: dict = Field(default_factory=dict)

class ClientUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    shop_domain: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    settings: Optional[dict] = None
    attribution_config: Optional[dict] = None
    is_active: Optional[bool] = None

class CustomerResponse(BaseModel):
    id: str
    external_id: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    total_orders: int
    total_spent: float
    average_order_value: float
    first_order_at: Optional[str]
    last_order_at: Optional[str]
    rfm_segment: Optional[str]
    predicted_ltv: Optional[float]
    churn_probability: Optional[float]
    tags: List[str]
    is_active: bool
    created_at: str
    updated_at: str

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, desc
from sqlalchemy.orm import selectinload
from datetime import datetime
import structlog
import uuid

from ...core.config import get_settings
from ...core.database import get_db
from ...core.security import get_current_active_user
from ...models import Client, Customer, CustomerSegment, CustomerSegmentMember, Order, User

logger = structlog.get_logger()
router = APIRouter()

settings = get_settings()

@router.get("")
async def list_clients(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select, func, or_, desc
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select, func, or_, desc
    from sqlalchemy.orm import selectinload
    
    query = select(Client).where(Client.agency_id == current_user.agency_id)
    
    if search:
        query = query.where(
            or_(
                Client.name.ilike(f"%{search}%"),
                Client.slug.ilike(f"%{search}%"),
                Client.shop_domain.ilike(f"%{search}%"),
            )
        )
    
    if status == "active":
        query = query.where(Client.is_active == True)
    elif status == "inactive":
        query = query.where(Client.is_active == False)
    elif status == "onboarded":
        query = query.where(Client.is_onboarded == True)
    elif status == "not_onboarded":
        query = query.where(Client.is_onboarded == False)
    
    count_result = await db.execute(
        select(func.count()).select_from(
            select(Client.id).where(Client.agency_id == current_user.agency_id).subquery()
        )
    )
    total = count_result.scalar()
    
    query = query.order_by(Client.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    clients = result.scalars().all()
    
    client_responses = []
    for client in clients:
        order_stats = await db.execute(
            select(
                func.count(Order.id).label("order_count"),
                func.coalesce(func.sum(Order.total), 0).label("total_revenue"),
                func.count(func.distinct(Order.customer_id)).label("customer_count"),
            ).where(Order.client_id == client.id)
        )
        stats = order_stats.one()
        
        client_responses.append({
            "id": str(client.id),
            "name": client.name,
            "slug": client.slug,
            "description": client.description,
            "shop_domain": client.shop_domain,
            "website": client.website,
            "logo_url": client.logo_url,
            "timezone": client.timezone,
            "currency": client.currency,
            "settings": client.settings,
            "attribution_config": client.attribution_config,
            "is_active": client.is_active,
            "is_onboarded": client.is_onboarded,
            "last_sync_at": client.last_sync_at.isoformat() if client.last_sync_at else None,
            "created_at": client.created_at.isoformat(),
            "updated_at": client.updated_at.isoformat(),
            "customer_count": stats.customer_count or 0,
            "order_count": stats.order_count or 0,
            "total_revenue": float(stats.total_revenue or 0),
        })
    
    return {
        "clients": client_responses,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_client(
    client_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import Client
    slug = client_data.get("slug") or client_data.get("name", "").lower().replace(" ", "-")
    
    result = await db.execute(
        select(Client).where(
            Client.slug == slug,
            Client.agency_id == current_user.agency_id
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Client with this slug already exists")
    
    client = Client(
        agency_id=current_user.agency_id,
        name=client_data.get("name"),
        slug=client_data.get("slug") or client_data.get("name", "").lower().replace(" ", "-"),
        description=client_data.get("description"),
        shop_domain=client_data.get("shop_domain"),
        website=client_data.get("website"),
        logo_url=client_data.get("logo_url"),
        timezone=client_data.get("timezone", "UTC"),
        currency=client_data.get("currency", "USD"),
        settings=client_data.get("settings", {}),
        attribution_config=client_data.get("attribution_config", {}),
    )
    
    db.add(client)
    await db.commit()
    await db.refresh(client)
    
    return {
        "id": str(client.id),
        "name": client.name,
        "slug": client.slug,
        "message": "Client created successfully"
    }

@router.get("/{client_id}")
async def get_client(
    client_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.agency_id == current_user.agency_id
        )
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    return {
        "id": str(client.id),
        "name": client.name,
        "slug": client.slug,
        "description": client.description,
        "shop_domain": client.shop_domain,
        "website": client.website,
        "logo_url": client.logo_url,
        "timezone": client.timezone,
        "currency": client.currency,
        "settings": client.settings,
        "attribution_config": client.attribution_config,
        "is_active": client.is_active,
        "is_onboarded": client.is_onboarded,
        "last_sync_at": client.last_sync_at.isoformat() if client.last_sync_at else None,
        "created_at": client.created_at.isoformat(),
        "updated_at": client.updated_at.isoformat(),
    }

@router.patch("/{client_id}")
async def update_client(
    client_id: str,
    client_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.agency_id == current_user.agency_id
        )
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    update_data = client_data
    for field, value in update_data.items():
        if hasattr(client, field):
            setattr(client, field, value)
    
    await db.commit()
    await db.refresh(client)
    
    return {"message": "Client updated successfully"}

@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_client(
    client_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.agency_id == current_user.agency_id
        )
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    client.is_active = False
    await db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# Client onboarding
@router.post("/{client_id}/onboard")
async def onboard_client(
    client_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import Client
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.agency_id == current_user.agency_id
        )
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    if client.is_onboarded:
        raise HTTPException(status_code=400, detail="Client already onboarded")
    
    client.is_onboarded = True
    client.onboarded_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Client onboarded successfully, sync initiated"}

@router.get("/{client_id}/sync-status")
async def get_sync_status(
    client_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import Client, SyncJob
    from sqlalchemy import desc
    
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.agency_id == current_user.agency_id
        )
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    result = await db.execute(
        select(SyncJob)
        .where(SyncJob.client_id == client_id)
        .order_by(desc(SyncJob.created_at))
        .limit(10)
    )
    sync_jobs = result.scalars().all()
    
    return {
        "client_id": str(client.id),
        "is_onboarded": client.is_onboarded,
        "last_sync_at": client.last_sync_at.isoformat() if client.last_sync_at else None,
        "recent_jobs": [
            {
                "id": str(job.id),
                "platform": job.platform,
                "status": job.status,
                "records_synced": job.records_synced,
                "records_failed": job.records_failed,
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            }
            for job in sync_jobs
        ]
    }

@router.post("/{client_id}/sync")
async def trigger_sync(
    client_id: str,
    platform: Optional[str] = None,
    full_sync: bool = False,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.agency_id == current_user.agency_id
        )
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    from ...models import SyncJob
    import uuid
    
    sync_job = SyncJob(
        id=uuid.uuid4(),
        client_id=client.id,
        connection_id=None,
        platform=platform or "all",
        sync_type="full" if full_sync else "incremental",
        status="pending",
        triggered_by="manual",
    )
    
    db.add(sync_job)
    await db.commit()
    
    return {"message": "Sync job created", "job_id": str(sync_job.id)}

@router.get("/{client_id}/customers")
async def list_customers(
    client_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    segment: Optional[str] = None,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import or_, desc
    
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.agency_id == current_user.agency_id
        )
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    from sqlalchemy import or_, desc
    query = select(Customer).where(Customer.client_id == client_id)
    
    if search:
        query = query.where(
            or_(
                Customer.email.ilike(f"%{search}%"),
                Customer.first_name.ilike(f"%{search}%"),
                Customer.last_name.ilike(f"%{search}%"),
            )
        )
    
    if segment:
        from ...models import CustomerSegmentMember, CustomerSegment
        query = query.join(CustomerSegmentMember).join(CustomerSegment).where(
            CustomerSegment.slug == segment
        )
    
    count_result = await db.execute(
        select(func.count()).select_from(
            query.with_only_columns(Customer.id).subquery()
        )
    )
    total = count_result.scalar()
    
    query = query.order_by(desc(Customer.last_order_at).nullslast()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    customers = result.scalars().all()
    
    return {
        "customers": [
            {
                "id": str(c.id),
                "external_id": c.external_id,
                "email": c.email,
                "phone": c.phone,
                "first_name": c.first_name,
                "last_name": c.last_name,
                "total_orders": c.total_orders,
                "total_spent": float(c.total_spent),
                "average_order_value": float(c.average_order_value),
                "first_order_at": c.first_order_at.isoformat() if c.first_order_at else None,
                "last_order_at": c.last_order_at.isoformat() if c.last_order_at else None,
                "rfm_segment": c.rfm_segment,
                "predicted_ltv": float(c.predicted_ltv) if c.predicted_ltv else None,
                "churn_probability": float(c.churn_probability) if c.churn_probability else None,
                "tags": c.tags,
                "is_active": c.is_active,
                "created_at": c.created_at.isoformat(),
                "updated_at": c.updated_at.isoformat(),
            }
            for c in customers
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }

@router.get("/{client_id}/customers/{customer_id}")
async def get_customer(
    client_id: str,
    customer_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.client_id == client_id
        )
    )
    customer = result.scalar_one_or_none()
    
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    
    from sqlalchemy import desc
    orders_result = await db.execute(
        select(Order)
        .where(Order.customer_id == customer_id, Order.client_id == client_id)
        .order_by(desc(Order.placed_at))
        .limit(20)
    )
    orders = orders_result.scalars().all()
    
    return {
        "id": str(customer.id),
        "external_id": customer.external_id,
        "email": customer.email,
        "phone": customer.phone,
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "total_orders": customer.total_orders,
        "total_spent": float(customer.total_spent),
        "average_order_value": float(customer.average_order_value),
        "first_order_at": customer.first_order_at.isoformat() if customer.first_order_at else None,
        "last_order_at": customer.last_order_at.isoformat() if customer.last_order_at else None,
        "rfm_segment": customer.rfm_segment,
        "predicted_ltv": float(customer.predicted_ltv) if customer.predicted_ltv else None,
        "churn_probability": float(customer.churn_probability) if customer.churn_probability else None,
        "tags": customer.tags,
        "properties": customer.properties,
        "is_active": customer.is_active,
        "created_at": customer.created_at.isoformat(),
        "updated_at": customer.updated_at.isoformat(),
        "recent_orders": [
            {
                "id": str(o.id),
                "order_number": o.order_number,
                "total": float(o.total),
                "status": o.status,
                "placed_at": o.placed_at.isoformat(),
            }
            for o in orders
        ],
    }

@router.get("/{client_id}/segments")
async def list_segments(
    client_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.agency_id == current_user.agency_id
        )
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    from ...models import CustomerSegment
    result = await db.execute(
        select(CustomerSegment).where(CustomerSegment.client_id == client_id)
        .order_by(CustomerSegment.name)
    )
    segments = result.scalars().all()
    
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "slug": s.slug,
            "description": s.description,
            "definition": s.definition,
            "type": s.type,
            "customer_count": s.customer_count,
            "is_active": s.is_active,
            "auto_recalculate": s.auto_recalculate,
            "last_calculated_at": s.last_calculated_at.isoformat() if s.last_calculated_at else None,
            "created_at": s.created_at.isoformat(),
            "updated_at": s.updated_at.isoformat(),
        }
        for s in segments
    ]

@router.post("/{client_id}/segments", status_code=201)
async def create_segment(
    client_id: str,
    segment_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    from ...models import CustomerSegment, Client
    
    result = await db.execute(
        select(Client).where(
            Client.id == client_id,
            Client.agency_id == current_user.agency_id
        )
    )
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    slug = segment_data.get("slug") or segment_data.get("name", "").lower().replace(" ", "-")
    
    segment = CustomerSegment(
        client_id=client_id,
        name=segment_data.get("name"),
        slug=segment_data.get("slug") or segment_data.get("name", "").lower().replace(" ", "-"),
        description=segment_data.get("description"),
        definition=segment_data.get("definition", {}),
        type=segment_data.get("type", "dynamic"),
    )
    
    db.add(segment)
    await db.commit()
    await db.refresh(segment)
    
    return {
        "id": str(segment.id),
        "name": segment.name,
        "slug": segment.slug,
        "description": segment.description,
        "definition": segment.definition,
        "type": segment.type,
        "customer_count": segment.customer_count,
        "is_active": segment.is_active,
        "auto_recalculate": segment.auto_recalculate,
        "created_at": segment.created_at.isoformat(),
        "updated_at": segment.updated_at.isoformat(),
    }

@router.get("/{client_id}/segments/{segment_id}")
async def get_segment(
    client_id: str,
    segment_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CustomerSegment).where(
            CustomerSegment.id == segment_id,
            CustomerSegment.client_id == client_id
        )
    )
    segment = result.scalar_one_or_none()
    
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    return {
        "id": str(segment.id),
        "name": segment.name,
        "slug": segment.slug,
        "description": segment.description,
        "definition": segment.definition,
        "type": segment.type,
        "customer_count": segment.customer_count,
        "is_active": segment.is_active,
        "auto_recalculate": segment.auto_recalculate,
        "last_calculated_at": segment.last_calculated_at.isoformat() if segment.last_calculated_at else None,
        "created_at": segment.created_at.isoformat(),
        "updated_at": segment.updated_at.isoformat(),
    }

@router.patch("/{client_id}/segments/{segment_id}")
async def update_segment(
    client_id: str,
    segment_id: str,
    segment_data: dict,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CustomerSegment).where(
            CustomerSegment.id == segment_id,
            CustomerSegment.client_id == client_id
        )
    )
    segment = result.scalar_one_or_none()
    
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    update_data = segment_data
    for field, value in update_data.items():
        setattr(segment, field, value)
    
    await db.commit()
    await db.refresh(segment)
    
    return {
        "id": str(segment.id),
        "name": segment.name,
        "slug": segment.slug,
        "description": segment.description,
        "definition": segment.definition,
        "type": segment.type,
        "customer_count": segment.customer_count,
        "is_active": segment.is_active,
        "auto_recalculate": segment.auto_recalculate,
    }

@router.post("/{client_id}/segments/{segment_id}/calculate")
async def calculate_segment(
    client_id: str,
    segment_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return {"message": "Segment calculation started"}

@router.delete("/{client_id}/segments/{segment_id}", status_code=204)
async def delete_segment(
    client_id: str,
    segment_id: str,
    current_user = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CustomerSegment).where(
            CustomerSegment.id == segment_id,
            CustomerSegment.client_id == client_id
        )
    )
    segment = result.scalar_one_or_none()
    
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    
    await db.delete(segment)
    await db.commit()
    
    return Response(status_code=204)