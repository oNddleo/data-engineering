"""Hypothesis property tests."""

from __future__ import annotations

from datetime import datetime, timedelta

from hypothesis import given
from hypothesis import strategies as st

from fxagg.schema import VN_TZ, Bank, Currency, Quote
from fxagg.spread import AlertKind, analyze
from fxagg.storage import TimeSeriesStore, quote_from_dict, quote_to_dict

from ._fixtures import make_quote


@given(
    buy=st.integers(min_value=1, max_value=10**9),
    sell=st.integers(min_value=1, max_value=10**9),
)
def test_quote_round_trips_through_dict(buy, sell):
    q = Quote(
        bank=Bank.VCB,
        currency=Currency.USD,
        buy_transfer_vnd=buy,
        sell_vnd=sell,
        quoted_at=datetime(2026, 5, 14, tzinfo=VN_TZ),
        buy_cash_vnd=None,
    )
    assert quote_from_dict(quote_to_dict(q)) == q


@given(buy=st.integers(min_value=1, max_value=10**9))
def test_inverted_quote_always_fires(buy):
    """For any (buy > sell) input, INVERTED_SPREAD must fire."""
    qs = {
        Bank.VCB: make_quote(buy_transfer=buy + 1, sell=buy),  # always inverted
        Bank.BIDV: make_quote(bank=Bank.BIDV, buy_transfer=25_000, sell=25_200),
        Bank.TCB: make_quote(bank=Bank.TCB, buy_transfer=25_010, sell=25_210),
    }
    a = analyze(qs)
    assert AlertKind.INVERTED_SPREAD in {al.kind for al in a.alerts}


@given(n=st.integers(min_value=1, max_value=30))
def test_storage_append_idempotent_repeats(n):
    """Appending the same quote n times must leave exactly one row."""
    s = TimeSeriesStore()
    q = make_quote()
    for _ in range(n):
        s.append_quote(q)
    assert len(s.history(Bank.VCB, Currency.USD)) == 1


@given(
    times=st.lists(
        st.integers(min_value=0, max_value=10_000),
        min_size=1,
        max_size=30,
        unique=True,
    )
)
def test_storage_history_sorted_regardless_of_insertion_order(times):
    s = TimeSeriesStore()
    base = datetime(2026, 5, 14, tzinfo=VN_TZ)
    for t in times:
        s.append_quote(make_quote(quoted_at=base + timedelta(seconds=t)))
    hist = s.history(Bank.VCB, Currency.USD)
    assert hist == sorted(hist, key=lambda q: q.quoted_at)
