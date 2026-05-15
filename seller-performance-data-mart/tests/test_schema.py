"""Dimension + fact invariants."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from sellermart.schema import (
    VN_TZ,
    DimCategory,
    DimDate,
    DimSeller,
    FactSellerDay,
    make_date_key,
    make_dim_date,
)


def test_vn_tz_is_utc_plus_7():
    offset = VN_TZ.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == 7 * 3600


def test_make_date_key_packs_yyyymmdd():
    assert make_date_key(date(2026, 5, 14)) == 20260514
    assert make_date_key(date(2026, 1, 1)) == 20260101


def test_make_dim_date_populates_iso_parts():
    d = make_dim_date(date(2026, 5, 14))
    assert d.date_key == 20260514
    assert d.weekday == 3  # Thursday
    assert d.iso_year == 2026
    assert 1 <= d.iso_week <= 53


def test_dim_seller_rejects_bad_id():
    with pytest.raises(ValueError):
        DimSeller(
            seller_id=0,
            seller_name="Shop",
            onboarded_at=datetime(2026, 1, 1, tzinfo=VN_TZ),
            is_official_shop=False,
        )


def test_dim_seller_rejects_empty_name():
    with pytest.raises(ValueError):
        DimSeller(
            seller_id=1,
            seller_name="",
            onboarded_at=datetime(2026, 1, 1, tzinfo=VN_TZ),
            is_official_shop=False,
        )


def test_dim_seller_requires_tz_aware():
    with pytest.raises(ValueError):
        DimSeller(
            seller_id=1,
            seller_name="Shop",
            onboarded_at=datetime(2026, 1, 1),
            is_official_shop=False,
        )


def test_dim_date_rejects_mismatch():
    with pytest.raises(ValueError):
        DimDate(date_key=20260515, day=date(2026, 5, 14), weekday=3, iso_week=20, iso_year=2026)


def test_dim_date_rejects_out_of_range_key():
    with pytest.raises(ValueError):
        DimDate(date_key=42, day=date(2026, 5, 14), weekday=3, iso_week=20, iso_year=2026)


def test_dim_date_rejects_bad_weekday():
    with pytest.raises(ValueError):
        DimDate(date_key=20260514, day=date(2026, 5, 14), weekday=7, iso_week=20, iso_year=2026)


def test_dim_category_validates_non_empty():
    with pytest.raises(ValueError):
        DimCategory(category_key="", display_name="x", parent_key=None)
    with pytest.raises(ValueError):
        DimCategory(category_key="x", display_name="", parent_key=None)


def _make_fact(**overrides: object) -> FactSellerDay:
    defaults: dict[str, object] = {
        "seller_id": 100_001,
        "date_key": 20260514,
        "n_orders": 10,
        "n_units": 15,
        "gmv_vnd": 1_000_000,
        "n_returns": 1,
        "refund_vnd": 99_000,
        "n_reviews": 5,
        "sum_rating_x100": 2_250,
        "n_unique_buyers": 8,
    }
    defaults.update(overrides)
    return FactSellerDay(**defaults)  # type: ignore[arg-type]


def test_fact_rejects_negative_counts():
    for field in (
        "n_orders",
        "n_units",
        "gmv_vnd",
        "n_returns",
        "refund_vnd",
        "n_reviews",
        "sum_rating_x100",
        "n_unique_buyers",
    ):
        with pytest.raises(ValueError):
            _make_fact(**{field: -1})


def test_fact_rejects_returns_exceeding_orders():
    with pytest.raises(ValueError, match="cannot exceed n_orders"):
        _make_fact(n_orders=3, n_returns=4, n_units=3, n_unique_buyers=3)


def test_fact_rejects_units_less_than_orders():
    with pytest.raises(ValueError, match="cannot be less than n_orders"):
        _make_fact(n_orders=5, n_units=4)


def test_fact_rejects_buyers_exceeding_orders():
    with pytest.raises(ValueError, match="cannot exceed n_orders"):
        _make_fact(n_orders=5, n_units=5, n_unique_buyers=6)


def test_utc_datetime_accepted_for_dim_seller():
    ds = DimSeller(
        seller_id=1,
        seller_name="Shop",
        onboarded_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        is_official_shop=True,
    )
    assert ds.is_official_shop is True
