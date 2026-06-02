"""Schema dataclass invariants."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from vmzrecon.schema import VN_TZ, MerchantOrder, Status, Wallet, WalletTxn


def _now() -> datetime:
    return datetime(2026, 5, 14, 9, 30, tzinfo=VN_TZ)


def test_wallet_enum_values():
    assert {w.value for w in Wallet} == {"VNPAY", "MOMO", "ZALOPAY"}


def test_status_enum_values():
    assert {s.value for s in Status} == {"SUCCESS", "FAILED", "PENDING"}


def test_vn_tz_is_utc_plus_7():
    offset = VN_TZ.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == 7 * 3600


def test_wallet_txn_happy_path():
    t = WalletTxn(
        wallet=Wallet.VNPAY,
        merchant_order_id="ORD-1",
        wallet_txn_id="VNP-1",
        amount_vnd=1_000_000,
        status=Status.SUCCESS,
        paid_at=_now(),
    )
    assert t.amount_vnd == 1_000_000


def test_wallet_txn_rejects_negative_amount():
    with pytest.raises(ValueError):
        WalletTxn(Wallet.MOMO, "ORD-1", "M-1", -1, Status.SUCCESS, _now())


def test_wallet_txn_rejects_empty_order_id():
    with pytest.raises(ValueError):
        WalletTxn(Wallet.MOMO, "", "M-1", 100, Status.SUCCESS, _now())


def test_wallet_txn_rejects_empty_txn_id():
    with pytest.raises(ValueError):
        WalletTxn(Wallet.MOMO, "ORD-1", "", 100, Status.SUCCESS, _now())


def test_wallet_txn_rejects_naive_datetime():
    naive = datetime(2026, 5, 14, 9, 30)
    with pytest.raises(ValueError):
        WalletTxn(Wallet.MOMO, "ORD-1", "M-1", 100, Status.SUCCESS, naive)


def test_merchant_order_happy_path():
    o = MerchantOrder(
        order_id="ORD-1",
        wallet=Wallet.MOMO,
        expected_amount_vnd=500_000,
        status=Status.SUCCESS,
        created_at=_now(),
    )
    assert o.expected_amount_vnd == 500_000


def test_merchant_order_rejects_negative_amount():
    with pytest.raises(ValueError):
        MerchantOrder("ORD-1", Wallet.MOMO, -1, Status.SUCCESS, _now())


def test_merchant_order_rejects_naive_datetime():
    with pytest.raises(ValueError):
        MerchantOrder("ORD-1", Wallet.MOMO, 1, Status.SUCCESS, datetime(2026, 1, 1, tzinfo=None))


def test_wallet_txn_accepts_utc_datetime():
    """Any tz-aware datetime is fine — we don't require UTC+7 specifically."""
    t = WalletTxn(
        Wallet.MOMO, "ORD-1", "M-1", 100, Status.SUCCESS, datetime(2026, 5, 14, tzinfo=timezone.utc)
    )
    assert t.paid_at.tzinfo is not None
