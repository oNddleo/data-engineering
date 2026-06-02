"""3-way matcher tests."""

from __future__ import annotations

from datetime import datetime

from vmzrecon.discrepancy import DiscrepancyKind
from vmzrecon.matcher import reconcile
from vmzrecon.schema import VN_TZ, MerchantOrder, Status, Wallet, WalletTxn


def _now() -> datetime:
    return datetime(2026, 5, 14, 9, 30, tzinfo=VN_TZ)


def _wallet_txn(
    *,
    wallet: Wallet = Wallet.VNPAY,
    order_id: str = "ORD-1",
    txn_id: str = "T-1",
    amount: int = 100_000,
    status: Status = Status.SUCCESS,
) -> WalletTxn:
    return WalletTxn(
        wallet=wallet,
        merchant_order_id=order_id,
        wallet_txn_id=txn_id,
        amount_vnd=amount,
        status=status,
        paid_at=_now(),
    )


def _merchant_order(
    *,
    wallet: Wallet = Wallet.VNPAY,
    order_id: str = "ORD-1",
    amount: int = 100_000,
    status: Status = Status.SUCCESS,
) -> MerchantOrder:
    return MerchantOrder(
        order_id=order_id,
        wallet=wallet,
        expected_amount_vnd=amount,
        status=status,
        created_at=_now(),
    )


def test_perfect_match_yields_no_discrepancy():
    assert reconcile([_merchant_order()], [_wallet_txn()]) == []


def test_wallet_only_detected():
    discrepancies = reconcile([], [_wallet_txn()])
    assert len(discrepancies) == 1
    d = discrepancies[0]
    assert d.kind is DiscrepancyKind.WALLET_ONLY
    assert d.wallet_amount == 100_000


def test_merchant_only_detected_when_success():
    discrepancies = reconcile([_merchant_order()], [])
    assert len(discrepancies) == 1
    assert discrepancies[0].kind is DiscrepancyKind.MERCHANT_ONLY


def test_merchant_only_not_reported_when_failed():
    """A merchant order in FAILED state has no money to settle — not a discrepancy."""
    discrepancies = reconcile([_merchant_order(status=Status.FAILED)], [])
    assert discrepancies == []


def test_merchant_only_not_reported_when_pending():
    discrepancies = reconcile([_merchant_order(status=Status.PENDING)], [])
    assert discrepancies == []


def test_amount_mismatch_detected():
    discrepancies = reconcile(
        [_merchant_order(amount=100_000)],
        [_wallet_txn(amount=99_000)],
    )
    assert len(discrepancies) == 1
    d = discrepancies[0]
    assert d.kind is DiscrepancyKind.AMOUNT_MISMATCH
    assert d.wallet_amount == 99_000
    assert d.merchant_amount == 100_000


def test_status_mismatch_detected():
    discrepancies = reconcile(
        [_merchant_order(status=Status.SUCCESS)],
        [_wallet_txn(status=Status.FAILED)],
    )
    assert len(discrepancies) == 1
    assert discrepancies[0].kind is DiscrepancyKind.STATUS_MISMATCH


def test_pending_on_wallet_side_suppresses_status_mismatch():
    """Settlement still in flight on wallet side — silent until tomorrow."""
    discrepancies = reconcile(
        [_merchant_order(status=Status.SUCCESS)],
        [_wallet_txn(status=Status.PENDING)],
    )
    assert discrepancies == []


def test_pending_on_merchant_side_suppresses_status_mismatch():
    discrepancies = reconcile(
        [_merchant_order(status=Status.PENDING)],
        [_wallet_txn(status=Status.SUCCESS)],
    )
    assert discrepancies == []


def test_amount_mismatch_preempts_status_mismatch():
    """If amounts disagree we don't bother emitting a separate STATUS_MISMATCH."""
    discrepancies = reconcile(
        [_merchant_order(amount=100_000, status=Status.SUCCESS)],
        [_wallet_txn(amount=99_000, status=Status.FAILED)],
    )
    assert len(discrepancies) == 1
    assert discrepancies[0].kind is DiscrepancyKind.AMOUNT_MISMATCH


def test_duplicate_in_wallet_emits_single_record():
    discrepancies = reconcile(
        [_merchant_order()],
        [_wallet_txn(txn_id="T-1"), _wallet_txn(txn_id="T-2")],
    )
    # Only the duplicate, no extra wallet/amount/status discrepancy.
    assert len(discrepancies) == 1
    assert discrepancies[0].kind is DiscrepancyKind.DUPLICATE_IN_WALLET


def test_duplicate_with_concurrent_mismatch_reports_both():
    """Duplicate + the (first) row also doesn't match merchant amount → 2 discrepancies."""
    discrepancies = reconcile(
        [_merchant_order(amount=100_000)],
        [
            _wallet_txn(amount=99_000, txn_id="T-1"),
            _wallet_txn(amount=99_000, txn_id="T-2"),
        ],
    )
    kinds = {d.kind for d in discrepancies}
    assert DiscrepancyKind.DUPLICATE_IN_WALLET in kinds
    assert DiscrepancyKind.AMOUNT_MISMATCH in kinds


def test_results_are_sorted_for_stable_diffing():
    """Sorted by (wallet, order_id, kind) — daily diff vs yesterday must be deterministic."""
    discrepancies = reconcile(
        [],
        [
            _wallet_txn(wallet=Wallet.ZALOPAY, order_id="Z-1"),
            _wallet_txn(wallet=Wallet.MOMO, order_id="M-2"),
            _wallet_txn(wallet=Wallet.MOMO, order_id="M-1"),
            _wallet_txn(wallet=Wallet.VNPAY, order_id="V-1"),
        ],
    )
    keys = [(d.wallet.value, d.order_id) for d in discrepancies]
    assert keys == sorted(keys)


def test_cross_wallet_same_order_id_does_not_collide():
    """ORD-1 on VNPay and ORD-1 on MoMo are independent keys."""
    discrepancies = reconcile(
        [
            _merchant_order(wallet=Wallet.VNPAY, order_id="ORD-1", amount=100_000),
            _merchant_order(wallet=Wallet.MOMO, order_id="ORD-1", amount=100_000),
        ],
        [
            _wallet_txn(wallet=Wallet.VNPAY, order_id="ORD-1", amount=100_000),
            _wallet_txn(wallet=Wallet.MOMO, order_id="ORD-1", amount=100_000),
        ],
    )
    assert discrepancies == []
