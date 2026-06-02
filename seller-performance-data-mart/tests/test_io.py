"""JSONL codec round-trips + type checks."""

from __future__ import annotations

import pytest

from sellermart.io_jsonl import (
    dump_facts,
    dump_orders,
    dump_returns,
    dump_reviews,
    fact_from_dict,
    fact_to_dict,
    load_facts,
    load_orders,
    load_returns,
    load_reviews,
    order_from_dict,
    return_from_dict,
    review_from_dict,
)
from sellermart.schema import FactSellerDay

from ._fixtures import make_order, make_return, make_review


def test_order_roundtrip():
    o = make_order()
    text = dump_orders([o])
    [back] = list(load_orders(text))
    assert back == o


def test_return_roundtrip():
    r = make_return()
    text = dump_returns([r])
    [back] = list(load_returns(text))
    assert back == r


def test_review_roundtrip():
    rv = make_review()
    text = dump_reviews([rv])
    [back] = list(load_reviews(text))
    assert back == rv


def test_fact_roundtrip():
    f = FactSellerDay(
        seller_id=100_001,
        date_key=20260514,
        n_orders=10,
        n_units=15,
        gmv_vnd=1_000_000,
        n_returns=1,
        refund_vnd=99_000,
        n_reviews=5,
        sum_rating_x100=2_250,
        n_unique_buyers=8,
    )
    text = dump_facts([f])
    [back] = list(load_facts(text))
    assert back == f


def test_jsonl_handles_blank_lines():
    text = dump_orders([make_order()])
    blanks = "\n\n" + text + "\n\n"
    back = list(load_orders(blanks))
    assert len(back) == 1


def test_order_decoder_rejects_wrong_type():
    bad = {
        "order_id": 5,
        "seller_id": 1,
        "buyer_id": "B",
        "category_key": "c",
        "n_units": 1,
        "gross_vnd": 0,
        "created_at": "2026-05-01T00:00:00+07:00",
    }
    with pytest.raises(TypeError, match="order_id"):
        order_from_dict(bad)


def test_order_decoder_rejects_bool_for_int():
    """bool is a subclass of int — we must reject it for int fields."""
    bad = {
        "order_id": "O",
        "seller_id": True,
        "buyer_id": "B",
        "category_key": "c",
        "n_units": 1,
        "gross_vnd": 0,
        "created_at": "2026-05-01T00:00:00+07:00",
    }
    with pytest.raises(TypeError, match="seller_id"):
        order_from_dict(bad)


def test_return_decoder_rejects_missing_key():
    with pytest.raises(KeyError):
        return_from_dict({"return_id": "RT"})


def test_review_decoder_rejects_string_rating():
    bad = {
        "review_id": "RV",
        "order_id": "O",
        "seller_id": 1,
        "rating_x100": "450",
        "created_at": "2026-05-01T00:00:00+07:00",
    }
    with pytest.raises(TypeError, match="rating_x100"):
        review_from_dict(bad)


def test_fact_to_dict_includes_all_fields():
    f = FactSellerDay(
        seller_id=1,
        date_key=20260101,
        n_orders=1,
        n_units=1,
        gmv_vnd=0,
        n_returns=0,
        refund_vnd=0,
        n_reviews=0,
        sum_rating_x100=0,
        n_unique_buyers=1,
    )
    d = fact_to_dict(f)
    assert set(d) == {
        "seller_id",
        "date_key",
        "n_orders",
        "n_units",
        "gmv_vnd",
        "n_returns",
        "refund_vnd",
        "n_reviews",
        "sum_rating_x100",
        "n_unique_buyers",
    }


def test_fact_from_dict_preserves_zero_values():
    d = {
        "seller_id": 1,
        "date_key": 20260101,
        "n_orders": 1,
        "n_units": 1,
        "gmv_vnd": 0,
        "n_returns": 0,
        "refund_vnd": 0,
        "n_reviews": 0,
        "sum_rating_x100": 0,
        "n_unique_buyers": 1,
    }
    f = fact_from_dict(d)
    assert f.gmv_vnd == 0
    assert f.n_orders == 1
