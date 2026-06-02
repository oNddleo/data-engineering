"""Star-schema data mart for VN-marketplace seller performance.

The mart is the classic Kimball star:

* :class:`DimSeller`     — one row per seller (Shopee shop / Lazada vendor).
* :class:`DimDate`       — one row per calendar day in ``VN_TZ``.
* :class:`DimCategory`   — one row per leaf category key.
* :class:`FactSellerDay` — one row per (seller_id, date_key) grain. The
  grain is **daily**, not per-order, because the downstream consumers
  (ops dashboards, finance) want a stable per-day shape regardless of
  the underlying order volume.

All money is integer ``VND`` (no Decimal, no float drift). Star ratings
are stored × 100 (matches the convention from
``shopee-product-scraper-warehouse`` so reviews join cleanly).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

VN_TZ = timezone(timedelta(hours=7))


@dataclass(frozen=True, slots=True)
class DimSeller:
    """One seller (Shopee shop / Lazada vendor / Tiki seller)."""

    seller_id: int
    seller_name: str
    onboarded_at: datetime
    is_official_shop: bool

    def __post_init__(self) -> None:
        if self.seller_id <= 0:
            raise ValueError(f"seller_id must be > 0, got {self.seller_id}")
        if not self.seller_name:
            raise ValueError("seller_name must be non-empty")
        if self.onboarded_at.tzinfo is None:
            raise ValueError("onboarded_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class DimDate:
    """One calendar day, with cached weekday + ISO-week parts.

    ``date_key`` is the canonical ``YYYYMMDD`` int — easier to join on
    than a date object, and stable across language libraries.
    """

    date_key: int
    day: date
    weekday: int  # 0 = Monday … 6 = Sunday
    iso_week: int
    iso_year: int

    def __post_init__(self) -> None:
        if not 10000000 <= self.date_key <= 99991231:
            raise ValueError(f"date_key must look like YYYYMMDD, got {self.date_key}")
        if not 0 <= self.weekday <= 6:
            raise ValueError(f"weekday must be in [0, 6], got {self.weekday}")
        expected_key = self.day.year * 10000 + self.day.month * 100 + self.day.day
        if expected_key != self.date_key:
            raise ValueError(f"date_key {self.date_key} doesn't match day {self.day}")


@dataclass(frozen=True, slots=True)
class DimCategory:
    """One leaf category in the marketplace taxonomy."""

    category_key: str
    display_name: str
    parent_key: str | None

    def __post_init__(self) -> None:
        if not self.category_key:
            raise ValueError("category_key must be non-empty")
        if not self.display_name:
            raise ValueError("display_name must be non-empty")


@dataclass(frozen=True, slots=True)
class FactSellerDay:
    """One (seller, day) row in the fact table.

    Grain: **one row per ``(seller_id, date_key)``**. If a seller had
    zero orders on a given day, the row is absent (the mart is
    sparse). All counters are non-negative; ``returns`` ≤ ``orders``.
    """

    seller_id: int
    date_key: int
    n_orders: int
    n_units: int
    gmv_vnd: int
    n_returns: int
    refund_vnd: int
    n_reviews: int
    sum_rating_x100: int
    n_unique_buyers: int

    def __post_init__(self) -> None:
        for name, value in (
            ("n_orders", self.n_orders),
            ("n_units", self.n_units),
            ("gmv_vnd", self.gmv_vnd),
            ("n_returns", self.n_returns),
            ("refund_vnd", self.refund_vnd),
            ("n_reviews", self.n_reviews),
            ("sum_rating_x100", self.sum_rating_x100),
            ("n_unique_buyers", self.n_unique_buyers),
        ):
            if value < 0:
                raise ValueError(f"{name} must be >= 0, got {value}")
        if self.n_returns > self.n_orders:
            raise ValueError(
                f"n_returns ({self.n_returns}) cannot exceed n_orders ({self.n_orders})"
            )
        if self.n_units < self.n_orders:
            raise ValueError(
                f"n_units ({self.n_units}) cannot be less than n_orders ({self.n_orders})"
            )
        if self.n_unique_buyers > self.n_orders:
            raise ValueError(
                f"n_unique_buyers ({self.n_unique_buyers}) cannot exceed n_orders ({self.n_orders})"
            )


def make_date_key(day: date) -> int:
    """Pack ``date`` → ``YYYYMMDD`` integer."""
    return day.year * 10000 + day.month * 100 + day.day


def make_dim_date(day: date) -> DimDate:
    """Build a populated :class:`DimDate` from a plain ``date``."""
    iso_year, iso_week, _ = day.isocalendar()
    return DimDate(
        date_key=make_date_key(day),
        day=day,
        weekday=day.weekday(),
        iso_week=iso_week,
        iso_year=iso_year,
    )


__all__ = [
    "VN_TZ",
    "DimCategory",
    "DimDate",
    "DimSeller",
    "FactSellerDay",
    "make_date_key",
    "make_dim_date",
]
