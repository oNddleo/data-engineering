"""Source-record validation."""

from __future__ import annotations

from datetime import datetime

import pytest

from sellermart.schema import VN_TZ
from sellermart.sources import Order, Review

from ._fixtures import make_order, make_return, make_review


def test_order_happy_path():
    o = make_order()
    assert o.seller_id == 100_001
    assert o.n_units == 2


def test_order_rejects_empty_id():
    with pytest.raises(ValueError):
        make_order(order_id="")


def test_order_rejects_bad_seller():
    with pytest.raises(ValueError):
        make_order(seller_id=0)


def test_order_rejects_zero_units():
    with pytest.raises(ValueError):
        make_order(n_units=0)


def test_order_rejects_negative_gross():
    with pytest.raises(ValueError):
        make_order(gross_vnd=-1)


def test_order_requires_tz_aware():
    with pytest.raises(ValueError):
        Order(
            order_id="O-1",
            seller_id=1,
            buyer_id="B",
            category_key="cat",
            n_units=1,
            gross_vnd=0,
            created_at=datetime(2026, 5, 1),
        )


def test_order_zero_gross_is_legal():
    o = make_order(gross_vnd=0)
    assert o.gross_vnd == 0


def test_return_happy_path():
    r = make_return()
    assert r.refund_vnd == 499_000


def test_return_rejects_negative_refund():
    with pytest.raises(ValueError):
        make_return(refund_vnd=-1)


def test_return_rejects_empty_order_id():
    with pytest.raises(ValueError):
        make_return(order_id="")


def test_review_validates_rating_range():
    with pytest.raises(ValueError):
        make_review(rating_x100=501)
    with pytest.raises(ValueError):
        make_review(rating_x100=-1)


def test_review_rejects_naive_datetime():
    with pytest.raises(ValueError):
        Review(
            review_id="RV",
            order_id="O",
            seller_id=1,
            rating_x100=400,
            created_at=datetime(2026, 5, 1),
        )


def test_review_min_max_rating_accepted():
    r0 = make_review(rating_x100=0)
    r500 = make_review(rating_x100=500)
    assert r0.rating_x100 == 0
    assert r500.rating_x100 == 500


def test_review_tz_aware_passes():
    r = Review(
        review_id="RV",
        order_id="O",
        seller_id=1,
        rating_x100=400,
        created_at=datetime(2026, 5, 1, tzinfo=VN_TZ),
    )
    assert r.created_at.tzinfo is not None
