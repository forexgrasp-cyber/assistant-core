"""Trust & Social Proof Service - Testimonials, Activity Feed, Referrals, Trust Signals."""

from __future__ import annotations

import secrets
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_, or_, delete, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

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
from app.models.user import User
from app.models.gamification import UserXP, UserStreak
from app.services.gamification_service import GamificationService


# =============================================================================
# Constants
# =============================================================================

REFERRAL_REWARDS = {
    "referrer_gems": 500,
    "referred_gems": 500,
    "referrer_xp": 1000,
    "referred_xp": 500,
}

ACTIVITY_TEMPLATES = {
    ActivityType.LESSON_COMPLETED: [
        "completed {lesson_title}",
        "finished {lesson_title} with {score}% accuracy",
    ],
    ActivityType.STREAK_MILESTONE: [
        "reached a {streak_days}-day streak! 🔥",
        "is on fire with a {streak_days}-day streak!",
    ],
    ActivityType.LEVEL_UP: [
        "leveled up to Level {new_level}! ⬆️",
        "just reached Level {new_level}!",
    ],
    ActivityType.ACHIEVEMENT_UNLOCKED: [
        "unlocked the '{achievement_name}' achievement! 🏆",
        "earned the '{achievement_name}' badge!",
    ],
    ActivityType.LEAGUE_PROMOTION: [
        "promoted to {new_tier} League! 🎉",
        "advanced to {new_tier} League!",
    ],
    ActivityType.LANGUAGE_STARTED: [
        "started learning {language_name}! 🌍",
        "began their {language_name} journey!",
    ],
    ActivityType.HUMAN_TUTOR_SESSION: [
        "completed a human tutor session! 💬",
        "had a great conversation with a tutor!",
    ],
    ActivityType.PERFECT_LESSON: [
        "aced {lesson_title} with 100%! 💯",
        "got a perfect score on {lesson_title}!",
    ],
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class TrustStats:
    """Aggregated trust statistics for landing page."""
    total_users: int
    total_lessons_completed: int
    total_countries: int
    average_rating: float
    total_hours_learned: int
    languages_offered: int
    active_learners_today: int
    success_stories: int


@dataclass
class ActivityFeedItem:
    """Activity feed item for display."""
    id: int
    user_id: int
    user_name: str
    user_avatar_url: Optional[str]
    user_location: Optional[str]
    activity_type: ActivityType
    title: str
    description: str
    language: Optional[str]
    created_at: datetime


# =============================================================================
# Trust Service
# =============================================================================

class TrustService:
    """Service for trust signals, social proof, and referrals."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -------------------------------------------------------------------------
    # Trust Signals (Global Stats)
    # -------------------------------------------------------------------------

    async def get_trust_stats(self) -> TrustStats:
        """Get aggregated trust statistics for landing page."""
        # Get or create trust signals
        signals = await self._get_or_create_default_signals()

        signal_map = {s.key: s.value for s in signals}

        return TrustStats(
            total_users=signal_map.get("total_users", 0),
            total_lessons_completed=signal_map.get("total_lessons_completed", 0),
            total_countries=signal_map.get("total_countries", 0),
            average_rating=signal_map.get("average_rating", 4.9) / 100,  # Stored as 490 for 4.90
            total_hours_learned=signal_map.get("total_hours_learned", 0),
            languages_offered=signal_map.get("languages_offered", 70),
            active_learners_today=signal_map.get("active_learners_today", 0),
            success_stories=signal_map.get("success_stories", 0),
        )

    async def _get_or_create_default_signals(self) -> List[TrustSignal]:
        """Get or create default trust signals."""
        default_signals = [
            {"key": "total_users", "label": "Learners Worldwide", "value": 50000, "display_format": "k_format", "icon": "users", "sort_order": 1},
            {"key": "total_lessons_completed", "label": "Lessons Completed", "value": 2500000, "display_format": "m_format", "icon": "book-open", "sort_order": 2},
            {"key": "total_countries", "label": "Countries", "value": 180, "display_format": "number", "icon": "globe", "sort_order": 3},
            {"key": "average_rating", "label": "App Store Rating", "value": 490, "display_format": "rating", "icon": "star", "sort_order": 4},
            {"key": "total_hours_learned", "label": "Hours Learned", "value": 1500000, "display_format": "m_format", "icon": "clock", "sort_order": 5},
            {"key": "languages_offered", "label": "Languages", "value": 70, "display_format": "number", "icon": "languages", "sort_order": 6},
            {"key": "active_learners_today", "label": "Learning Today", "value": 12500, "display_format": "k_format", "icon": "activity", "sort_order": 7},
            {"key": "success_stories", "label": "Success Stories", "value": 15000, "display_format": "k_format", "icon": "trophy", "sort_order": 8},
        ]

        signals = []
        for sig_data in default_signals:
            result = await self.db.execute(select(TrustSignal).where(TrustSignal.key == sig_data["key"]))
            signal = result.scalar_one_or_none()
            if not signal:
                signal = TrustSignal(**sig_data)
                self.db.add(signal)
            signals.append(signal)

        await self.db.flush()
        return signals

    async def increment_signal(self, key: str, amount: int = 1) -> TrustSignal:
        """Increment a trust signal counter."""
        result = await self.db.execute(select(TrustSignal).where(TrustSignal.key == key))
        signal = result.scalar_one_or_none()
        if signal:
            signal.value += amount
            signal.updated_at = datetime.now(timezone.utc)
        else:
            signal = TrustSignal(key=key, label=key.replace("_", " ").title(), value=amount)
            self.db.add(signal)
        await self.db.flush()
        return signal

    async def get_public_signals(self) -> List[TrustSignal]:
        """Get all public trust signals for display."""
        result = await self.db.execute(
            select(TrustSignal)
            .where(TrustSignal.is_public == True)
            .order_by(TrustSignal.sort_order)
        )
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Testimonials
    # -------------------------------------------------------------------------

    async def submit_testimonial(
        self,
        user_id: int,
        content: str,
        rating: int,
        language: Optional[str] = None,
        cefr_level: Optional[str] = None,
    ) -> Testimonial:
        """Submit a new testimonial (pending moderation)."""
        # Get user info for denormalization
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one()

        testimonial = Testimonial(
            user_id=user_id,
            content=content,
            rating=rating,
            author_name=user.name,
            author_avatar_url=user.avatar_url,
            author_location=user.location,
            author_level=user.xp.level if user.xp else None,
            language=language,
            cefr_level=cefr_level,
            status=TestimonialStatus.PENDING,
        )
        self.db.add(testimonial)
        await self.db.flush()
        return testimonial

    async def get_featured_testimonials(self, limit: int = 10, language: Optional[str] = None) -> List[Testimonial]:
        """Get featured/approved testimonials for display."""
        query = select(Testimonial).where(
            Testimonial.status.in_([TestimonialStatus.APPROVED, TestimonialStatus.FEATURED]),
        )
        if language:
            query = query.where(Testimonial.language == language)
        query = query.order_by(Testimonial.is_featured.desc(), Testimonial.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_testimonials_for_moderation(self, status: Optional[TestimonialStatus] = None) -> List[Testimonial]:
        """Get testimonials for admin moderation."""
        query = select(Testimonial).options(selectinload(Testimonial.user))
        if status:
            query = query.where(Testimonial.status == status)
        else:
            query = query.where(Testimonial.status == TestimonialStatus.PENDING)
        query = query.order_by(Testimonial.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def moderate_testimonial(
        self,
        testimonial_id: int,
        moderator_id: int,
        action: str,  # approve, reject, feature
        rejection_reason: Optional[str] = None,
    ) -> Testimonial:
        """Moderate a testimonial."""
        result = await self.db.execute(select(Testimonial).where(Testimonial.id == testimonial_id))
        testimonial = result.scalar_one_or_none()
        if not testimonial:
            raise ValueError("Testimonial not found")

        if action == "approve":
            testimonial.status = TestimonialStatus.APPROVED
        elif action == "reject":
            testimonial.status = TestimonialStatus.REJECTED
            testimonial.rejection_reason = rejection_reason
        elif action == "feature":
            testimonial.status = TestimonialStatus.FEATURED
            testimonial.is_featured = True
        else:
            raise ValueError("Invalid action")

        testimonial.moderated_by = moderator_id
        testimonial.moderated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return testimonial

    # -------------------------------------------------------------------------
    # Activity Feed
    # -------------------------------------------------------------------------

    async def record_activity(
        self,
        user_id: int,
        activity_type: ActivityType,
        title: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
        language: Optional[str] = None,
        is_public: bool = True,
    ) -> ActivityFeed:
        """Record a user activity for the feed."""
        activity = ActivityFeed(
            user_id=user_id,
            activity_type=activity_type,
            title=title,
            description=description,
            metadata=metadata or {},
            language=language,
            is_public=is_public,
        )
        self.db.add(activity)
        await self.db.flush()

        # Increment relevant trust signals
        if activity_type == ActivityType.LESSON_COMPLETED:
            await self.increment_signal("total_lessons_completed")
        elif activity_type == ActivityType.LANGUAGE_STARTED:
            await self.increment_signal("languages_started")

        return activity

    async def record_activity_from_template(
        self,
        user_id: int,
        activity_type: ActivityType,
        template_data: Dict[str, Any],
        language: Optional[str] = None,
        is_public: bool = True,
    ) -> ActivityFeed:
        """Record activity using a template."""
        templates = ACTIVITY_TEMPLATES.get(activity_type, ["did something awesome!"])
        template = random.choice(templates)

        # Format title and description
        try:
            title = template.format(**template_data)
            description = template.format(**template_data)
        except KeyError:
            title = template
            description = template

        return await self.record_activity(
            user_id=user_id,
            activity_type=activity_type,
            title=title,
            description=description,
            metadata=template_data,
            language=language,
            is_public=is_public,
        )

    async def get_public_activity_feed(
        self,
        limit: int = 50,
        offset: int = 0,
        language: Optional[str] = None,
    ) -> List[ActivityFeedItem]:
        """Get public activity feed for display."""
        query = (
            select(ActivityFeed, User.name, User.avatar_url, User.location)
            .join(User, ActivityFeed.user_id == User.id)
            .where(ActivityFeed.is_public == True)
            .order_by(desc(ActivityFeed.created_at))
            .limit(limit)
            .offset(offset)
        )
        if language:
            query = query.where(ActivityFeed.language == language)

        result = await self.db.execute(query)
        rows = result.all()

        return [
            ActivityFeedItem(
                id=activity.id,
                user_id=activity.user_id,
                user_name=name,
                user_avatar_url=avatar_url,
                user_location=location,
                activity_type=activity.activity_type,
                title=activity.title,
                description=activity.description,
                language=activity.language,
                created_at=activity.created_at,
            )
            for activity, name, avatar_url, location in rows
        ]

    async def get_user_activity_feed(
        self,
        user_id: int,
        limit: int = 50,
    ) -> List[ActivityFeed]:
        """Get activity feed for a specific user."""
        result = await self.db.execute(
            select(ActivityFeed)
            .where(ActivityFeed.user_id == user_id)
            .order_by(desc(ActivityFeed.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Referrals
    # -------------------------------------------------------------------------

    def _generate_referral_code(self) -> str:
        """Generate a unique referral code."""
        return f"TUTOR{secrets.token_urlsafe(6).upper()}"

    async def create_referral(self, referrer_id: int, referred_email: str) -> Referral:
        """Create a new referral."""
        # Check if referral already exists
        existing = await self.db.execute(
            select(Referral).where(
                Referral.referrer_id == referrer_id,
                Referral.referred_email == referred_email,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Referral already exists for this email")

        code = self._generate_referral_code()
        # Ensure uniqueness
        while True:
            result = await self.db.execute(select(Referral).where(Referral.code == code))
            if not result.scalar_one_or_none():
                break
            code = self._generate_referral_code()

        referral = Referral(
            referrer_id=referrer_id,
            referred_email=referred_email,
            code=code,
            referrer_reward_gems=REFERRAL_REWARDS["referrer_gems"],
            referred_reward_gems=REFERRAL_REWARDS["referred_gems"],
            referrer_reward_xp=REFERRAL_REWARDS["referrer_xp"],
            referred_reward_xp=REFERRAL_REWARDS["referred_xp"],
        )
        self.db.add(referral)
        await self.db.flush()
        return referral

    async def get_referral_by_code(self, code: str) -> Optional[Referral]:
        """Get referral by code."""
        result = await self.db.execute(select(Referral).where(Referral.code == code))
        return result.scalar_one_or_none()

    async def process_referral_signup(self, code: str, new_user_id: int) -> Optional[Referral]:
        """Process a referral when the referred user signs up."""
        referral = await self.get_referral_by_code(code)
        if not referral or referral.status != ReferralStatus.PENDING:
            return None

        referral.referred_id = new_user_id
        referral.status = ReferralStatus.SIGNED_UP
        referral.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return referral

    async def activate_referral(self, referred_user_id: int) -> Optional[Referral]:
        """Activate referral when referred user completes first lesson."""
        result = await self.db.execute(
            select(Referral).where(
                Referral.referred_id == referred_user_id,
                Referral.status == ReferralStatus.SIGNED_UP,
            )
        )
        referral = result.scalar_one_or_none()
        if not referral:
            return None

        referral.status = ReferralStatus.ACTIVATED
        referral.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        return referral

    async def reward_referral(self, referral_id: int) -> bool:
        """Reward both referrer and referred user."""
        result = await self.db.execute(select(Referral).where(Referral.id == referral_id))
        referral = result.scalar_one_or_none()
        if not referral or referral.status != ReferralStatus.ACTIVATED:
            return False

        # Award referrer
        gamification = GamificationService(self.db)
        await gamification.award_xp(referral.referrer_id, referral.referrer_reward_xp, "referral_reward", referral_id, "referral")
        xp_referrer = await gamification.get_or_create_xp(referral.referrer_id)
        xp_referrer.gems += referral.referrer_reward_gems
        xp_referrer.gems_earned_total += referral.referrer_reward_gems

        # Award referred user
        if referral.referred_id:
            await gamification.award_xp(referral.referred_id, referral.referred_reward_xp, "referral_bonus", referral_id, "referral")
            xp_referred = await gamification.get_or_create_xp(referral.referred_id)
            xp_referred.gems += referral.referred_reward_gems
            xp_referred.gems_earned_total += referral.referred_reward_gems

        referral.status = ReferralStatus.REWARDED
        referral.rewarded_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True

    async def get_user_referrals(self, user_id: int) -> List[Referral]:
        """Get all referrals sent by a user."""
        result = await self.db.execute(
            select(Referral)
            .where(Referral.referrer_id == user_id)
            .order_by(desc(Referral.created_at))
        )
        return list(result.scalars().all())

    async def get_referral_stats(self, user_id: int) -> Dict[str, Any]:
        """Get referral statistics for a user."""
        referrals = await self.get_user_referrals(user_id)
        total = len(referrals)
        signed_up = sum(1 for r in referrals if r.status in [ReferralStatus.SIGNED_UP, ReferralStatus.ACTIVATED, ReferralStatus.REWARDED])
        activated = sum(1 for r in referrals if r.status in [ReferralStatus.ACTIVATED, ReferralStatus.REWARDED])
        rewarded = sum(1 for r in referrals if r.status == ReferralStatus.REWARDED)

        total_gems_earned = sum(r.referrer_reward_gems for r in referrals if r.status == ReferralStatus.REWARDED)
        total_xp_earned = sum(r.referrer_reward_xp for r in referrals if r.status == ReferralStatus.REWARDED)

        return {
            "total_referrals": total,
            "signed_up": signed_up,
            "activated": activated,
            "rewarded": rewarded,
            "conversion_rate": (activated / total * 100) if total > 0 else 0,
            "total_gems_earned": total_gems_earned,
            "total_xp_earned": total_xp_earned,
            "referral_code": referrals[0].code if referrals else await self._get_or_create_user_code(user_id),
        }

    async def _get_or_create_user_code(self, user_id: int) -> str:
        """Get or create a referral code for a user (for sharing)."""
        result = await self.db.execute(
            select(Referral).where(Referral.referrer_id == user_id).order_by(Referral.created_at).limit(1)
        )
        referral = result.scalar_one_or_none()
        if referral:
            return referral.code
        # Create a dummy referral for code generation
        referral = Referral(
            referrer_id=user_id,
            referred_email="pending@referral.com",
            code=self._generate_referral_code(),
            status=ReferralStatus.PENDING,
        )
        self.db.add(referral)
        await self.db.flush()
        return referral.code

    # -------------------------------------------------------------------------
    # Press Mentions
    # -------------------------------------------------------------------------

    async def get_featured_press(self, limit: int = 6) -> List[PressMention]:
        """Get featured press mentions."""
        result = await self.db.execute(
            select(PressMention)
            .where(PressMention.is_featured == True)
            .order_by(PressMention.sort_order, desc(PressMention.published_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_all_press(self, limit: int = 20) -> List[PressMention]:
        """Get all press mentions."""
        result = await self.db.execute(
            select(PressMention)
            .order_by(desc(PressMention.is_featured), PressMention.sort_order, desc(PressMention.published_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    # -------------------------------------------------------------------------
    # Auto-activity triggers (called from other services)
    # -------------------------------------------------------------------------

    async def on_lesson_completed(
        self,
        user_id: int,
        lesson_title: str,
        score: int,
        language: str,
        is_perfect: bool = False,
    ):
        """Trigger when user completes a lesson."""
        await self.record_activity_from_template(
            user_id=user_id,
            activity_type=ActivityType.PERFECT_LESSON if is_perfect else ActivityType.LESSON_COMPLETED,
            template_data={"lesson_title": lesson_title, "score": score},
            language=language,
        )

    async def on_streak_milestone(self, user_id: int, streak_days: int, language: Optional[str] = None):
        """Trigger when user reaches a streak milestone."""
        await self.record_activity_from_template(
            user_id=user_id,
            activity_type=ActivityType.STREAK_MILESTONE,
            template_data={"streak_days": streak_days},
            language=language,
        )

    async def on_level_up(self, user_id: int, new_level: int, language: Optional[str] = None):
        """Trigger when user levels up."""
        await self.record_activity_from_template(
            user_id=user_id,
            activity_type=ActivityType.LEVEL_UP,
            template_data={"new_level": new_level},
            language=language,
        )

    async def on_achievement_unlocked(self, user_id: int, achievement_name: str, language: Optional[str] = None):
        """Trigger when user unlocks an achievement."""
        await self.record_activity_from_template(
            user_id=user_id,
            activity_type=ActivityType.ACHIEVEMENT_UNLOCKED,
            template_data={"achievement_name": achievement_name},
            language=language,
        )

    async def on_league_promotion(self, user_id: int, new_tier: str, language: Optional[str] = None):
        """Trigger when user gets promoted in league."""
        await self.record_activity_from_template(
            user_id=user_id,
            activity_type=ActivityType.LEAGUE_PROMOTION,
            template_data={"new_tier": new_tier.title()},
            language=language,
        )

    async def on_language_started(self, user_id: int, language_name: str):
        """Trigger when user starts a new language."""
        await self.increment_signal("total_users")  # New learner
        await self.record_activity_from_template(
            user_id=user_id,
            activity_type=ActivityType.LANGUAGE_STARTED,
            template_data={"language_name": language_name},
            language=language_name.lower()[:2],
        )

    async def on_human_tutor_session(self, user_id: int, language: Optional[str] = None):
        """Trigger when user completes a human tutor session."""
        await self.record_activity_from_template(
            user_id=user_id,
            activity_type=ActivityType.HUMAN_TUTOR_SESSION,
            template_data={},
            language=language,
        )