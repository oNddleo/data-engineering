"""Hypothesis property tests — invariants that must hold over arbitrary inputs."""

from __future__ import annotations

from datetime import datetime

from hypothesis import given
from hypothesis import strategies as st

from vmzrecon.discrepancy import DiscrepancyKind
from vmzrecon.matcher import reconcile
from vmzrecon.normalize import status_from_momo, status_from_vnpay
from vmzrecon.report import summarise
from vmzrecon.schema import VN_TZ, MerchantOrder, Status, Wallet, WalletTxn


def _w(order_id: str, amount: int, status: Status = Status.SUCCESS) -> WalletTxn:
    return WalletTxn(
        wallet=Wallet.VNPAY,
        merchant_order_id=order_id,
        wallet_txn_id="T-" + order_id,
        amount_vnd=amount,
        status=status,
        paid_at=datetime(2026, 5, 14, tzinfo=VN_TZ),
    )


def _m(order_id: str, amount: int, status: Status = Status.SUCCESS) -> MerchantOrder:
    return MerchantOrder(
        order_id=order_id,
        wallet=Wallet.VNPAY,
        expected_amount_vnd=amount,
        status=status,
        created_at=datetime(2026, 5, 14, tzinfo=VN_TZ),
    )


@given(
    order_ids=st.lists(
        st.text(min_size=1, max_size=8, alphabet=st.characters(min_codepoint=65, max_codepoint=90)),
        min_size=1,
        max_size=20,
        unique=True,
    ),
    amount=st.integers(min_value=1, max_value=10_000_000),
)
def test_identical_sides_never_produce_discrepancies(order_ids, amount):
    """If wallet and merchant agree perfectly, recon must return [].

    Property: reconcile(M, W) == [] when M and W are mirror images.
    """
    merchant = [_m(oid, amount) for oid in order_ids]
    wallet = [_w(oid, amount) for oid in order_ids]
    assert reconcile(merchant, wallet) == []


@given(
    order_ids=st.lists(
        st.text(min_size=1, max_size=8, alphabet=st.characters(min_codepoint=65, max_codepoint=90)),
        min_size=1,
        max_size=10,
        unique=True,
    )
)
def test_wallet_only_summary_matches_count(order_ids):
    """Property: |reconcile([], W)| == |W| when every wallet txn is unmatched."""
    wallet = [_w(oid, 1_000_000) for oid in order_ids]
    discrepancies = reconcile([], wallet)
    assert len(discrepancies) == len(order_ids)
    assert all(d.kind is DiscrepancyKind.WALLET_ONLY for d in discrepancies)


@given(amount=st.integers(min_value=0, max_value=10_000_000))
def test_summarise_total_equals_input_length(amount):
    """summarise(disc).total == len(disc) for any input."""
    wallet = [_w("ORD", amount)]
    discrepancies = reconcile([], wallet)
    s = summarise(discrepancies)
    assert s.total == len(discrepancies)


@given(code=st.text(min_size=0, max_size=4))
def test_vnpay_status_always_returns_a_status(code):
    """status_from_vnpay never raises on string input."""
    assert status_from_vnpay(code) in {Status.SUCCESS, Status.FAILED, Status.PENDING}


@given(code=st.integers(min_value=-100, max_value=100_000))
def test_momo_status_always_returns_a_status(code):
    assert status_from_momo(code) in {Status.SUCCESS, Status.FAILED, Status.PENDING}
