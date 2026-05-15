"""Schema invariants."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from clvseg.schema import VN_TZ, RFMScore, Segment

from ._fixtures import DEFAULT_TS, make_customer, make_order, make_score


def test_vn_tz_is_utc_plus_7():
    offset = VN_TZ.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == 7 * 3600


def test_segment_enum_has_ten_values():
    """10 segments per the standard RFM industry mapping."""
    assert len(list(Segment)) == 10


def test_customer_rejects_empty_id():
    with pytest.raises(ValueError):
        make_customer(customer_id="")


def test_customer_rejects_empty_city():
    with pytest.raises(ValueError):
        make_customer(city_key="")


def test_customer_rejects_naive_datetime():
    with pytest.raises(ValueError):
        make_customer(registered_at=datetime(2026, 1, 1))


def test_order_rejects_empty_ids():
    with pytest.raises(ValueError):
        make_order(order_id="")
    with pytest.raises(ValueError):
        make_order(customer_id="")


def test_order_rejects_zero_items():
    with pytest.raises(ValueError):
        make_order(n_items=0)


def test_order_rejects_negative_gross():
    with pytest.raises(ValueError):
        make_order(gross_vnd=-1)


def test_order_zero_gross_allowed():
    """Zero-VND order is valid — promo / coupon / refund-pending."""
    o = make_order(gross_vnd=0)
    assert o.gross_vnd == 0


def test_score_rfm_string_concatenates():
    s = make_score(r_score=5, f_score=3, m_score=4)
    assert s.rfm_string == "534"


def test_score_composite_numeric():
    s = make_score(r_score=5, f_score=3, m_score=4)
    assert s.composite == 534


def test_score_validates_rfm_range():
    for field in ("r_score", "f_score", "m_score"):
        with pytest.raises(ValueError):
            make_score(**{field: 0})
        with pytest.raises(ValueError):
            make_score(**{field: 6})


def test_score_rejects_negative_recency():
    with pytest.raises(ValueError):
        make_score(recency_days=-1)


def test_score_rejects_negative_frequency():
    with pytest.raises(ValueError):
        make_score(frequency=-1)


def test_score_rejects_negative_monetary():
    with pytest.raises(ValueError):
        make_score(monetary_vnd=-1)


def test_score_zero_frequency_is_legal():
    """A registered-but-never-bought customer is still a valid record."""
    s = make_score(frequency=0, monetary_vnd=0)
    assert s.frequency == 0
    assert s.monetary_vnd == 0


def test_score_rejects_naive_as_of():
    with pytest.raises(ValueError):
        RFMScore(
            customer_id="C",
            as_of=datetime(2026, 5, 14),
            recency_days=0,
            frequency=0,
            monetary_vnd=0,
            r_score=1,
            f_score=1,
            m_score=1,
        )


def test_order_placed_in_past_legal():
    o = make_order(placed_at=DEFAULT_TS - timedelta(days=300))
    assert o.placed_at < DEFAULT_TS
