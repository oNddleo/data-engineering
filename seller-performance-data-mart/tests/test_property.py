"""Hypothesis properties — fact-table invariants are preserved by the ETL."""

from __future__ import annotations

from datetime import datetime, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from sellermart.etl import build_fact_seller_day
from sellermart.schema import VN_TZ
from sellermart.sources import Order, Return


@st.composite
def _orders(draw: st.DrawFn) -> list[Order]:
    n = draw(st.integers(min_value=1, max_value=10))
    sellers = draw(
        st.lists(
            st.integers(min_value=100_001, max_value=100_005),
            min_size=1,
            max_size=3,
            unique=True,
        )
    )
    base = datetime(2026, 5, 1, 9, 0, 0, tzinfo=VN_TZ)
    out: list[Order] = []
    for i in range(n):
        seller = draw(st.sampled_from(sellers))
        day_offset = draw(st.integers(min_value=0, max_value=4))
        out.append(
            Order(
                order_id=f"O-{i:04d}",
                seller_id=seller,
                buyer_id=f"B-{draw(st.integers(min_value=0, max_value=5)):03d}",
                category_key="electronics",
                n_units=draw(st.integers(min_value=1, max_value=4)),
                gross_vnd=draw(st.integers(min_value=0, max_value=10_000_000)),
                created_at=base + timedelta(days=day_offset),
            )
        )
    return out


@given(orders=_orders())
@settings(max_examples=50, deadline=None)
def test_total_orders_preserved(orders: list[Order]) -> None:
    """Sum of n_orders over all fact rows == len(orders)."""
    facts = build_fact_seller_day(orders, [], [])
    assert sum(f.n_orders for f in facts) == len(orders)


@given(orders=_orders())
@settings(max_examples=50, deadline=None)
def test_gmv_preserved(orders: list[Order]) -> None:
    """Sum of gmv_vnd over all fact rows == sum of order gross."""
    facts = build_fact_seller_day(orders, [], [])
    assert sum(f.gmv_vnd for f in facts) == sum(o.gross_vnd for o in orders)


@given(orders=_orders())
@settings(max_examples=50, deadline=None)
def test_unique_buyers_at_most_n_orders(orders: list[Order]) -> None:
    """n_unique_buyers <= n_orders for every fact row (invariant from schema)."""
    facts = build_fact_seller_day(orders, [], [])
    for f in facts:
        assert f.n_unique_buyers <= f.n_orders


@given(orders=_orders())
@settings(max_examples=50, deadline=None)
def test_facts_sorted_by_seller_then_date(orders: list[Order]) -> None:
    facts = build_fact_seller_day(orders, [], [])
    keys = [(f.seller_id, f.date_key) for f in facts]
    assert keys == sorted(keys)


@given(orders=_orders())
@settings(max_examples=30, deadline=None)
def test_orphan_returns_are_dropped(orders: list[Order]) -> None:
    """A return with a foreign order_id never affects the fact table."""
    facts_no_ret = build_fact_seller_day(orders, [], [])
    bogus = Return(
        return_id="RT-orphan",
        order_id="NOT-PRESENT",
        seller_id=100_001,
        refund_vnd=999,
        created_at=datetime(2026, 5, 1, tzinfo=VN_TZ),
    )
    facts_with_orphan = build_fact_seller_day(orders, [bogus], [])
    assert facts_no_ret == facts_with_orphan
