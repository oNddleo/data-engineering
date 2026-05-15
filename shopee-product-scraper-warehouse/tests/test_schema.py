"""Schema invariants."""

from __future__ import annotations

from datetime import datetime

import pytest

from shopeedw.schema import VN_TZ

from ._fixtures import make_product, make_shop


def test_product_happy_path():
    p = make_product(price=200_000, original_price=300_000)
    assert p.gmv_vnd == 200_000 * 50  # default sold=50
    assert 33 < p.discount_pct < 34


def test_product_rejects_non_positive_ids():
    with pytest.raises(ValueError):
        make_product(item_id=0)
    with pytest.raises(ValueError):
        make_product(shop_id=-1)


def test_product_rejects_empty_name():
    with pytest.raises(ValueError):
        make_product(name="  ")


def test_product_rejects_empty_category():
    with pytest.raises(ValueError):
        make_product(category_key="")


def test_product_rejects_non_positive_price():
    with pytest.raises(ValueError):
        make_product(price=0)


def test_product_rejects_price_above_original():
    with pytest.raises(ValueError):
        make_product(price=400_000, original_price=300_000)


def test_product_rejects_negative_stock():
    with pytest.raises(ValueError):
        make_product(stock=-1)


def test_product_rejects_negative_sold():
    with pytest.raises(ValueError):
        make_product(sold=-1)


def test_product_rating_out_of_range():
    with pytest.raises(ValueError):
        make_product(rating_x100=501)
    with pytest.raises(ValueError):
        make_product(rating_x100=-1)


def test_product_rejects_negative_review_count():
    with pytest.raises(ValueError):
        make_product(review_count=-1)


def test_product_rejects_naive_datetime():
    with pytest.raises(ValueError):
        make_product(fetched_at=datetime(2026, 5, 14, 9, 0))


def test_product_discount_pct_zero_when_no_discount():
    p = make_product(price=199_000, original_price=199_000)
    assert p.discount_pct == 0


def test_product_gmv_calculation():
    p = make_product(price=100_000, sold=10)
    assert p.gmv_vnd == 1_000_000


def test_shop_happy_path():
    s = make_shop()
    assert s.rating_x100 == 480


def test_shop_rejects_invalid_response_rate():
    with pytest.raises(ValueError):
        make_shop(response_rate_pct=101)
    with pytest.raises(ValueError):
        make_shop(response_rate_pct=-1)


def test_shop_rejects_invalid_rating():
    with pytest.raises(ValueError):
        make_shop(rating_x100=600)


def test_shop_rejects_negative_followers():
    with pytest.raises(ValueError):
        make_shop(follower_count=-1)


def test_shop_rejects_naive_datetime():
    with pytest.raises(ValueError):
        make_shop(fetched_at=datetime(2026, 5, 14, 9, 0))


def test_vn_tz_offset():
    offset = VN_TZ.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == 7 * 3600
