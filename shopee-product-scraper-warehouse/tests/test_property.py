"""Hypothesis property tests."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from shopeedw.io_jsonl import product_from_dict, product_to_dict, shop_from_dict, shop_to_dict
from shopeedw.warehouse import Warehouse

from ._fixtures import make_product, make_shop


@given(price=st.integers(min_value=1, max_value=10**11))
def test_product_round_trips_through_dict(price):
    p = make_product(price=price, original_price=max(price, 999_000))
    assert product_from_dict(product_to_dict(p)) == p


@given(
    rating=st.integers(min_value=0, max_value=500),
    followers=st.integers(min_value=0, max_value=10_000_000),
    response_rate=st.integers(min_value=0, max_value=100),
)
def test_shop_round_trips(rating, followers, response_rate):
    s = make_shop(rating_x100=rating, follower_count=followers, response_rate_pct=response_rate)
    assert shop_from_dict(shop_to_dict(s)) == s


@given(n=st.integers(min_value=0, max_value=20))
def test_warehouse_ingest_n_distinct_products(n):
    wh = Warehouse()
    for i in range(n):
        wh.ingest_product(make_product(item_id=500_000_000 + i))
    assert len(wh.products) == n


@given(price=st.integers(min_value=1_000, max_value=10**9))
def test_gmv_positive_when_sold(price):
    p = make_product(price=price, sold=10, original_price=max(price, 999_000))
    assert p.gmv_vnd == price * 10
