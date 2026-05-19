"""AML detection: CTR, structuring, high-velocity."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from vnbank.aml import (
    AMLKind,
    find_ctr,
    find_high_velocity,
    find_structuring,
)
from vnbank.schema import (
    CTR_THRESHOLD_VND,
    VN_TZ,
    TxnDirection,
    TxnKind,
    TxnStatus,
)

from ._fixtures import make_txn

# ---------- CTR -------------------------------------------------------------


def test_ctr_fires_on_large_cash_deposit() -> None:
    """One cash deposit at the threshold fires CTR."""
    t = make_txn(
        kind=TxnKind.CASH_DEPOSIT,
        direction=TxnDirection.CREDIT,
        amount_vnd=CTR_THRESHOLD_VND,
    )
    findings = find_ctr([t])
    assert len(findings) == 1
    assert findings[0].kind is AMLKind.CTR_CASH_THRESHOLD


def test_ctr_silent_below_threshold() -> None:
    t = make_txn(
        kind=TxnKind.CASH_DEPOSIT,
        direction=TxnDirection.CREDIT,
        amount_vnd=CTR_THRESHOLD_VND - 1,
    )
    assert find_ctr([t]) == []


def test_ctr_aggregates_per_day() -> None:
    """Two cash deposits summing to ≥ threshold fire CTR."""
    txns = [
        make_txn(
            txn_id=f"T-{i}",
            kind=TxnKind.CASH_DEPOSIT,
            direction=TxnDirection.CREDIT,
            amount_vnd=200_000_000,
            occurred_at=datetime(2026, 5, 18, 10 + i, 0, tzinfo=VN_TZ),
        )
        for i in range(2)
    ]
    findings = find_ctr(txns)
    assert len(findings) == 1
    assert findings[0].metric == 400_000_000


def test_ctr_includes_withdrawals() -> None:
    """Cash withdrawals also count toward the threshold."""
    t = make_txn(
        kind=TxnKind.CASH_WITHDRAWAL,
        direction=TxnDirection.DEBIT,
        amount_vnd=CTR_THRESHOLD_VND + 100_000,
    )
    findings = find_ctr([t])
    assert len(findings) == 1


def test_ctr_ignores_non_cash() -> None:
    """Transfers are not cash transactions."""
    t = make_txn(
        kind=TxnKind.INTERBANK_TRANSFER,
        amount_vnd=CTR_THRESHOLD_VND * 2,
    )
    assert find_ctr([t]) == []


def test_ctr_ignores_pending() -> None:
    """Only POSTED transactions count."""
    t = make_txn(
        kind=TxnKind.CASH_DEPOSIT,
        direction=TxnDirection.CREDIT,
        amount_vnd=CTR_THRESHOLD_VND,
        status=TxnStatus.PENDING,
    )
    assert find_ctr([t]) == []


# ---------- Structuring -----------------------------------------------------


def test_structuring_fires_on_split_deposits() -> None:
    """4 deposits of 90M on one day = STRUCTURING."""
    txns = [
        make_txn(
            txn_id=f"T-{i}",
            kind=TxnKind.CASH_DEPOSIT,
            direction=TxnDirection.CREDIT,
            amount_vnd=90_000_000,
            occurred_at=datetime(2026, 5, 18, 10 + i, 0, tzinfo=VN_TZ),
        )
        for i in range(4)
    ]
    findings = find_structuring(txns)
    assert len(findings) == 1
    assert findings[0].kind is AMLKind.STRUCTURING
    assert findings[0].metric == 360_000_000


def test_structuring_silent_below_threshold_total() -> None:
    """3 small deposits not summing to CTR don't fire."""
    txns = [
        make_txn(
            txn_id=f"T-{i}",
            kind=TxnKind.CASH_DEPOSIT,
            direction=TxnDirection.CREDIT,
            amount_vnd=10_000_000,
            occurred_at=datetime(2026, 5, 18, 10 + i, 0, tzinfo=VN_TZ),
        )
        for i in range(3)
    ]
    assert find_structuring(txns) == []


def test_structuring_silent_on_fewer_than_threshold() -> None:
    """1 single large sub-CTR deposit is not structuring."""
    t = make_txn(
        kind=TxnKind.CASH_DEPOSIT,
        direction=TxnDirection.CREDIT,
        amount_vnd=290_000_000,
    )
    assert find_structuring([t]) == []


def test_structuring_excludes_at_or_above_ctr() -> None:
    """A deposit ≥ CTR is not structuring (it's just a CTR)."""
    txns = [
        make_txn(
            txn_id=f"T-{i}",
            kind=TxnKind.CASH_DEPOSIT,
            direction=TxnDirection.CREDIT,
            amount_vnd=CTR_THRESHOLD_VND,
            occurred_at=datetime(2026, 5, 18, 10 + i, 0, tzinfo=VN_TZ),
        )
        for i in range(3)
    ]
    assert find_structuring(txns) == []


def test_structuring_validates_param() -> None:
    with pytest.raises(ValueError, match="min_structuring_txns"):
        find_structuring([], min_structuring_txns=1)


# ---------- High Velocity ---------------------------------------------------


def test_velocity_fires_on_burst() -> None:
    base = datetime(2026, 5, 18, 14, 0, tzinfo=VN_TZ)
    txns = [
        make_txn(
            txn_id=f"T-{i}",
            kind=TxnKind.INTERBANK_TRANSFER,
            direction=TxnDirection.DEBIT,
            amount_vnd=1_000_000,
            occurred_at=base + timedelta(seconds=i * 30),
        )
        for i in range(60)
    ]
    findings = find_high_velocity(txns)
    assert len(findings) == 1
    assert findings[0].kind is AMLKind.HIGH_VELOCITY
    assert findings[0].metric == 60


def test_velocity_silent_on_normal_pace() -> None:
    """5 transfers spaced 1 hour apart don't fire."""
    base = datetime(2026, 5, 18, 9, 0, tzinfo=VN_TZ)
    txns = [
        make_txn(
            txn_id=f"T-{i}",
            kind=TxnKind.INTERBANK_TRANSFER,
            direction=TxnDirection.DEBIT,
            amount_vnd=1_000_000,
            occurred_at=base + timedelta(hours=i),
        )
        for i in range(5)
    ]
    assert find_high_velocity(txns) == []


def test_velocity_ignores_credits() -> None:
    base = datetime(2026, 5, 18, 14, 0, tzinfo=VN_TZ)
    txns = [
        make_txn(
            txn_id=f"T-{i}",
            kind=TxnKind.VIETQR_RECEIVE,
            direction=TxnDirection.CREDIT,
            amount_vnd=100_000,
            occurred_at=base + timedelta(seconds=i * 10),
        )
        for i in range(100)
    ]
    assert find_high_velocity(txns) == []


def test_velocity_validates_param() -> None:
    with pytest.raises(ValueError, match="window_hours"):
        find_high_velocity([], window_hours=0)
    with pytest.raises(ValueError, match="min_velocity_txns"):
        find_high_velocity([], min_velocity_txns=1)
