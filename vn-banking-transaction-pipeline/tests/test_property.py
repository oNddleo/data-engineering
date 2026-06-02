"""Hypothesis property tests."""

from __future__ import annotations

from datetime import datetime, timedelta

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from vnbank.banks import all_profiles, profile_for_bin
from vnbank.io_jsonl import txn_from_dict, txn_to_dict
from vnbank.routing import NAPAS_247_MAX_VND, Rail, route
from vnbank.schema import (
    VN_TZ,
    Transaction,
    TxnDirection,
    TxnKind,
)
from vnbank.summary import aggregate_daily
from vnbank.vietqr import build_vietqr, parse_vietqr

_bins_pool = tuple(p.bank.bin_code for p in all_profiles())


@st.composite
def vn_account(draw: st.DrawFn) -> tuple[str, str]:
    profile = draw(st.sampled_from(all_profiles()))
    length = draw(
        st.integers(
            min_value=profile.min_account_length,
            max_value=profile.max_account_length,
        ),
    )
    digits = draw(st.integers(min_value=0, max_value=10**length - 1))
    return (f"{digits:0{length}d}", profile.bank.bin_code)


@st.composite
def voice_txn(draw: st.DrawFn) -> Transaction:
    account, bin_ = draw(vn_account())
    amount = draw(st.integers(min_value=1, max_value=10_000_000))
    days = draw(st.integers(min_value=0, max_value=29))
    hour = draw(st.integers(min_value=0, max_value=23))
    txn_id = draw(st.text(min_size=1, max_size=10, alphabet="0123456789AB"))
    kind = draw(
        st.sampled_from(
            [
                TxnKind.INTRA_BANK_TRANSFER,
                TxnKind.INTERBANK_TRANSFER,
                TxnKind.VIETQR_SEND,
                TxnKind.BILL_PAYMENT,
            ]
        )
    )
    direction = draw(st.sampled_from([TxnDirection.DEBIT, TxnDirection.CREDIT]))
    return Transaction(
        txn_id=f"T-{txn_id}-{days}-{hour}",
        account_number=account,
        bank_bin=bin_,
        kind=kind,
        direction=direction,
        amount_vnd=amount,
        occurred_at=datetime(2026, 5, 1, hour, 0, tzinfo=VN_TZ) + timedelta(days=days),
    )


# ---------- VietQR ----------------------------------------------------------


@given(
    st.sampled_from(_bins_pool),
    st.integers(min_value=0, max_value=99_999_999_999_999),
    st.integers(min_value=0, max_value=999_999_999),
)
@settings(max_examples=50)
def test_vietqr_roundtrip(bin_code: str, account_seed: int, amount: int) -> None:
    """build → parse must recover the input fields."""
    profile = profile_for_bin(bin_code)
    assert profile is not None
    length = profile.min_account_length
    account = f"{account_seed:0{length}d}"[:length]
    qr = build_vietqr(bin_code, account, amount)
    parsed = parse_vietqr(qr)
    assert parsed.bank_bin == bin_code
    assert parsed.account_number == account
    assert parsed.amount_vnd == amount


# ---------- Routing ---------------------------------------------------------


@given(
    st.sampled_from(_bins_pool),
    st.sampled_from(_bins_pool),
    st.integers(min_value=0, max_value=NAPAS_247_MAX_VND),
)
@settings(max_examples=60)
def test_route_amount_under_cap_never_uses_citad(
    sender: str,
    receiver: str,
    amount: int,
) -> None:
    d = route(sender, receiver, amount)
    assert d.rail is not Rail.CITAD


@given(
    st.sampled_from(_bins_pool),
    st.sampled_from(_bins_pool),
    st.integers(min_value=NAPAS_247_MAX_VND + 1, max_value=10_000_000_000),
)
@settings(max_examples=40)
def test_route_amount_above_cap_uses_citad_when_interbank(
    sender: str,
    receiver: str,
    amount: int,
) -> None:
    if sender == receiver:
        return  # same bank → intra, not citad
    d = route(sender, receiver, amount)
    assert d.rail is Rail.CITAD


@given(
    st.sampled_from(_bins_pool),
    st.sampled_from(_bins_pool),
    st.integers(min_value=0, max_value=NAPAS_247_MAX_VND),
)
@settings(max_examples=40)
def test_route_fee_never_negative(
    sender: str,
    receiver: str,
    amount: int,
) -> None:
    d = route(sender, receiver, amount)
    assert d.fee_vnd >= 0


# ---------- JSONL -----------------------------------------------------------


@given(voice_txn())
@settings(max_examples=50)
def test_txn_jsonl_roundtrip(t: Transaction) -> None:
    assert txn_from_dict(txn_to_dict(t)) == t


# ---------- Summary conservation -------------------------------------------


@given(st.lists(voice_txn(), min_size=1, max_size=30))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=20)
def test_summary_totals_equal_input_totals(txns: list[Transaction]) -> None:
    seen: set[str] = set()
    unique = []
    for t in txns:
        if t.txn_id not in seen:
            seen.add(t.txn_id)
            unique.append(t)
    summaries = aggregate_daily(unique)
    sum_debit_summary = sum(s.total_debit_vnd for s in summaries)
    sum_credit_summary = sum(s.total_credit_vnd for s in summaries)
    sum_debit_txn = sum(t.amount_vnd for t in unique if t.direction is TxnDirection.DEBIT)
    sum_credit_txn = sum(t.amount_vnd for t in unique if t.direction is TxnDirection.CREDIT)
    assert sum_debit_summary == sum_debit_txn
    assert sum_credit_summary == sum_credit_txn
