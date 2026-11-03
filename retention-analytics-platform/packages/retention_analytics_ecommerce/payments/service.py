"""Payments service (provider-agnostic money path).

The platform never imports a payment SDK directly (PRODUCTION_STANDARDS.md
L13). Providers are resolved through the canonical registry
(``shared.payments.registry``), which returns a provider implementing the
canonical ``BasePaymentProvider`` contract. Switching provider is a
configuration change, not a code change.

Actions: list_providers, create_payment, get_payment, refund, verify_webhook.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

import structlog
from retention_analytics_core.repository import new_id, repository_for
from retention_analytics_engagement.base import EngagementService

logger = structlog.get_logger(__name__)


class PaymentService(EngagementService):
    def __init__(self, registry, version: str = "0.1.0") -> None:
        super().__init__("payments", registry, version)
        self.register_action("list_providers", self._list_providers)
        self.register_action("create_payment", self._create_payment)
        self.register_action("get_payment", self._get_payment)
        self.register_action("refund", self._refund)
        self.register_action("verify_webhook", self._verify_webhook)
        self._providers: dict[str, Any] = {}

    def _tenant(self, payload: dict[str, Any]) -> str:
        return str(payload.get("tenant_id") or "default")

    def _provider_name(self, payload: dict[str, Any]) -> str:
        from retention_analytics_shared_config import get_settings

        requested = payload.get("provider")
        if requested:
            return str(requested)
        return get_settings().payment_provider

    def _get_provider(self, name: str) -> Any:
        if name not in self._providers:
            from shared.payments.registry import build_provider

            self._providers[name] = build_provider(name)
        return self._providers[name]

    async def _list_providers(self, payload: dict[str, Any]) -> dict[str, Any]:
        from shared.payments.registry import available_providers, provider_status

        return {
            "status": "ok",
            "providers": available_providers(),
            "status_by_provider": provider_status(),
        }

    async def _create_payment(self, payload: dict[str, Any]) -> dict[str, Any]:
        from shared.payments.base import PaymentRequest

        tenant_id = self._tenant(payload)
        provider_name = self._provider_name(payload)
        amount = payload.get("amount")

        if amount is None:
            return self.fail("amount is required")
        try:
            amount_value = Decimal(str(amount))
        except (InvalidOperation, ValueError):
            return self.fail("amount must be a number")
        if amount_value <= 0:
            return self.fail("amount must be greater than zero")

        order_id = str(payload.get("order_id") or new_id("ord"))
        request = PaymentRequest(
            amount=amount_value,
            currency=str(payload.get("currency") or "USD"),
            order_id=order_id,
            customer_email=payload.get("customer_email"),
            customer_name=payload.get("customer_name"),
            description=payload.get("description"),
            metadata={"tenant_id": tenant_id},
            return_url=payload.get("return_url"),
            cancel_url=payload.get("cancel_url"),
            webhook_url=payload.get("webhook_url"),
        )

        try:
            provider = self._get_provider(provider_name)
            response = await provider.create_payment(request)
        except KeyError:
            return self.fail(f"unknown payment provider '{provider_name}'")
        except Exception as exc:  # noqa: BLE001 - provider boundary
            logger.error("payment.create_failed", provider=provider_name, error=str(exc))
            return self.fail(f"payment provider error: {exc}")

        payment_id = str(response.payment_id)
        record = {
            "payment_id": payment_id,
            "provider": str(response.provider),
            "status": str(response.status),
            "amount": str(response.amount),
            "currency": response.currency,
            "order_id": order_id,
            "tenant_id": tenant_id,
            "checkout_url": response.checkout_url,
            "created_at": datetime_now(),
        }
        await repository_for("payments", tenant_id).save(payment_id, record)

        logger.info(
            "payment.created",
            payment_id=payment_id,
            provider=str(response.provider),
            amount=str(response.amount),
            tenant_id=tenant_id,
        )
        return {
            "status": "created",
            "payment_id": payment_id,
            "provider": str(response.provider),
            "payment_status": str(response.status),
            "amount": str(response.amount),
            "currency": response.currency,
            "checkout_url": response.checkout_url,
        }

    async def _get_payment(self, payload: dict[str, Any]) -> dict[str, Any]:
        tenant_id = self._tenant(payload)
        payment_id = payload.get("payment_id")
        if not payment_id:
            return self.fail("payment_id is required")
        record = await repository_for("payments", tenant_id).load(str(payment_id))
        if record is None:
            return self.fail("unknown payment_id")
        return {"status": "found", "payment": record}

    async def _refund(self, payload: dict[str, Any]) -> dict[str, Any]:
        from shared.payments.base import RefundRequest

        tenant_id = self._tenant(payload)
        payment_id = payload.get("payment_id")
        if not payment_id:
            return self.fail("payment_id is required")

        repo = repository_for("payments", tenant_id)
        record = await repo.load(str(payment_id))
        if record is None:
            return self.fail("unknown payment_id")

        amount = payload.get("amount")
        amount_value: Decimal | None = None
        if amount is not None:
            try:
                amount_value = Decimal(str(amount))
            except (InvalidOperation, ValueError):
                return self.fail("amount must be a number")

        provider_name = str(record.get("provider") or self._provider_name(payload))
        try:
            provider = self._get_provider(provider_name)
            response = await provider.create_refund(
                RefundRequest(
                    payment_id=str(payment_id),
                    amount=amount_value,
                    reason=payload.get("reason"),
                    metadata={"tenant_id": tenant_id},
                )
            )
        except KeyError:
            return self.fail(f"unknown payment provider '{provider_name}'")
        except Exception as exc:  # noqa: BLE001 - provider boundary
            logger.error("payment.refund_failed", provider=provider_name, error=str(exc))
            return self.fail(f"payment provider error: {exc}")

        record["refund_id"] = response.refund_id
        record["refund_status"] = str(response.status)
        record["refunded_amount"] = str(response.amount)
        await repo.save(str(payment_id), record)

        logger.info(
            "payment.refunded",
            payment_id=payment_id,
            refund_id=response.refund_id,
            amount=str(response.amount),
            tenant_id=tenant_id,
        )
        return {
            "status": "refunded",
            "payment_id": payment_id,
            "refund_id": response.refund_id,
            "refund_status": str(response.status),
            "amount": str(response.amount),
        }

    async def _verify_webhook(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Verify a provider webhook signature through the canonical provider."""
        tenant_id = self._tenant(payload)
        provider_name = self._provider_name(payload)
        event = payload.get("event") or {}
        signature = payload.get("signature")

        try:
            provider = self._get_provider(provider_name)
            valid = await provider.verify_webhook(event, signature)
        except KeyError:
            return self.fail(f"unknown payment provider '{provider_name}'")
        except Exception as exc:  # noqa: BLE001 - provider boundary
            logger.error("payment.webhook_verify_failed", provider=provider_name, error=str(exc))
            return self.fail(f"payment provider error: {exc}")

        if not valid:
            return self.fail("invalid webhook signature")

        event_id = str(event.get("id") or new_id("evt"))
        record = {
            "event_id": event_id,
            "provider": provider_name,
            "event_type": str(event.get("type") or "unknown"),
            "payload": event,
            "tenant_id": tenant_id,
            "received_at": datetime_now(),
        }
        await repository_for("payment_webhooks", tenant_id).save(event_id, record)
        logger.info(
            "payment.webhook_verified",
            event_id=event_id,
            provider=provider_name,
            tenant_id=tenant_id,
        )
        return {"status": "verified", "event_id": event_id, "provider": provider_name}


def datetime_now() -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).isoformat()


__all__ = ["PaymentService"]
