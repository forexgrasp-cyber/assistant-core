"""
Tenant/Agency management API endpoints.
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
import structlog

from ...core.config import get_settings
from ...core.database import get_db
from ...core.security import get_current_active_user
from ...models import Agency, User, UserRole, Role

logger = structlog.get_logger()
router = APIRouter()


# Pydantic models
class AgencyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: Optional[str] = None
    description: Optional[str] = None
    website: Optional[str] = None
    timezone: str = Field(default="UTC")
    currency: str = Field(default="USD")
    white_label_domain: Optional[str] = None
    white_label_enabled: bool = False


class AgencyUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    website: Optional[str] = None
    logo_url: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    white_label_domain: Optional[str] = None
    white_label_enabled: Optional[bool] = None
    timezone: Optional[str] = None
    currency: Optional[str] = None
    settings: Optional[dict] = None


class AgencyResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    website: Optional[str]
    logo_url: Optional[str]
    primary_color: Optional[str]
    secondary_color: Optional[str]
    white_label_domain: Optional[str]
    white_label_enabled: bool
    timezone: str
    currency: str
    settings: dict
    subscription_status: str
    trial_ends_at: Optional[str]
    created_at: str
    updated_at: str
    owner_id: str
    owner_email: Optional[str] = None
    client_count: int = 0
    user_count: int = 0


class AgencyListResponse(BaseModel):
    agencies: List[AgencyResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserInvite(BaseModel):
    email: str
    role: str = "member"
    client_ids: List[str] = []


class UserRoleUpdate(BaseModel):
    role: str


@router.post("", response_model=AgencyResponse, status_code=status.HTTP_201_CREATED)
async def create_agency(
    agency_data: AgencyCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new agency (sub-agency under current user's agency)."""
    # Check if user has permission to create agencies
    # Only agency owners/admins can create sub-agencies
    
    # Generate slug if not provided
    slug = agency_data.slug or agency_data.name.lower().replace(" ", "-")
    
    # Check if slug already exists in current agency
    result = await db.execute(
        select(Agency).where(
            Agency.slug == agency_data.slug,
            Agency.id == current_user.agency_id
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Slug already exists")
    
    # Create agency
    agency = Agency(
        name=agency_data.name,
        slug=agency_data.slug,
        description=agency_data.description,
        website=agency_data.website,
        timezone=agency_data.timezone,
        currency=agency_data.currency,
        white_label_domain=agency_data.white_label_domain,
        white_label_enabled=agency_data.white_label_enabled,
        platform_id=current_user.platform_id,
        owner_id=current_user.id,
        settings=agency_data.settings or {},
    )
    
    db.add(agency)
    await db.commit()
    await db.refresh(agency)
    
    # Add current user as owner of new agency
    # This would require updating the user's agency_id or creating a ClientUser link
    
    return AgencyResponse.from_orm(agency)


@router.get("", response_model=AgencyListResponse)
async def list_agencies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List agencies accessible to current user."""
    # Build query
    query = select(Agency).where(Agency.platform_id == current_user.platform_id)
    
    # Filter by user's agency hierarchy
    # User can see their own agency and sub-agencies
    if current_user.agency_id:
        query = query.where(
            (Agency.id == current_user.agency_id) |
            (Agency.platform_id == current_user.platform_id)
        )
    
    if search:
        query = query.where(
            Agency.name.ilike(f"%{search}%") |
            Agency.slug.ilike(f"%{search}%")
        )
    
    if status:
        query = query.where(Agency.subscription_status == status)
    
    # Count total
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()
    
    # Paginate
    query = query.order_by(Agency.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    agencies = result.scalars().all()
    
    # Get counts for each agency
    agency_responses = []
    for agency in agencies:
        # Get client count
        client_count_result = await db.execute(
            select(func.count()).select_from(
                select(1).where(
                    # Would need Client model
                ).subquery()
            )
        )
        
        agency_responses.append(AgencyResponse.from_orm(agency))
    
    return AgencyListResponse(
        agencies=agency_responses,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size,
    )


@router.get("/{agency_id}", response_model=AgencyResponse)
async def get_agency(
    agency_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get agency details."""
    result = await db.execute(
        select(Agency)
        .options(selectinload(Agency.owner))
        .where(Agency.id == agency_id)
    )
    agency = result.scalar_one_or_none()
    
    if not agency:
        raise HTTPException(status_code=404, detail="Agency not found")
    
    # Check access permissions
    # User must be in same platform or have access to this agency
    
    return AgencyResponse.from_orm(agency)


@router.patch("/{agency_id}", response_model=AgencyResponse)
async def update_agency(
    agency_id: str,
    agency_data: AgencyUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update agency settings."""
    result = await db.execute(select(Agency).where(Agency.id == agency_id))
    agency = result.scalar_one_or_none()
    
    if not agency:
        raise HTTPException(status_code=404, detail="Agency not found")
    
    # Check permissions
    # Only owner or admin can update
    
    update_data = agency_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(agency, field, value)
    
    await db.commit()
    await db.refresh(agency)
    
    return AgencyResponse.from_orm(agency)


@router.delete("/{agency_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agency(
    agency_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an agency (soft delete)."""
    result = await db.execute(select(Agency).where(Agency.id == agency_id))
    agency = result.scalar_one_or_none()
    
    if not agency:
        raise HTTPException(status_code=404, detail="Agency not found")
    
    # Check permissions - only owner can delete
    if agency.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this agency")
    
    # Soft delete - mark as inactive
    agency.is_active = False
    agency.subscription_status = "cancelled"
    await db.commit()
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Agency members
@router.get("/{agency_id}/members")
async def list_agency_members(
    agency_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """List all members of an agency."""
    # Check access
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles))
        .where(User.agency_id == agency_id)
    )
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
            "roles": [r.role.name for r in u.roles],
        }
        for u in users
    ]


