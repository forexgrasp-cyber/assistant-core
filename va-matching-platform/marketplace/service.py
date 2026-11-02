"""
VA Matching Platform - Main Service
====================================
Orchestrates the complete VA matching pipeline:
- VA sourcing from multiple platforms
- Client intake & matching
- Vetting workflow
- Onboarding & delivery tracking
- Billing & payments
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from .base import ClientProfile, Match, MatchStatus, VAProfile, VAStatus
from .adapters import VAAdapterRegistry, default_registry
from .matching import MatchingService
from .vetting import VettingService
from .carriers import OnboardingManager, DeliveryTracker
from .payments import PaymentService
from .banking import Ledger, init_ledger
from .base import VAStatus, MatchStatus

log = logging.getLogger(__name__)


@dataclass
class MatchResult:
    """Result of a match operation."""
    match_id: str
    client_id: str
    va_id: str
    match_score: float
    status: MatchStatus
    payment_intent_id: str | None = None
    subscription_id: str | None = None


class VAMatchingPlatform:
    """
    Main orchestration service for the VA Matching Platform.
    
    Orchestrates the complete pipeline:
    1. Client intake & profiling
    2. VA sourcing from multiple platforms
    3. Matching algorithm
    4. Vetting workflow
    5. Onboarding & onboarding
    5. Billing & payments
    6. Delivery tracking
    """

    def __init__(
        self,
        adapter_registry=None,
        ledger_db: str = "ledger.db",
        stripe_api_key: str | None = None,
        stripe_webhook_secret: str | None = None,
        platform_fee_rate: Decimal = Decimal("0.20"),
        monthly_platform_fee: Decimal = Decimal("200.00"),
    ):
        self.adapter_registry = adapter_registry or default_registry
        self.matching_service = MatchingService()
        self.vetting_service = VettingService()
        self.onboarding_manager = OnboardingManager()
        self.delivery_tracker = None  # Set after onboarding
        self.payment_service = PaymentService()
        self.ledger = init_ledger("ledger.db")

        # Configuration
        self.placement_fee_min = Decimal("1500.00")
        self.placement_fee_max = Decimal("3000.00")
        self.monthly_platform_fee = Decimal("200.00")

        log.info("VAMatchingPlatform initialized")

    async def initialize(self):
        """Initialize all subsystems."""
        log.info("Discovering working VA source adapters...")
        await self.adapter_registry.discover_working_instances()
        # Initialize delivery tracker
        from .carriers import DeliveryTracker
        self.delivery_tracker = DeliveryTracker()
        log.info("Platform initialized successfully")

    # ==================== CLIENT INTAKE ====================

    async def create_client(
        self,
        email: str,
        company_name: str,
        contact_name: str,
        timezone: str,
        industry: str,
        company_size: int,
        monthly_budget: float,
        needed_hours_per_week: int,
        required_skills: list[str],
        tasks_to_delegate: list[str],
        current_tools: list[str] | None = None,
        preferred_timezone_overlap_hours: int = 4,
        max_hourly_rate: float = 0,
        source: str = "direct",
    ) -> str:
        """Create a new client profile from intake form."""
        client = ClientProfile(
            id=str(uuid4()),
            email=email,
            company_name=company_name,
            contact_name=contact_name,
            timezone=timezone,
            industry=industry,
            company_size=company_size,
            monthly_budget=Decimal(str(monthly_budget)),
            needed_hours_per_week=needed_hours_per_week,
            required_skills=required_skills,
            tasks_to_delegate=tasks_to_delegate,
            current_tools=current_tools or [],
            preferred_timezone_overlap_hours=preferred_timezone_overlap_hours,
            max_hourly_rate=Decimal(str(max_hourly_rate)) if max_hourly_rate > 0 else Decimal("0"),
            source=source,
        )

        # In production: save to database
        log.info(f"Created client: {client.id} ({client.company_name})")
        return client.id

    # ==================== VA SOURCING ====================

    async def source_vas(
        self,
        skills: list[str],
        min_hourly_rate: float | None = None,
        max_hourly_rate: float | None = None,
        min_rating: float | None = None,
        timezone: str | None = None,
        availability_hours: int | None = None,
        limit: int = 50,
    ) -> list:
        """Source VAs from all registered adapters."""
        return await self.adapter_registry.search_all_sources(
            skills=skills,
            min_hourly_rate=min_hourly_rate,
            max_hourly_rate=max_hourly_rate,
            min_rating=min_rating,
            timezone=timezone,
            availability_hours=availability_hours,
            limit=limit,
        )

    async def vet_va_pool(self, vas: list, task_category: str = "admin") -> list:
        """Vet a pool of VAs."""
        return await self.vetting_service.bulk_vet(vas, task_category)

    # ==================== MATCHING ====================

    async def match_client(
        self,
        client_id: str,
        client_profile,
        va_pool: list,
        limit: int = 5,
        min_score: float = 0.4,
    ) -> list:
        """Find matches for a client."""
        return await self.matching_service.match_client(
            client_profile, va_pool, limit=limit, min_score=min_score
        )

    async def create_match(
        self,
        client_id: str,
        client_profile,
        va_id: str,
        va_profile,
        match_score: float,
        match_factors: dict,
    ) -> str:
        """Create a match record."""
        match = Match(
            id=str(uuid4()),
            client_id=client_id,
            va_id=va_id,
            status=MatchStatus.PROPOSED,
            match_score=match_score,
            match_factors=match_factors,
        )
        # In production: save to database
        log.info(f"Created match: {match.id} (score: {match_score:.2f})")
        return match.id

    # ==================== BILLING & PAYMENTS ====================

    async def charge_placement_fee(
        self,
        match_id: str,
        client_id: str,
        va_id: str,
        amount: Decimal,
    ) -> str:
        """Charge one-time placement fee."""
        payment = await self.payment_service.charge_placement_fee(
            client_id=client_id,
            amount=amount,
            match_id=match_id,
            va_id=va_id,
            description=f"VA placement fee for match",
        )
        return payment.id

    async def setup_monthly_platform_fee(
        self,
        match_id: str,
        client_id: str,
        va_id: str,
        amount: Decimal | None = None,
    ) -> str:
        """Set up recurring monthly platform fee."""
        subscription = await self.payment_service.setup_monthly_platform_fee(
            client_id=client_id,
            match_id=match_id,
            va_id=va_id,
            amount=amount,
        )
        return subscription.id

    async def record_placement_fee_in_ledger(
        self,
        match_id: str,
        client_id: str,
        va_id: str,
        amount: Decimal,
    ):
        """Record placement fee in double-entry ledger."""
        entry, platform_entry = self.ledger.create_placement_fee_entry(
            match_id=match_id,
            client_id=client_id,
            va_id=va_id,
            amount=amount,
        )
        self.ledger.record_entry(entry)
        self.ledger.record_entry(platform_entry)

    # ==================== ONBOARDING ====================

    async def start_onboarding(self, match_id: str, client_id: str, va_id: str) -> dict:
        """Start onboarding for a match."""
        plan = self.onboarding_manager.create_plan(match_id, client_id, va_id)
        self.onboarding_manager.start_onboarding(match_id)
        return plan

    async def complete_onboarding_task(self, match_id: str, task_id: str, completed_by: str) -> bool:
        """Complete an onboarding task."""
        return self.onboarding_manager.complete_task(match_id, task_id, completed_by)

    def get_onboarding_progress(self, match_id: str) -> dict:
        return self.onboarding_manager.get_progress(match_id)

    # ==================== DELIVERY TRACKING ====================

    def create_delivery(
        self,
        match_id: str,
        task_id: str,
        va_id: str,
        client_id: str,
        title: str,
        description: str,
    ):
        return self.delivery_tracker.create_delivery(
            match_id, task_id, va_id, client_id, title, description
        )

    def submit_delivery(self, match_id: str, delivery_id: str, deliverables: list[str], hours: float):
        self.delivery_tracker.submit_delivery(match_id, delivery_id, deliverables, hours)

    def review_delivery(self, match_id: str, delivery_id: str, status: str, feedback: str):
        self.delivery_tracker.review_delivery(match_id, delivery_id, status, feedback)

    # ==================== MATCH LIFECYCLE ====================

    async def accept_match(self, match_id: str, client_id: str) -> bool:
        """Client accepts match proposal."""
        # In production: update match status, trigger billing, start onboarding
        log.info(f"Match {match_id} accepted by client {client_id}")
        return True

    async def reject_match(self, match_id: str, client_id: str, reason: str) -> bool:
        """Client rejects match proposal."""
        log.info(f"Match {match_id} rejected by client {client_id}: {reason}")
        return True

    async def complete_match(self, match_id: str) -> bool:
        """Mark match as completed successfully."""
        log.info(f"Match {match_id} completed")
        return True

    # ==================== DISPUTES & REFUNDS ====================

    async def request_refund(self, match_id: str, payment_intent_id: str, reason: str):
        """Request refund for a match."""
        payment = self.payment_service.get_payment_intent(payment_intent_id)
        if not payment:
            raise ValueError(f"Payment intent not found: {payment_intent_id}")

        refund = await self.payment_service.refund_placement_fee(
            payment_intent_id=payment_intent_id,
            reason=reason,
        )

        # Record in ledger
        self.ledger.record_entry(
            self.ledger.create_refund_entry(match_id, Decimal("0"), reason)
        )

        log.info(f"Refund processed for match {match_id}: {refund}")
        return refund

    async def cancel_platform_fee(self, subscription_id: str, immediate: bool = False):
        """Cancel monthly platform fee subscription."""
        return await self.payment_service.cancel_platform_fee(subscription_id, immediate)

    # ==================== REPORTING ====================

    def get_ledger_trial_balance(self) -> dict:
        return self.ledger.get_trial_balance()

    def get_payment_stats(self) -> dict:
        return {
            "total_payment_intents": len(self.payment_service.payment_intents),
            "total_subscriptions": len(self.payment_service.subscriptions),
            "ledger_balances": self.ledger.get_trial_balance(),
        }


# Singleton instance
_platform_instance = None


def get_platform() -> VAMatchingPlatform:
    """Get or create platform singleton."""
    global _platform_instance
    if _platform_instance is None:
        _platform_instance = VAMatchingPlatform()
    return _platform_instance


async def initialize_platform() -> VAMatchingPlatform:
    """Initialize and return platform instance."""
    platform = get_platform()
    await platform.initialize()
    return platform