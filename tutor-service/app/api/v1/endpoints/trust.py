"""Trust & Social Proof API Endpoints."""

from __future__ import annotations

from typing import List, Optional, Dict, Any
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict, EmailStr

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User
from app.models.trust import (
    Testimonial,
    ActivityFeed,
    Referral,
    TrustSignal,
    PressMention,
    TestimonialStatus,
    ActivityType,
    ReferralStatus,
)
from app.schemas.trust import (
    TrustStatsResponse,
    TestimonialResponse,
    TestimonialSubmitRequest,
    ActivityFeedResponse,
    ReferralResponse,
    ReferralCreateRequest,
    ReferralStatsResponse,
    PressMentionResponse,
    TrustSignalResponse,
)
from app.services.trust_service import TrustService

router = APIRouter(prefix="/trust", tags=["trust"])


# =============================================================================
# Dependency: Get Current User (placeholder - replace with real auth)
# =============================================================================

async def get_current_user(
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current user from token."""
    from sqlalchemy import select
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# =============================================================================
# Trust Signals / Stats (Public)
# =============================================================================

@router.get("/stats", response_model=TrustStatsResponse)
async def get_trust_stats(
    db: AsyncSession = Depends(get_db),
):
    """Get trust statistics for landing page (public)."""
    service = TrustService(db)
    stats = await service.get_trust_stats()
    return TrustStatsResponse(
        total_users=stats.total_users,
        total_lessons_completed=stats.total_lessons_completed,
        total_countries=stats.total_countries,
        average_rating=stats.average_rating,
        total_hours_learned=stats.total_hours_learned,
        languages_offered=stats.languages_offered,
        active_learners_today=stats.active_learners_today,
        success_stories=stats.success_stories,
    )


@router.get("/signals", response_model=List[TrustSignalResponse])
async def get_trust_signals(
    db: AsyncSession = Depends(get_db),
):
    """Get all public trust signals for display."""
    service = TrustService(db)
    signals = await service.get_public_signals()
    return [
        TrustSignalResponse(
            key=s.key,
            label=s.label,
            value=s.value,
            display_format=s.display_format,
            icon=s.icon,
            description=s.description,
        )
        for s in signals
    ]


# =============================================================================
# Testimonials
# =============================================================================

@router.get("/testimonials", response_model=List[TestimonialResponse])
async def get_featured_testimonials(
    limit: int = Query(10, le=50),
    language: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get featured/approved testimonials for display (public)."""
    service = TrustService(db)
    testimonials = await service.get_featured_testimonials(limit=limit, language=language)
    return [
        TestimonialResponse(
            id=t.id,
            content=t.content,
            rating=t.rating,
            author_name=t.author_name,
            author_avatar_url=t.author_avatar_url,
            author_location=t.author_location,
            author_level=t.author_level,
            language=t.language,
            cefr_level=t.cefr_level,
            is_featured=t.is_featured,
            created_at=t.created_at,
        )
        for t in testimonials
    ]


@router.post("/testimonials", response_model=TestimonialResponse, status_code=status.HTTP_201_CREATED)
async def submit_testimonial(
    request: TestimonialSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a testimonial (requires auth)."""
    service = TrustService(db)
    testimonial = await service.submit_testimonial(
        user_id=current_user.id,
        content=request.content,
        rating=request.rating,
        language=request.language,
        cefr_level=request.cefr_level,
    )
    return TestimonialResponse(
        id=testimonial.id,
        content=testimonial.content,
        rating=testimonial.rating,
        author_name=testimonial.author_name,
        author_avatar_url=testimonial.author_avatar_url,
        author_location=testimonial.author_location,
        author_level=testimonial.author_level,
        language=testimonial.language,
        cefr_level=testimonial.cefr_level,
        is_featured=testimonial.is_featured,
        created_at=testimonial.created_at,
    )


# =============================================================================
# Activity Feed
# =============================================================================

@router.get("/activity", response_model=List[ActivityFeedResponse])
async def get_public_activity_feed(
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    language: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get public activity feed for social proof (public)."""
    service = TrustService(db)
    activities = await service.get_public_activity_feed(limit=limit, offset=offset, language=language)
    return [
        ActivityFeedResponse(
            id=a.id,
            user_id=a.user_id,
            user_name=a.user_name,
            user_avatar_url=a.user_avatar_url,
            user_location=a.user_location,
            activity_type=a.activity_type.value,
            title=a.title,
            description=a.description,
            language=a.language,
            created_at=a.created_at,
        )
        for a in activities
    ]


@router.get("/activity/user", response_model=List[ActivityFeedResponse])
async def get_user_activity_feed(
    limit: int = Query(50, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get activity feed for current user."""
    service = TrustService(db)
    activities = await service.get_user_activity_feed(current_user.id, limit=limit)
    return [
        ActivityFeedResponse(
            id=a.id,
            user_id=a.user_id,
            user_name=current_user.name,
            user_avatar_url=current_user.avatar_url,
            user_location=current_user.location,
            activity_type=a.activity_type.value,
            title=a.title,
            description=a.description,
            language=a.language,
            created_at=a.created_at,
        )
        for a in activities
    ]


# =============================================================================
# Referrals
# =============================================================================

@router.get("/referrals/stats", response_model=ReferralStatsResponse)
async def get_referral_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get referral statistics for current user."""
    service = TrustService(db)
    stats = await service.get_referral_stats(current_user.id)
    return ReferralStatsResponse(**stats)


@router.post("/referrals", response_model=ReferralResponse, status_code=status.HTTP_201_CREATED)
async def create_referral(
    request: ReferralCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new referral for an email."""
    service = TrustService(db)
    try:
        referral = await service.create_referral(current_user.id, request.email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ReferralResponse(
        id=referral.id,
        code=referral.code,
        referred_email=referral.referred_email,
        status=referral.status.value,
        referrer_reward_gems=referral.referrer_reward_gems,
        referred_reward_gems=referral.referred_reward_gems,
        created_at=referral.created_at,
    )


@router.get("/referrals", response_model=List[ReferralResponse])
async def get_user_referrals(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all referrals sent by current user."""
    service = TrustService(db)
    referrals = await service.get_user_referrals(current_user.id)
    return [
        ReferralResponse(
            id=r.id,
            code=r.code,
            referred_email=r.referred_email,
            status=r.status.value,
            referrer_reward_gems=r.referrer_reward_gems,
            referred_reward_gems=r.referred_reward_gems,
            created_at=r.created_at,
        )
        for r in referrals
    ]


@router.get("/referrals/{code}", response_model=ReferralResponse)
async def get_referral_by_code(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """Get referral info by code (public, for landing page)."""
    service = TrustService(db)
    referral = await service.get_referral_by_code(code)
    if not referral:
        raise HTTPException(status_code=404, detail="Referral code not found")
    return ReferralResponse(
        id=referral.id,
        code=referral.code,
        referred_email=referral.referred_email,
        status=referral.status.value,
        referrer_reward_gems=referral.referrer_reward_gems,
        referred_reward_gems=referral.referred_reward_gems,
        created_at=referral.created_at,
    )


# =============================================================================
# Press Mentions
# =============================================================================

@router.get("/press", response_model=List[PressMentionResponse])
async def get_press_mentions(
    featured_only: bool = Query(False),
    limit: int = Query(20, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Get press mentions (public)."""
    service = TrustService(db)
    if featured_only:
        press = await service.get_featured_press(limit=limit)
    else:
        press = await service.get_all_press(limit=limit)
    return [
        PressMentionResponse(
            id=p.id,
            title=p.title,
            publication=p.publication,
            publication_logo_url=p.publication_logo_url,
            url=p.url,
            excerpt=p.excerpt,
            published_at=p.published_at,
            is_featured=p.is_featured,
        )
        for p in press
    ]


# =============================================================================
# Admin: Testimonial Moderation
# =============================================================================

@router.get("/admin/testimonials", response_model=List[TestimonialResponse])
async def get_testimonials_for_moderation(
    status: Optional[TestimonialStatus] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get testimonials for moderation (admin only)."""
    # TODO: Add admin check
    service = TrustService(db)
    testimonials = await service.get_testimonials_for_moderation(status)
    return [
        TestimonialResponse(
            id=t.id,
            content=t.content,
            rating=t.rating,
            author_name=t.author_name,
            author_avatar_url=t.author_avatar_url,
            author_location=t.author_location,
            author_level=t.author_level,
            language=t.language,
            cefr_level=t.cefr_level,
            is_featured=t.is_featured,
            created_at=t.created_at,
        )
        for t in testimonials
    ]


@router.post("/admin/testimonials/{testimonial_id}/moderate", response_model=TestimonialResponse)
async def moderate_testimonial(
    testimonial_id: int,
    action: str,  # approve, reject, feature
    rejection_reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Moderate a testimonial (admin only)."""
    # TODO: Add admin check
    service = TrustService(db)
    try:
        testimonial = await service.moderate_testimonial(
            testimonial_id=testimonial_id,
            moderator_id=current_user.id,
            action=action,
            rejection_reason=rejection_reason,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return TestimonialResponse(
        id=testimonial.id,
        content=testimonial.content,
        rating=testimonial.rating,
        author_name=testimonial.author_name,
        author_avatar_url=testimonial.author_avatar_url,
        author_location=testimonial.author_location,
        author_level=testimonial.author_level,
        language=testimonial.language,
        cefr_level=testimonial.cefr_level,
        is_featured=testimonial.is_featured,
        created_at=testimonial.created_at,
    )