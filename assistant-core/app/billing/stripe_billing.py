"""Stripe Billing for business assistants."""

from __future__ import annotations

import os
import stripe
from dataclasses import dataclass
from typing import Any

# Pricing tiers
TIERS = {
    "starter": {
        "price_monthly": 49,
        "calls_included": 100,
        "features": ["voice", "sms", "booking", "missed_call_recovery"],
        "stripe_price_id": os.getenv("STRIPE_PRICE_STARTER"),
    },
    "pro": {
        "price_monthly": 149,
        "calls_included": 500,
        "features": ["voice", "sms", "booking", "missed_call_recovery", "calendar_sync", "whatsapp", "widget"],
        "stripe_price_id": os.getenv("STRIPE_PRICE_PRO"),
    },
    "enterprise": {
        "price_monthly": 499,
        "calls_included": 2000,
        "features": ["voice", "sms", "booking", "missed_call_recovery", "calendar_sync", "whatsapp", "widget", "custom_integrations", "dedicated_support"],
        "stripe_price_id": os.getenv("STRIPE_PRICE_ENTERPRISE"),
    },
}


@dataclass
class BillingConfig:
    stripe_secret_key: str
    stripe_webhook_secret: str
    success_url: str
    cancel_url: str


class StripeBilling:
    """Stripe billing for business assistants."""

    def __init__(self, config: BillingConfig):
        self.config = config
        stripe.api_key = config.stripe_secret_key

    def create_customer(self, email: str, name: str, metadata: dict | None = None) -> str:
        """Create Stripe customer."""
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata=metadata or {},
        )
        return customer.id

    def create_subscription(
        self,
        customer_id: str,
        tier: str,
        metadata: dict | None = None,
    ) -> dict:
        """Create subscription for a tier."""
        tier_config = TIERS.get(tier)
        if not tier_config:
            raise ValueError(f"Unknown tier: {tier}")

        price_id = tier_config.get("stripe_price_id")
        if not price_id:
            raise ValueError(f"No Stripe price ID configured for tier: {tier}")

        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{"price": price_id}],
            metadata=metadata or {},
            payment_behavior="default_incomplete",
            expand=["latest_invoice.payment_intent"],
        )
        return {
            "subscription_id": subscription.id,
            "client_secret": subscription.latest_invoice.payment_intent.client_secret,
            "status": subscription.status,
        }

    def cancel_subscription(self, subscription_id: str) -> bool:
        """Cancel a subscription."""
        try:
            stripe.Subscription.delete(subscription_id)
            return True
        except Exception:
            return False

    def create_checkout_session(
        self,
        customer_id: str,
        tier: str,
        success_url: str | None = None,
        cancel_url: str | None = None,
    ) -> dict:
        """Create Stripe Checkout session for subscription."""
        tier_config = TIERS.get(tier)
        if not tier_config:
            raise ValueError(f"Unknown tier: {tier}")

        price_id = tier_config.get("stripe_price_id")
        if not price_id:
            raise ValueError(f"No Stripe price ID configured for tier: {tier}")

        session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url or self.config.success_url,
            cancel_url=cancel_url or self.config.cancel_url,
        )
        return {"session_id": session.id, "url": session.url}

    def handle_webhook(self, payload: bytes, sig_header: str) -> dict:
        """Handle Stripe webhook."""
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.config.stripe_webhook_secret
            )
            return {"event": event.type, "data": event.data.object}
        except stripe.error.SignatureVerificationError:
            raise ValueError("Invalid signature")

    def get_tier_info(self, tier: str) -> dict:
        """Get tier information."""
        return TIERS.get(tier, {})

    def list_tiers(self) -> dict:
        """List all available tiers."""
        return TIERS