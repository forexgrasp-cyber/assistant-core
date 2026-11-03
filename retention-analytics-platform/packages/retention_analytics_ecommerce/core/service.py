"""Ecommerce core service: products, orders, cart.

Actions: place_order, abandon_cart, recover_cart. A cart-abandonment workflow
can call core.abandon_cart then engagement.email.send to recover the sale.

Orders and carts are persisted per tenant, so the retention analytics that
consume them are computed from real records rather than in-memory state.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import structlog
from retention_analytics_core.repository import new_id, repository_for
from retention_analytics_engagement.base import EngagementService

logger = structlog.get_logger(__name__)


class EcommerceCoreService(EngagementService):
    def __init__(self, registry, version: str = "0.1.0") -> None:
        super().__init__("ecommerce.core", registry, version)
        self.register_action("place_order", self._place_order)
        self.register_action("abandon_cart", self._abandon_cart)
        self.register_action("recover_cart", self._recover_cart)

    def _tenant(self, payload: dict[str, Any]) -> str:
        return str(payload.get("tenant_id") or "default")

    async def _place_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        customer_email = payload.get("customer_email")
        total = payload.get("total")
        items = payload.get("items", [])
        tenant_id = self._tenant(payload)

        if not customer_email:
            return self.fail("customer_email is required")

        amount = _to_decimal(total)
        if amount is None:
            return self.fail("total must be a number")

        order_id = new_id("ord")
        order = {
            "order_id": order_id,
            "customer_email": customer_email,
            "total": str(amount),
            "items": items,
            "status": "placed",
            "tenant_id": tenant_id,
            "placed_at": datetime.now(UTC).isoformat(),
        }
        await repository_for("orders", tenant_id).save(order_id, order)
        logger.info(
            "order.place",
            order_id=order_id,
            customer_email=customer_email,
            total=str(amount),
            tenant_id=tenant_id,
        )
        return {
            "status": "placed",
            "order_id": order_id,
            "customer_email": customer_email,
            "total": str(amount),
            "items": items,
        }

    async def _abandon_cart(self, payload: dict[str, Any]) -> dict[str, Any]:
        customer_email = payload.get("customer_email")
        cart_id = payload.get("cart_id") or new_id("cart")
        tenant_id = self._tenant(payload)

        if not customer_email:
            return self.fail("customer_email is required")

        cart = {
            "cart_id": cart_id,
            "customer_email": customer_email,
            "total": str(_to_decimal(payload.get("total")) or Decimal("0")),
            "items": payload.get("items", []),
            "status": "abandoned",
            "tenant_id": tenant_id,
            "abandoned_at": datetime.now(UTC).isoformat(),
        }
        await repository_for("carts", tenant_id).save(str(cart_id), cart)
        logger.info(
            "cart.abandon",
            cart_id=cart_id,
            customer_email=customer_email,
            tenant_id=tenant_id,
        )
        return {
            "status": "abandoned",
            "cart_id": cart_id,
            "customer_email": customer_email,
        }

    async def _recover_cart(self, payload: dict[str, Any]) -> dict[str, Any]:
        cart_id = payload.get("cart_id")
        discount = payload.get("discount")
        tenant_id = self._tenant(payload)
        if not cart_id:
            return self.fail("cart_id is required")

        repo = repository_for("carts", tenant_id)
        cart = await repo.load(str(cart_id))
        if cart is None:
            return self.fail("unknown cart_id")

        cart["status"] = "recovery_offered"
        cart["discount"] = discount
        cart["recovery_offered_at"] = datetime.now(UTC).isoformat()
        await repo.save(str(cart_id), cart)
        logger.info("cart.recover", cart_id=cart_id, discount=discount, tenant_id=tenant_id)
        return {"status": "recovery_offered", "cart_id": cart_id, "discount": discount}


def _to_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


__all__ = ["EcommerceCoreService"]
