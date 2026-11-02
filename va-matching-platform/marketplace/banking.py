"""
Marketplace money book — thin adapter over the canonical SalesLedger.

Every fee/refund/claim event lands in the canonical, append-only,
multi-confirmation `shared.payments.SalesLedger` (env: ``PAYMENT_LEDGER_DB``).
This module only provides marketplace-shaped helpers:

    ledger = MarketLedger()
    ledger.record_fee(client_id, match_id, "placement_fee", "500.00",
                      provider_ref="pi_123")
    ledger.confirm(sale_intent_id, "webhook", evidence="evt_1")
    ledger.refund(sale_intent_id, idempotency_key="r-1", reason="...")
    ledger.summary()          # window totals for revenue reporting
    ledger.accounting_rows()  # journal rows for export/audit
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

import structlog

from shared.payments.sales_ledger import SaleStatus, get_sales_ledger

__all__ = ["MarketLedger", "FEE_KINDS", "get_market_ledger"]

log = structlog.get_logger(__name__)

FEE_KINDS = ("placement_fee", "platform_fee")


class MarketLedger:
    """Marketplace fee bookkeeping delegated to the canonical SalesLedger."""

    def __init__(self, db_path: str | None = None):
        # Canonical ledger already honors PAYMENT_LEDGER_DB from env;
        # explicit db_path is only for tests/short-lived books.
        self._ledger = get_sales_ledger(db_path) if db_path else get_sales_ledger()

    # ── registration ────────────────────────────────────────────────────

    def record_fee(
        self,
        client_id: str,
        match_id: str,
        fee_kind: str,
        amount: Any,
        *,
        customer_key: str | None = None,
        provider: str = "stripe",
        provider_ref: str | None = None,
        period: str | None = None,
        currency: str = "USD",
    ) -> dict[str, Any]:
        """Register a placement or monthly platform fee on the ledger.

        Identical (client, fee-kind, amount) within the duplicate window
        returns the existing intent flagged ``duplicate`` (canonical guard).
        """
        if fee_kind not in FEE_KINDS:
            raise ValueError(f"unknown fee kind {fee_kind!r}")

        product_key = f"{fee_kind}:{match_id}"
        if fee_kind == "platform_fee" and period:
            product_key = f"{fee_kind}:{match_id}:{period}"

        registration = self._ledger.register_sale(
            provider=provider,
            customer_key=customer_key or client_id,
            product_key=product_key,
            amount=str(amount),
            currency=currency,
            provider_ref=provider_ref,
            metadata={
                "fee_kind": fee_kind,
                "match_id": match_id,
                "client_id": client_id,
                "period": period or "",
            },
        )
        registration_dict: dict[str, Any] = {
            "intent_id": registration.intent.intent_id,
            "status": registration.intent.status.value,
            "duplicate": bool(registration.duplicate),
            "product_key": product_key,
        }
        if registration.duplicate:
            log.warning(
                "market_ledger.duplicate_fee",
                fee_kind=fee_kind,
                match_id=match_id,
                intent_id=registration.intent.intent_id,
            )
        return registration_dict

    # ── confirmations ───────────────────────────────────────────────────

    def confirm(
        self,
        intent_id: str,
        source: str,
        *,
        evidence: str | None = None,
        amount: Any = None,
        status_hint: str | SaleStatus | None = None,
    ) -> dict[str, Any]:
        """Record one independent confirmation (multi-source required)."""
        outcome = self._ledger.confirm(
            intent_id,
            source,
            amount=str(amount) if amount is not None else None,
            evidence=evidence,
            status_hint=status_hint,
        )
        return {
            "intent_id": intent_id,
            "status": getattr(outcome, "sale_status", getattr(outcome, "status", "")),
            "outcomes": getattr(outcome, "details", None),
        }

    def get_intent(self, intent_id: str) -> dict[str, Any]:
        return self._ledger.get_intent(intent_id).to_dict()

    # ── refunds / disputes ──────────────────────────────────────────────

    def refund(
        self,
        intent_id: str,
        *,
        idempotency_key: str | None = None,
        amount: Any = None,
        reason: str | None = None,
        forced: bool = False,
        claim_ref: str | None = None,
    ) -> dict[str, Any]:
        """Idempotent, cap-guarded refund (canonical)."""
        record = self._ledger.request_refund(
            intent_id,
            amount=str(amount) if amount is not None else None,
            idempotency_key=idempotency_key or f"refund:{uuid4()}",
            reason=reason,
            forced=forced,
            claim_ref=claim_ref,
        )
        return {
            "refund_id": record.refund_id,
            "intent_id": intent_id,
            "status": record.status,
            "amount": str(record.amount),
            "duplicate": getattr(record, "duplicate", False),
        }

    # ── reporting ───────────────────────────────────────────────────────

    def summary(self, **window: Any) -> dict[str, Any]:
        """Window totals (sales, refunds, holds, claims) from the canonical ledger."""
        return self._ledger.summary(**window)

    def accounting_rows(self, **window: Any) -> list[dict[str, Any]]:
        """Append-only journal rows for export/audit."""
        return self._ledger.accounting_rows(**window)

    def reconcile(self, settlement_rows: list[dict[str, Any]], **window: Any) -> dict[str, Any]:
        """Reconcile a settlement export against the sale journal."""
        return self._ledger.reconcile(settlement_rows, **window)

    def blocked_amounts(self) -> dict[str, Any]:
        return self._ledger.blocked_amounts()


_market_ledger: MarketLedger | None = None


def get_market_ledger() -> MarketLedger:
    """Cached marketplace ledger instance."""
    global _market_ledger
    if _market_ledger is None:
        _market_ledger = MarketLedger()
    return _market_ledger
