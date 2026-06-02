"""Schema for multi-platform price tracking.

Three core shapes:

* :class:`Platform` — which marketplace the observation came from.
  We bundle the three biggest Vietnamese platforms (Shopee, Lazada,
  Tiki); production can extend the enum for Sendo, FPT Shop, etc.
* :class:`SkuMapping` — links one platform's internal item id to a
  canonical SKU (typically the GTIN / EAN / UPC barcode, or a
  retailer-supplied stock-keeping number). One SKU usually maps to
  three platform listings — one per platform.
* :class:`ProductObservation` — one price/stock snapshot from a
  platform at a point in time.

Money is integer VND. Datetimes are tz-aware UTC+7.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))


class Platform(str, Enum):
    """A retail platform observed by the tracker."""

    SHOPEE = "SHOPEE"
    LAZADA = "LAZADA"
    TIKI = "TIKI"


@dataclass(frozen=True, slots=True)
class SkuMapping:
    """Link a ``(platform, platform_item_id)`` pair to a canonical SKU."""

    canonical_sku: str
    platform: Platform
    platform_item_id: str

    def __post_init__(self) -> None:
        if not self.canonical_sku:
            raise ValueError("canonical_sku must be non-empty")
        if not self.platform_item_id:
            raise ValueError("platform_item_id must be non-empty")


@dataclass(frozen=True, slots=True)
class ProductObservation:
    """One observation of a product's price + stock on one platform."""

    canonical_sku: str
    platform: Platform
    platform_item_id: str
    name: str
    price_vnd: int
    original_price_vnd: int
    stock: int
    observed_at: datetime

    def __post_init__(self) -> None:
        if not self.canonical_sku:
            raise ValueError("canonical_sku must be non-empty")
        if not self.platform_item_id:
            raise ValueError("platform_item_id must be non-empty")
        if not self.name.strip():
            raise ValueError("name must be non-empty")
        if self.price_vnd <= 0:
            raise ValueError(f"price_vnd must be > 0, got {self.price_vnd}")
        if self.original_price_vnd < self.price_vnd:
            raise ValueError(
                f"original_price_vnd ({self.original_price_vnd}) must be >= "
                f"price_vnd ({self.price_vnd})"
            )
        if self.stock < 0:
            raise ValueError(f"stock must be >= 0, got {self.stock}")
        if self.observed_at.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")

    @property
    def is_in_stock(self) -> bool:
        return self.stock > 0


__all__ = ["VN_TZ", "Platform", "ProductObservation", "SkuMapping"]
