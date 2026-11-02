"""
Repository layer for data access.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from marketplace.models import (
    User,
    UserRole,
    UserStatus,
    VAProfile,
    VAStatus,
    ClientProfile,
    ClientStatus,
    Match,
    MatchStatus,
    PaymentIntent,
    PaymentStatus,
    PaymentType,
    Subscription,
    OnboardingPlan,
    Delivery,
    JournalEntry,
    Account,
    Notification,
    VettingResult,
)


class UserRepository:
    """Repository for user operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        return user

    async def get_by_id(self, user_id: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def update(self, user: User) -> User:
        user.updated_at = datetime.now(UTC)
        await self.session.flush()
        return user

    async def list(
        self,
        role: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[User]:
        query = select(User)
        if role:
            query = query.where(User.role == role)
        if status:
            query = query.where(User.status == status)
        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count(self, role: Optional[str] = None, status: Optional[str] = None) -> int:
        query = select(func.count(User.id))
        if role:
            query = query.where(User.role == role)
        if status:
            query = query.where(User.status == status)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def ensure_platform_user(
        self,
        user_id: str,
        email: str,
        role: UserRole = UserRole.CLIENT,
    ) -> User:
        """Idempotently create the marketplace User row for an auth user."""
        user = await self.get_by_id(user_id)
        if user:
            return user
        user = User(
            id=str(user_id),
            email=email,
            hashed_password="",
            role=role,
            status=UserStatus.PENDING,
        )
        self.session.add(user)
        await self.session.flush()
        return user


class VAProfileRepository:
    """Repository for VA profile operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, profile: VAProfile) -> VAProfile:
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def get_by_id(self, profile_id: str) -> Optional[VAProfile]:
        result = await self.session.execute(
            select(VAProfile).where(VAProfile.id == profile_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: str) -> Optional[VAProfile]:
        result = await self.session.execute(
            select(VAProfile).where(VAProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_external(self, source: str, profile_url: str) -> Optional[VAProfile]:
        """Find a profile previously sourced from an external marketplace."""
        if not source:
            return None
        query = select(VAProfile).where(VAProfile.source == source)
        if profile_url:
            query = query.where(VAProfile.source_profile_url == profile_url)
        result = (await self.session.execute(query.limit(1))).scalar_one_or_none()
        return result

    async def update(self, profile: VAProfile) -> VAProfile:
        profile.updated_at = datetime.now(UTC)
        await self.session.flush()
        return profile

    async def list_active(
        self,
        skills: Optional[list[str]] = None,
        min_rate: Optional[Decimal] = None,
        max_rate: Optional[Decimal] = None,
        timezone: Optional[str] = None,
        min_hours: Optional[int] = None,
        min_vetting_score: Decimal = Decimal("0.6"),
        limit: int = 50,
        offset: int = 0,
    ) -> list[VAProfile]:
        query = select(VAProfile).where(
            VAProfile.status == VAStatus.ACTIVE,
            VAProfile.vetting_score >= min_vetting_score,
        )
        if skills:
            for skill in skills:
                query = query.where(VAProfile.skills.op("@>")([{"name": skill}]))
        if min_rate:
            query = query.where(VAProfile.hourly_rate >= min_rate)
        if max_rate:
            query = query.where(VAProfile.hourly_rate <= max_rate)
        if timezone:
            query = query.where(VAProfile.timezone == timezone)
        if min_hours:
            query = query.where(VAProfile.availability_hours_per_week >= min_hours)
        query = query.order_by(VAProfile.vetting_score.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def search_all(
        self,
        skills: list[str],
        min_hourly_rate: Optional[float] = None,
        max_hourly_rate: Optional[float] = None,
        min_rating: Optional[float] = None,
        timezone: Optional[str] = None,
        availability_hours: Optional[int] = None,
        limit: int = 50,
    ) -> list[VAProfile]:
        query = select(VAProfile).where(VAProfile.status == VAStatus.ACTIVE)
        # For now, simple filtering - could be enhanced with full-text search
        if skills:
            for skill in skills[:5]:  # Limit to 5 skills for performance
                query = query.where(
                    VAProfile.skills.op("@>")([{"name": skill}])
                )
        if min_hourly_rate:
            query = query.where(VAProfile.hourly_rate >= Decimal(str(min_hourly_rate)))
        if max_hourly_rate:
            query = query.where(VAProfile.hourly_rate <= Decimal(str(max_hourly_rate)))
        if min_rating:
            query = query.where(VAProfile.source_rating >= Decimal(str(min_rating)))
        if timezone:
            query = query.where(VAProfile.timezone == timezone)
        if availability_hours:
            query = query.where(
                VAProfile.availability_hours_per_week >= availability_hours
            )
        query = query.order_by(VAProfile.source_rating.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())


class ClientProfileRepository:
    """Repository for client profile operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, profile: ClientProfile) -> ClientProfile:
        self.session.add(profile)
        await self.session.flush()
        return profile

    async def get_by_id(self, profile_id: str) -> Optional[ClientProfile]:
        result = await self.session.execute(
            select(ClientProfile).where(ClientProfile.id == profile_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: str) -> Optional[ClientProfile]:
        result = await self.session.execute(
            select(ClientProfile).where(ClientProfile.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def update(self, profile: ClientProfile) -> ClientProfile:
        profile.updated_at = datetime.now(UTC)
        await self.session.flush()
        return profile


class MatchRepository:
    """Repository for match operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, match: Match) -> Match:
        self.session.add(match)
        await self.session.flush()
        return match

    async def get_by_id(self, match_id: str) -> Optional[Match]:
        result = await self.session.execute(
            select(Match)
            .options(
                selectinload(Match.client).selectinload(ClientProfile.user),
                selectinload(Match.va).selectinload(VAProfile.user),
            )
            .where(Match.id == match_id)
        )
        return result.scalar_one_or_none()

    async def get_by_client(self, client_id: str) -> list[Match]:
        result = await self.session.execute(
            select(Match)
            .options(
                selectinload(Match.va).selectinload(VAProfile.user),
            )
            .where(Match.client_id == client_id)
            .order_by(Match.proposed_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_va(self, va_id: str) -> list[Match]:
        result = await self.session.execute(
            select(Match)
            .options(
                selectinload(Match.client).selectinload(ClientProfile.user),
            )
            .where(Match.va_id == va_id)
            .order_by(Match.proposed_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, match: Match) -> Match:
        await self.session.flush()
        return match

    async def get_pending_for_client(self, client_id: str) -> list[Match]:
        result = await self.session.execute(
            select(Match)
            .options(selectinload(Match.va).selectinload(VAProfile.user))
            .where(Match.client_id == client_id, Match.status == MatchStatus.PROPOSED)
            .order_by(Match.match_score.desc())
        )
        return list(result.scalars().all())

    async def list_active_with_client(self) -> list[Match]:
        """
        Fee-bearing matches (payment cycle active) — statuses ACCEPTED,
        ONBOARDING, ACTIVE — with the client eagerly loaded.
        """
        result = await self.session.execute(
            select(Match)
            .options(selectinload(Match.client).selectinload(ClientProfile.user))
            .where(
                Match.status.in_(
                    [MatchStatus.ACCEPTED, MatchStatus.ONBOARDING, MatchStatus.ACTIVE]
                )
            )
        )
        return list(result.scalars().all())


class PaymentRepository:
    """Repository for payment operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, payment: PaymentIntent) -> PaymentIntent:
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def get_by_id(self, payment_id: str) -> Optional[PaymentIntent]:
        result = await self.session.execute(
            select(PaymentIntent).where(PaymentIntent.id == payment_id)
        )
        return result.scalar_one_or_none()

    async def get_by_stripe_id(self, stripe_id: str) -> Optional[PaymentIntent]:
        result = await self.session.execute(
            select(PaymentIntent).where(
                PaymentIntent.stripe_payment_intent_id == stripe_id
            )
        )
        return result.scalar_one_or_none()

    async def update(self, payment: PaymentIntent) -> PaymentIntent:
        payment.updated_at = datetime.now(UTC)
        await self.session.flush()
        return payment

    async def list_by_client(
        self, client_id: str, limit: int = 50, offset: int = 0
    ) -> list[PaymentIntent]:
        result = await self.session.execute(
            select(PaymentIntent)
            .where(PaymentIntent.client_id == client_id)
            .order_by(PaymentIntent.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())


class SubscriptionRepository:
    """Repository for subscription operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, subscription: Subscription) -> Subscription:
        self.session.add(subscription)
        await self.session.flush()
        return subscription

    async def get_by_id(self, subscription_id: str) -> Optional[Subscription]:
        result = await self.session.execute(
            select(Subscription).where(Subscription.id == subscription_id)
        )
        return result.scalar_one_or_none()

    async def get_by_stripe_id(self, stripe_id: str) -> Optional[Subscription]:
        result = await self.session.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == stripe_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_client(self, client_id: str) -> list[Subscription]:
        result = await self.session.execute(
            select(Subscription).where(Subscription.client_id == client_id)
        )
        return list(result.scalars().all())

    async def get_active_by_match(self, match_id: str) -> Optional[Subscription]:
        result = await self.session.execute(
            select(Subscription).where(
                Subscription.match_id == match_id,
                Subscription.status.in_(
                    [PaymentStatus.SUCCEEDED, PaymentStatus.PROCESSING]
                ),
            )
        )
        return result.scalar_one_or_none()

    async def update(self, subscription: Subscription) -> Subscription:
        subscription.updated_at = datetime.now(UTC)
        await self.session.flush()
        return subscription


class OnboardingPlanRepository:
    """Repository for onboarding plan operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, plan: OnboardingPlan) -> OnboardingPlan:
        self.session.add(plan)
        await self.session.flush()
        return plan

    async def get_by_match(self, match_id: str) -> Optional[OnboardingPlan]:
        result = await self.session.execute(
            select(OnboardingPlan).where(OnboardingPlan.match_id == match_id)
        )
        return result.scalar_one_or_none()

    async def update(self, plan: OnboardingPlan) -> OnboardingPlan:
        await self.session.flush()
        return plan


class DeliveryRepository:
    """Repository for delivery operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, delivery: Delivery) -> Delivery:
        self.session.add(delivery)
        await self.session.flush()
        return delivery

    async def get_by_id(self, delivery_id: str) -> Optional[Delivery]:
        result = await self.session.execute(
            select(Delivery).where(Delivery.id == delivery_id)
        )
        return result.scalar_one_or_none()

    async def get_by_match(self, match_id: str) -> list[Delivery]:
        result = await self.session.execute(
            select(Delivery)
            .where(Delivery.match_id == match_id)
            .order_by(Delivery.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_va(self, va_id: str) -> list[Delivery]:
        result = await self.session.execute(
            select(Delivery).where(Delivery.va_id == va_id)
        )
        return list(result.scalars().all())

    async def update(self, delivery: Delivery) -> Delivery:
        await self.session.flush()
        return delivery


class LedgerRepository:
    """Repository for ledger operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_account(self, account: Account) -> Account:
        self.session.add(account)
        await self.session.flush()
        return account

    async def get_account(self, account_id: str) -> Optional[Account]:
        result = await self.session.execute(
            select(Account).where(Account.id == account_id)
        )
        return result.scalar_one_or_none()

    async def get_account_by_name(self, name: str) -> Optional[Account]:
        result = await self.session.execute(
            select(Account).where(Account.name == name)
        )
        return result.scalar_one_or_none()

    async def record_entry(self, entry: JournalEntry) -> JournalEntry:
        if not entry.is_balanced():
            raise ValueError("Journal entry not balanced")
        self.session.add(entry)
        # Update account balances
        for line in entry.lines:
            account = await self.get_account(line["account_id"])
            if account:
                debit = Decimal(str(line.get("debit", 0)))
                credit = Decimal(str(line.get("credit", 0)))
                account.balance = account.balance + debit - credit
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def get_trial_balance(self) -> dict[str, Decimal]:
        result = await self.session.execute(
            select(Account.name, Account.balance).where(Account.balance != 0)
        )
        return {row.name: row.balance for row in result.all()}


class NotificationRepository:
    """Repository for notification operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, notification: Notification) -> Notification:
        self.session.add(notification)
        await self.session.flush()
        return notification

    async def get_unread_count(self, user_id: str) -> int:
        result = await self.session.execute(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id, Notification.read == False
            )
        )
        return result.scalar() or 0

    async def get_unread(self, user_id: str, limit: int = 20) -> list[Notification]:
        result = await self.session.execute(
            select(Notification)
            .where(Notification.user_id == user_id, Notification.read == False)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_read(self, notification_id: str, user_id: str) -> bool:
        result = await self.session.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        notification = result.scalar_one_or_none()
        if notification and not notification.read:
            notification.read = True
            notification.read_at = datetime.now(UTC)
            await self.session.flush()
            return True
        return False


class VettingRepository:
    """Repository for vetting results."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, result: VettingResult) -> VettingResult:
        self.session.add(result)
        await self.session.flush()
        return result

    async def get_by_va(self, va_id: str) -> list[VettingResult]:
        result = await self.session.execute(
            select(VettingResult)
            .where(VettingResult.va_id == va_id)
            .order_by(VettingResult.completed_at.desc())
        )
        return list(result.scalars().all())

    async def get_latest(self, va_id: str, test_type: str) -> Optional[VettingResult]:
        result = await self.session.execute(
            select(VettingResult)
            .where(VettingResult.va_id == va_id, VettingResult.test_type == test_type)
            .order_by(VettingResult.completed_at.desc())
        )
        return result.scalar_one_or_none()