"""MarketLedger (canonical SalesLedger adapter) — SQLite-backed, no Stripe."""

from __future__ import annotations

from decimal import Decimal
from shared.payments.sales_ledger import SaleStatus

from marketplace.banking import MarketLedger


def test_record_fee_and_duplicate_guard(tmp_path):
    ledger = MarketLedger(db_path=str(tmp_path / "ledger.db"))

    reg = ledger.record_fee(
        "client-1", "match-1", "placement_fee", Decimal("950.00"),
        provider_ref="pi_test_1",
    )
    assert reg["intent_id"]
    assert reg["duplicate"] is False
    assert reg["product_key"] == "placement_fee:match-1"

    # Identical (client, fee-kind, amount) within window -> duplicate flag
    reg2 = ledger.record_fee(
        "client-1", "match-1", "placement_fee", Decimal("950.00"),
        provider_ref="pi_test_1",
    )
    assert reg2["duplicate"] is True

    summary = ledger.summary()
    assert summary["sales"]["count"] == 1
    assert summary["sales"]["gross"] == "950.00"


def test_platform_fee_period_keying(tmp_path):
    ledger = MarketLedger(db_path=str(tmp_path / "ledger.db"))
    a = ledger.record_fee(
        "client-2", "match-2", "platform_fee", Decimal("200.00"),
        period="2026-10",
    )
    b = ledger.record_fee(
        "client-2", "match-2", "platform_fee", Decimal("200.00"),
        period="2026-11",
    )
    assert a["duplicate"] is False
    assert b["duplicate"] is False
    assert a["product_key"] == "platform_fee:match-2:2026-10"
    assert b["product_key"] == "platform_fee:match-2:2026-11"


def test_unknown_fee_kind_rejected(tmp_path):
    ledger = MarketLedger(db_path=str(tmp_path / "ledger.db"))
    try:
        ledger.record_fee("c", "m", "bogus_fee", Decimal("1.00"))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_confirm_then_refund(tmp_path):
    ledger = MarketLedger(db_path=str(tmp_path / "ledger.db"))
    reg = ledger.record_fee(
        "client-2", "match-2", "platform_fee", Decimal("200.00"),
        period="2026-10", provider_ref="pi_test_2",
    )
    intent_id = reg["intent_id"]

    confirmed = ledger.confirm(
        intent_id, source="webhook", amount=Decimal("200.00"), status_hint="captured"
    )
    assert confirmed["intent_id"] == intent_id

    refund = ledger.refund(intent_id, amount=Decimal("200.00"), reason="test")
    assert refund["amount"] == "200.00"
    assert refund["duplicate"] is False


def test_accounting_rows(tmp_path):
    ledger = MarketLedger(db_path=str(tmp_path / "ledger.db"))
    ledger.record_fee(
        "client-3", "match-3", "placement_fee", Decimal("1200.00"),
        provider_ref="pi_test_3",
    )
    rows = ledger.accounting_rows(limit=10)
    assert len(rows) == 1
