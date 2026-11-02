"""
Payments — orchestration over the canonical shared billing services (multi-provider).

All provider protocol work (checkout, subscriptions, webhooks, Connect onboarding)
is canonical via shared.billing.* services.

This module only wires marketplace economics (placement fee, monthly
platform fee, refunds) onto those canonical services.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

import structlog

from shared.billing import (
    UnifiedPaymentService,
    EntitlementsService,
)
from shared.billing.entitlements_service import ServiceResponse
from shared.config.settings import Settings as BaseSettings
from shared.payments.sales_ledger import (
    SaleStatus,
    get_sales_ledger,
)
from shared.payments.hardening import (
    content_key,
    extract_event_id,
    get_webhook_gate,
    validate_amount,
)

from marketplace.config import settings as marketplace_settings

log = structlog.get_logger(__name__)


class PaymentType(str, Enum):
    """Marketplace-specific payment kinds."""

    PLACEMENT_FEE = "placement_fee"
    PLATFORM_FEE = "platform_fee"
    MONTHLY_SUBSCRIPTION = "monthly_subscription"
    REFUND = "refund"


@dataclass
class MarketFeeResult:
    """Result of creating a canonical payment + ledger sale registration."""

    payment_id: str | None
    checkout_url: str | None
    checkout_token: str | None
    amount: Decimal
    currency: str
    status: str
    sale_intent_id: str | None = None
    duplicate: bool = False
    raw: dict[str, Any] = field(default_factory=dict)


class PaymentService:
    """Marketplace charge orchestration on canonical billing rails (multi-provider)."""

    def __init__(self, platform_fee_rate: Decimal | None = None):
        self.platform_fee_rate = Decimal(
            str(platform_fee_rate or marketplace_settings.PLATFORM_FEE_RATE)
        )
        self.monthly_fee = Decimal(str(marketplace_settings.MONTHLY_PLATFORM_FEE))
        
        # Parse supported providers
        self.supported_providers = [
            p.strip() for p in marketplace_settings.SUPPORTED_PAYMENT_PROVIDERS.split(",")
        ]
        self.default_provider = marketplace_settings.DEFAULT_PAYMENT_PROVIDER
        if self.default_provider not in self.supported_providers:
            self.default_provider = "stripe"
        
        # Initialize canonical billing services
        self.unified_payment = UnifiedPaymentService(
            tenant_id="va-matching-platform",
            provider=self.default_provider,
        )
        self.entitlements = EntitlementsService()
        self.ledger = get_sales_ledger()
        self.gate = get_webhook_gate()
        
        # For Stripe Connect (VA payouts) - still uses Stripe directly
        self.connect = None
        if "stripe" in self.supported_providers:
            from shared.billing.stripe_connect_service import StripeConnectService
            self.connect = StripeConnectService(tenant_id="va-matching-platform")

    # ── Provider helpers ────────────────────────────────────────────────

    def _get_provider(self, provider: str | None) -> str:
        """Resolve provider name, falling back to default."""
        provider = (provider or self.default_provider).lower()
        if provider not in self.supported_providers:
            log.warning("provider_not_supported_fallback", 
                       provider=provider, fallback=self.default_provider)
            return self.default_provider
        return provider

    def _get_stripe_billing(self):
        """Lazy-load StripeBillingService when needed."""
        if not hasattr(self, "_stripe_billing"):
            from shared.billing.stripe_billing_service import StripeBillingService
            self._stripe_billing = StripeBillingService(
                secret_key=marketplace_settings.STRIPE_SECRET_KEY,
                webhook_secret=marketplace_settings.STRIPE_WEBHOOK_SECRET,
                entitlements=self.entitlements,
            )
        return self._stripe_billing

    # ── Charging ────────────────────────────────────────────────────────

    async def charge_placement_fee(
        self,
        *,
        placement_fee: Decimal,
        client_id: str,
        match_id: str,
        customer_email: str | None = None,
        va_id: str | None = None,
        description: str = "VA placement fee",
        provider: str | None = None,
    ) -> MarketFeeResult:
        """Create a payment link for placement fee via configured provider."""
        amount = validate_amount(placement_fee)
        provider = self._get_provider(provider)
        
        # Create payment link via UnifiedPaymentService
        result = self.unified_payment.create_payment_link(
            product_id=f"placement_fee:{match_id}",
            product_name=description,
            amount=float(amount),
            currency="USD",
            customer_email=customer_email,
            provider=provider,
        )
        
        if not result.success:
            log.warning("payment_link_creation_failed", provider=provider, 
                       error=result.error, match_id=match_id)
            raise RuntimeError(f"Payment link creation failed: {result.error}")

        # Register in canonical SalesLedger
        registration = self.ledger.register_sale(
            provider=provider,
            customer_key=customer_email or client_id,
            product_key=f"placement_fee:{match_id}",
            amount=str(amount),
            currency="USD",
            provider_ref=result.data.get("payment_link_id", ""),
            metadata={
                "match_id": match_id, 
                "client_id": client_id,
                "provider": provider
            },
        )
        if registration.duplicate:
            log.warning("placement_fee_duplicate", match_id=match_id, provider=provider)

        return MarketFeeResult(
            payment_id=result.data.get("payment_link_id") or result.data.get("payment_id"),
            checkout_url=result.data.get("payment_url") or result.data.get("checkout_url"),
            checkout_token=result.data.get("payment_link_id") or result.data.get("payment_link_id"),
            amount=amount,
            currency=result.data.get("currency", "USD"),
            status="pending",
            sale_intent_id=registration.intent.intent_id,
            duplicate=bool(registration.duplicate),
            raw=result.data,
        )

    async def charge_monthly_platform_fee(
        self,
        *,
        client_id: str,
        match_id: str,
        period: str | None = None,
        amount: Decimal | None = None,
        customer_email: str | None = None,
        va_id: str | None = None,
        provider: str | None = None,
    ) -> MarketFeeResult:
        """Bill the recurring monthly platform fee as a subscription."""
        validated = validate_amount(amount or self.monthly_fee)
        period = period or datetime.now(UTC).strftime("%Y-%m")
        provider = self._get_provider(provider)
        
        # Check if provider supports subscriptions
        if provider not in ("stripe", "lemonsqueezy"):
            log.warning("provider_does_not_support_subscriptions", 
                       provider=provider, fallback="stripe")
            provider = "stripe" if "stripe" in self.supported_providers else "lemonsqueezy"

        # Use UnifiedPaymentService for subscription
        result = self.unified_payment.create_subscription(
            product_id=f"platform_fee:{match_id}",
            product_name=f"Platform Fee {period}",
            amount=float(validated),
            billing_interval="month",
            customer_email=customer_email or f"client_{client_id}@va-matching.local",
            provider=provider,
        )
        
        if not result.success:
            log.error("subscription_creation_failed", provider=provider, 
                     error=result.error, match_id=match_id)
            raise RuntimeError(f"Subscription creation failed: {result.error}")
        
        registration = self.ledger.register_sale(
            provider=provider,
            customer_key=customer_email or client_id,
            product_key=f"platform_fee:{match_id}:{period}",
            amount=str(validated),
            currency="USD",
            provider_ref=result.data.get("subscription_id", ""),
            metadata={
                "match_id": match_id, 
                "client_id": client_id, 
                "period": period,
                "provider": provider
            },
        )
        if registration.duplicate:
            log.warning("platform_fee_duplicate", match_id=match_id, period=period, provider=provider)

        return MarketFeeResult(
            payment_id=result.data.get("subscription_id"),
            checkout_url=result.data.get("subscription_url"),
            checkout_token=result.data.get("subscription_id"),
            amount=validated,
            currency="USD",
            status=result.data.get("status", "active"),
            sale_intent_id=registration.intent.intent_id,
            duplicate=bool(registration.duplicate),
            raw=result.data,
        )

    # ── Confirmations / Ledger ────────────────────────────────────────

    def confirm_sale(
        self,
        sale_intent_id: str,
        *,
        source: str,
        evidence: str | None,
        amount: Decimal | None,
        status_hint: str | None = None,
    ) -> dict[str, Any]:
        """Record an independent confirmation in the canonical SalesLedger."""
        outcome = self.ledger.confirm(
            sale_intent_id,
            source,
            amount=str(amount) if amount is not None else None,
            evidence=evidence,
            status_hint=status_hint,
        )
        return {
            "intent_id": sale_intent_id,
            "status": getattr(outcome, "status", None) or getattr(outcome, "sale_status", ""),
            "outcomes": getattr(outcome, "summary", None) or "",
        }

    async def settle_payment(
        self,
        sale_intent_id: str,
        payment_id: str,
        *,
        source: str = "webhook",
        evidence: str | None = None,
        provider: str | None = None,
    ) -> dict[str, Any]:
        """Pull canonical provider status and record a ledger confirmation."""
        provider = self._get_provider(provider)
        
        # Use UnifiedPaymentService to get payment details
        details = await self.unified_payment.get_payment_details(
            payment_id=payment_id,
            provider=provider,
        )
        amount = None
        status_hint = None
        if details and details.get("status") == "succeeded":
            amount = Decimal(str(details.get("amount", 0))) / 100
            status_hint = "captured"
        
        return self.confirm_sale(
            sale_intent_id,
            source=source,
            evidence=evidence or payment_id,
            amount=amount,
            status_hint=status_hint or "captured",
        )

    # ── Refunds ────────────────────────────────────────────────────────

    async def refund_payment(
        self,
        *,
        sale_intent_id: str,
        payment_id: str,
        amount: Decimal | None = None,
        reason: str = "requested_by_customer",
        idempotency_key: str | None = None,
        provider: str | None = None,
    ) -> dict[str, Any]:
        """Canonical, idempotent, capped refund through provider + ledger."""
        provider = self._get_provider(provider)
        
        ledger_refund = self.ledger.request_refund(
            sale_intent_id,
            amount=str(amount) if amount is not None else None,
            idempotency_key=idempotency_key or f"refund:{payment_id}",
            reason=reason,
        )
        
        # Use UnifiedPaymentService for refund
        refund_result = self.unified_payment.refund_payment(
            payment_id=payment_id,
            amount=float(amount) if amount else None,
            reason=reason,
            provider=provider,
        )
        
        return {
            "refund_id": refund_result.data.get("refund_id") if refund_result.data else None,
            "payment_id": payment_id,
            "status": refund_result.data.get("status") if refund_result.data else "pending",
            "amount": float(amount) if amount else None,
            "ledger_status": getattr(ledger_refund, "status", ""),
            "ledger_id": getattr(ledger_refund, "refund_id", None),
        }

    # ── Webhooks ──────────────────────────────────────────────────────

    async def admit_webhook(self, payload: bytes, signature: str | None, provider: str | None = None) -> dict[str, Any]:
        """Verify signature (canonical), then admit via the WebhookGate.

        Returns the normalized event dict for platform dispatch; raises
        ``PermissionError`` on any rejection (verification, freshness or
        replay).
        """
        provider = self._get_provider(provider)
        text = payload.decode("utf-8", errors="replace")
        
        # Verify using UnifiedPaymentService
        headers = {"stripe-signature": signature} if signature else {}
        verified = self.unified_payment.verify_webhook(payload, headers, provider)
        if not verified:
            raise PermissionError(f"Invalid {provider} webhook signature")

        try:
            event = json.loads(text)
        except json.JSONDecodeError as exc:
            raise PermissionError("Malformed webhook payload") from exc

        event_id = extract_event_id(event) or ""
        verdict = self.gate.admit(provider=provider, event_id=event_id, occurred_at=event.get("created"))
        if verdict.rejected:
            raise PermissionError(f"Webhook rejected: {verdict.reason}")

        # Process webhook through UnifiedPaymentService (handles all providers)
        result = self.unified_payment.handle_webhook(event, provider)
        
        parsed = {
            "type": event.get("type"),
            "provider": provider,
            "data": event,
            "result": result.data if result.success else None,
            "error": result.error if not result.success else None,
        }
        parsed["gate_reason"] = verdict.reason
        parsed["duplicate"] = verdict.duplicate
        return parsed

    # ── VA Payout Onboarding (Stripe Connect) ────────────────────────

    def onboarding_stripe_service(self):
        """VA connected-account service for direct payouts (Stripe only)."""
        if not self.connect:
            raise RuntimeError("Stripe Connect not configured")
        return self.connect

    def create_va_connect_account(
        self, email: str, country: str = "US", metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create an Express connected account for a VA (Stripe only)."""
        if not self.connect:
            raise RuntimeError("Stripe Connect not configured")
        return self.connect.create_connect_account(
            email=email, country=country, metadata=metadata
        )

    def create_va_account_link(
        self, account_id: str
    ) -> dict[str, Any]:
        """Onboarding link for the VA to complete their payouts profile."""
        if not self.connect:
            raise RuntimeError("Stripe Connect not configured")
        return self.connect.create_account_link(
            account_id=account_id,
            refresh_url=str(marketplace_settings.CONNECT_REFRESH_URL),
            return_url=str(marketplace_settings.CONNECT_RETURN_URL),
        )


# ── Legacy compatibility ────────────────────────────────────────────

# These names are used by main.py and other modules
StripeConnectService = None  # Deprecated - use PaymentService.connect

def get_stripe_connect_service():
    """Deprecated - use PaymentService.connect"""
    from marketplace.payments import PaymentService
    svc = PaymentService()
    if not svc.connect:
        raise RuntimeError("Stripe Connect not configured")
    return svc.connect