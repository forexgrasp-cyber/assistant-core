"""Subscription service (money path).

Actions: create, cancel, reactivate, dunning. Workflows react to subscription
events (past_due -> dunning email, cancelled -> win-back email).

The lifecycle is persisted per tenant and entitlements are granted/revoked
through the canonical entitlements service
(``shared.billing.entitlements_service.EntitlementsService``), so a cancelled
subscription actually removes access instead of only logging.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import structlog
from retention_analytics_core.repository import data_root, new_id, repository_for
from retention_analytics_engagement.base import EngagementService

logger = structlog.get_logger(__name__)

# Entitlements granted by an active subscription.
SUBSCRIPTION_ENTITLEMENTS = (
    "platform.api_access",
    "platform.workflows",
    "platform.reports",
    "platform.support",
)


class SubscriptionService(EngagementService):
    def __init__(self, registry, version: str = "0.1.0") -> None:
        super().__init__("subscriptions", registry, version)
        self.register_action("create", self._create)
        self.register_action("cancel", self._cancel)
        self.register_action("reactivate", self._reactivate)
        self.register_action("dunning", self._dunning)
        self.register_action("get", self._get)
        self._entitlements: Any = None

    def _get_entitlements(self) -> Any:
        if self._entitlements is None:
            from shared.billing.entitlements_service import EntitlementsService

            self._entitlements = EntitlementsService(str(data_root() / "billing" / "entitlements.db"))
        return self._entitlements

    def _tenant(self, payload: dict[str, Any]) -> str:
        return str(payload.get("tenant_id") or "default")

    async def _create(self, payload: dict[str, Any]) -> dict[str, Any]:
        plan = payload.get("plan")
        customer_email = payload.get("customer_email")
        tenant_id = self._tenant(payload)

        if not plan or not customer_email:
            return self.fail("plan and customer_email are required")

        subscription_id = new_id("sub")
        subscription = {
            "subscription_id": subscription_id,
            "plan": plan,
            "customer_email": customer_email,
            "status": "active",
            "tenant_id": tenant_id,
            "created_at": datetime.now(UTC).isoformat(),
            "dunning_attempts": 0,
        }
        await repository_for("subscriptions", tenant_id).save(subscription_id, subscription)

        entitlements = self._get_entitlements()
        for entitlement in SUBSCRIPTION_ENTITLEMENTS:
            entitlements.grant(
                account=tenant_id,
                entitlement=entitlement,
                source="subscription",
                reference=subscription_id,
                tier=str(plan),
            )

        logger.info(
            "subscription.create",
            subscription_id=subscription_id,
            plan=plan,
            customer_email=customer_email,
            tenant_id=tenant_id,
        )
        return {
            "status": "active",
            "subscription_id": subscription_id,
            "plan": plan,
            "customer_email": customer_email,
        }

    async def _cancel(self, payload: dict[str, Any]) -> dict[str, Any]:
        subscription_id = payload.get("subscription_id")
        tenant_id = self._tenant(payload)
        if not subscription_id:
            return self.fail("subscription_id is required")

        repo = repository_for("subscriptions", tenant_id)
        subscription = await repo.load(str(subscription_id))
        if subscription is None:
            return self.fail("unknown subscription_id")

        subscription["status"] = "cancelled"
        subscription["cancelled_at"] = datetime.now(UTC).isoformat()
        await repo.save(str(subscription_id), subscription)

        entitlements = self._get_entitlements()
        for entitlement in SUBSCRIPTION_ENTITLEMENTS:
            entitlements.revoke(account=tenant_id, entitlement=entitlement)

        logger.info("subscription.cancel", subscription_id=subscription_id, tenant_id=tenant_id)
        return {"status": "cancelled", "subscription_id": subscription_id}

    async def _reactivate(self, payload: dict[str, Any]) -> dict[str, Any]:
        subscription_id = payload.get("subscription_id")
        tenant_id = self._tenant(payload)
        if not subscription_id:
            return self.fail("subscription_id is required")

        repo = repository_for("subscriptions", tenant_id)
        subscription = await repo.load(str(subscription_id))
        if subscription is None:
            return self.fail("unknown subscription_id")

        subscription["status"] = "active"
        subscription["reactivated_at"] = datetime.now(UTC).isoformat()
        await repo.save(str(subscription_id), subscription)

        entitlements = self._get_entitlements()
        for entitlement in SUBSCRIPTION_ENTITLEMENTS:
            entitlements.grant(
                account=tenant_id,
                entitlement=entitlement,
                source="subscription",
                reference=str(subscription_id),
                tier=str(subscription.get("plan", "")),
            )

        logger.info("subscription.reactivate", subscription_id=subscription_id, tenant_id=tenant_id)
        return {"status": "active", "subscription_id": subscription_id}

    async def _dunning(self, payload: dict[str, Any]) -> dict[str, Any]:
        subscription_id = payload.get("subscription_id")
        customer_email = payload.get("customer_email")
        tenant_id = self._tenant(payload)
        if not subscription_id:
            return self.fail("subscription_id is required")

        repo = repository_for("subscriptions", tenant_id)
        subscription = await repo.load(str(subscription_id))
        if subscription is None:
            return self.fail("unknown subscription_id")

        subscription["status"] = "past_due"
        subscription["dunning_attempts"] = int(subscription.get("dunning_attempts", 0)) + 1
        subscription["last_dunning_at"] = datetime.now(UTC).isoformat()
        await repo.save(str(subscription_id), subscription)

        logger.info(
            "subscription.dunning",
            subscription_id=subscription_id,
            customer_email=customer_email,
            attempts=subscription["dunning_attempts"],
            tenant_id=tenant_id,
        )
        return {
            "status": "dunning_started",
            "subscription_id": subscription_id,
            "customer_email": customer_email,
            "attempts": subscription["dunning_attempts"],
        }

    async def _get(self, payload: dict[str, Any]) -> dict[str, Any]:
        subscription_id = payload.get("subscription_id")
        tenant_id = self._tenant(payload)
        if not subscription_id:
            return self.fail("subscription_id is required")
        subscription = await repository_for("subscriptions", tenant_id).load(str(subscription_id))
        if subscription is None:
            return self.fail("unknown subscription_id")
        return {"status": "found", "subscription": subscription}


__all__ = ["SUBSCRIPTION_ENTITLEMENTS", "SubscriptionService"]