@router.post("/{agency_id}/members", status_code=status.HTTP_201_CREATED)
async def invite_member(
    agency_id: str,
    invite: UserInvite,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Invite a new member to the agency."""
    # Check if user already exists
    result = await db.execute(select(User).where(User.email == invite.email))
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        # Check if already a member
        # If not, add as ClientUser
        pass
    
    # Create new user or link existing
    # Send invitation email
    # TODO: Implement invitation flow
    
    return {"message": "Invitation sent"}


@router.patch("/{agency_id}/members/{user_id}")
async def update_member_role(
    agency_id: str,
    user_id: str,
    role_update: UserRoleUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a member's role."""
    # Check permissions
    # Update role
    # TODO: Implement role update
    
    return {"message": "Role updated"}


@router.delete("/{agency_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    agency_id: str,
    user_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from the agency."""
    # Check permissions
    # Remove user from agency
    # TODO: Implement member removal
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Agency settings
@router.get("/{agency_id}/settings")
async def get_agency_settings(
    agency_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Get agency settings."""
    result = await db.execute(select(Agency).where(Agency.id == agency_id))
    agency = result.scalar_one_or_none()
    
    if not agency:
        raise HTTPException(status_code=404, detail="Agency not found")
    
    return {
        "white_label": {
            "enabled": agency.white_label_enabled,
            "domain": agency.white_label_domain,
            "logo_url": agency.logo_url,
            "primary_color": agency.primary_color,
            "secondary_color": agency.secondary_color,
        },
        "timezone": agency.timezone,
        "currency": agency.currency,
        "settings": agency.settings,
    }


@router.patch("/{agency_id}/settings")
async def update_agency_settings(
    agency_id: str,
    settings_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Update agency settings."""
    result = await db.execute(select(Agency).where(Agency.id == agency_id))
    agency = result.scalar_one_or_none()
    
    if not agency:
        raise HTTPException(status_code=404, detail="Agency not found")
    
    # Merge settings
    agency.settings = {**agency.settings, **settings_data}
    
    if "white_label" in settings_data:
        wl = settings_data["white_label"]
        if "enabled" in wl:
            agency.white_label_enabled = wl["enabled"]
        if "domain" in wl:
            agency.white_label_domain = wl["domain"]
        if "logo_url" in wl:
            agency.logo_url = wl["logo_url"]
        if "primary_color" in wl:
            agency.primary_color = wl["primary_color"]
        if "secondary_color" in wl:
            agency.secondary_color = wl["secondary_color"]
    
    if "timezone" in settings_data:
        agency.timezone = settings_data["timezone"]
    if "currency" in settings_data:
        agency.currency = settings_data["currency"]
    
    await db.commit()
    
    return {"message": "Settings updated"}