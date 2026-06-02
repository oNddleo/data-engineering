"""Schema for Shopee VN product + shop facts.

Two main row types flow through the warehouse:

* :class:`ShopeeProduct` — one snapshot of a product listing at a
  specific point in time. Multiple snapshots of the same
  ``(item_id, shop_id)`` over time form the price-history series.
* :class:`ShopeeShop` — one snapshot of a seller's profile.

Money is integer VND. Ratings are stored as ``int`` representing
hundredths (so 4.85 stars → ``485``) to keep the schema fully
integer-typed and avoid float drift in aggregations.

The ``fetched_at`` field is the scrape time, **not** the
listing-creation time — that's important because product warehouses
key everything off when WE observed the row, not when the seller
created the listing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

VN_TZ = timezone(timedelta(hours=7))


@dataclass(frozen=True, slots=True)
class ShopeeProduct:
    """One snapshot of a product listing."""

    item_id: int
    shop_id: int
    name: str
    category_key: str
    price_vnd: int
    original_price_vnd: int
    stock: int
    sold_count: int
    rating_x100: int  # 4.85 stars → 485
    review_count: int
    fetched_at: datetime

    def __post_init__(self) -> None:
        if self.item_id <= 0:
            raise ValueError(f"item_id must be > 0, got {self.item_id}")
        if self.shop_id <= 0:
            raise ValueError(f"shop_id must be > 0, got {self.shop_id}")
        if not self.name.strip():
            raise ValueError("name must be non-empty")
        if not self.category_key:
            raise ValueError("category_key must be non-empty")
        if self.price_vnd <= 0:
            raise ValueError(f"price_vnd must be > 0, got {self.price_vnd}")
        if self.original_price_vnd < self.price_vnd:
            raise ValueError(
                f"original_price_vnd ({self.original_price_vnd}) must be >= price_vnd ({self.price_vnd})"
            )
        if self.stock < 0:
            raise ValueError(f"stock must be >= 0, got {self.stock}")
        if self.sold_count < 0:
            raise ValueError(f"sold_count must be >= 0, got {self.sold_count}")
        if not 0 <= self.rating_x100 <= 500:
            raise ValueError(f"rating_x100 must be in [0, 500], got {self.rating_x100}")
        if self.review_count < 0:
            raise ValueError(f"review_count must be >= 0, got {self.review_count}")
        if self.fetched_at.tzinfo is None:
            raise ValueError("fetched_at must be timezone-aware")

    @property
    def discount_pct(self) -> float:
        """``(original − price) / original × 100``. Zero when no discount."""
        if self.original_price_vnd == 0:
            return 0.0
        return (self.original_price_vnd - self.price_vnd) / self.original_price_vnd * 100

    @property
    def gmv_vnd(self) -> int:
        """Gross merchandise value contribution = ``price × sold_count``."""
        return self.price_vnd * self.sold_count


@dataclass(frozen=True, slots=True)
class ShopeeShop:
    """One snapshot of a seller's profile."""

    shop_id: int
    name: str
    location_province_code: str
    rating_x100: int
    follower_count: int
    response_rate_pct: int  # 0..100
    is_official: bool
    fetched_at: datetime

    def __post_init__(self) -> None:
        if self.shop_id <= 0:
            raise ValueError(f"shop_id must be > 0, got {self.shop_id}")
        if not self.name.strip():
            raise ValueError("name must be non-empty")
        if not 0 <= self.rating_x100 <= 500:
            raise ValueError(f"rating_x100 must be in [0, 500], got {self.rating_x100}")
        if self.follower_count < 0:
            raise ValueError(f"follower_count must be >= 0, got {self.follower_count}")
        if not 0 <= self.response_rate_pct <= 100:
            raise ValueError(f"response_rate_pct must be in [0, 100], got {self.response_rate_pct}")
        if self.fetched_at.tzinfo is None:
            raise ValueError("fetched_at must be timezone-aware")


__all__ = ["VN_TZ", "ShopeeProduct", "ShopeeShop"]
