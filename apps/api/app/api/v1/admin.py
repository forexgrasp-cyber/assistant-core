"""
Admin API endpoints: Platform administration, user management, billing, analytics.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import structlog

from ...core.config import get_settings
from ...core.database import get_db
from ...core.security import get_current_active_user
from ...models import User, Agency, Client, Role, UserRole, Invoice, AuditLog

logger = structlog.get_logger()
router = APIRouter()

settings = get_settings()


async def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    """Require admin or superuser role."""
    if not (current_user.is_superuser or current_user.is_staff or current_user.role in ("admin", "owner")):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


@router.get("/platform/stats")
async def get_platform_stats(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    agencies_count = await db.execute(select(func.count(Agency.id)))
    users_count = await db.execute(select(func.count(User.id)))
    clients_count = await db.execute(select(func.count(Client.id)))
    active_users = await db.execute(select(func.count(User.id)).where(User.is_active == True))
    return {
        "total_agencies": agencies_count.scalar(),
        "total_users": users_count.scalar(),
        "total_clients": clients_count.scalar(),
        "active_users": active_users.scalar(),
    }


@router.get("/users")
async def list_users(
    agency_id: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(User)
    if agency_id:
        query = query.where(User.agency_id == agency_id)
    if is_active is not None:
        query = query.where(User.is_active == is_active)
    query = query.order_by(desc(User.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "role": u.role,
            "is_active": u.is_active,
            "mfa_enabled": u.mfa_enabled,
            "last_login_at": u.last_login_at.isoformat() if u.last_login_at else None,
            "created_at": u.created_at.isoformat(),
            "agency_id": str(u.agency_id) if u.agency_id else None,
        }
        for u in users
    ]


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "is_active": user.is_active,
        "mfa_enabled": user.mfa_enabled,
        "timezone": user.timezone,
        "locale": user.locale,
        "last_login_at": user.last_login_at.isoformat() if user.last_login_at else None,
        "created_at": user.created_at.isoformat(),
        "agency_id": str(user.agency_id) if user.agency_id else None,
    }


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    user_data: dict,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    for field, value in user_data.items():
        if hasattr(user, field) and field not in ("id", "email", "hashed_password", "created_at"):
            setattr(user, field, value)
    user.updated_at = datetime.utcnow()
    await db.commit()
    return {"message": "User updated"}


@router.post("/users/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    user.is_active = False
    await db.commit()
    return {"message": "User deactivated"}


@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = True
    await db.commit()
    return {"message": "User activated"}


@router.get("/agencies")
async def list_agencies(
    status: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(Agency)
    if status:
        query = query.where(Agency.subscription_status == status)
    query = query.order_by(desc(Agency.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    agencies = result.scalars().all()
    return [
        {
            "id": str(a.id),
            "name": a.name,
            "slug": a.slug,
            "subscription_status": a.subscription_status,
            "trial_ends_at": a.trial_ends_at.isoformat() if a.trial_ends_at else None,
            "created_at": a.created_at.isoformat(),
        }
        for a in agencies
    ]


@router.get("/agencies/{agency_id}")
async def get_agency(
    agency_id: str,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agency).where(Agency.id == agency_id))
    agency = result.scalar_one_or_none()
    if not agency:
        raise HTTPException(status_code=404, detail="Agency not found")
    return {
        "id": str(agency.id),
        "name": agency.name,
        "slug": agency.slug,
        "subscription_status": agency.subscription_status,
        "trial_ends_at": agency.trial_ends_at.isoformat() if agency.trial_ends_at else None,
        "created_at": agency.created_at.isoformat(),
    }


@router.get("/billing/overview")
async def billing_overview(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    mrr_result = await db.execute(
        select(func.coalesce(func.sum(Invoice.total), 0)).where(
            Invoice.status == "paid",
            Invoice.issued_at >= datetime.utcnow() - timedelta(days=30),
        )
    )
    mrr = mrr_result.scalar() or 0
    cancelled = await db.execute(
        select(func.count(Agency.id)).where(
            Agency.subscription_status == "cancelled",
            Agency.updated_at >= datetime.utcnow() - timedelta(days=30),
        )
    )
    total_agencies = await db.execute(select(func.count(Agency.id)))
    return {
        "mrr": float(mrr),
        "churned_agencies_30d": cancelled.scalar() or 0,
        "total_agencies": total_agencies.scalar(),
    }


@router.get("/audit-logs")
async def list_audit_logs(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(AuditLog).order_by(desc(AuditLog.timestamp))
    if user_id:
        query = query.where(AuditLog.user_id == user_id)
    if action:
        query = query.where(AuditLog.action == action)
    if resource_type:
        query = query.where(AuditLog.resource_type == resource_type)
    if start_date:
        query = query.where(AuditLog.timestamp >= datetime.fromisoformat(start_date))
    if end_date:
        query = query.where(AuditLog.timestamp <= datetime.fromisoformat(end_date))
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()
    return [
        {
            "id": str(l.id),
            "user_id": str(l.user_id) if l.user_id else None,
            "action": l.action,
            "resource_type": l.resource_type,
            "resource_id": l.resource_id,
            "status": l.status,
            "timestamp": l.timestamp.isoformat(),
            "ip_address": l.ip_address,
        }
        for l in logs
    ]