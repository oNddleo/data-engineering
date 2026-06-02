"""VN property-listing schema.

Models normalized real-estate listings parsed from free-form Vietnamese
text. Listing portals (Batdongsan.com, Chotot, Cafeland) emit prices
in mixed units (VND, *triệu* = 10⁶, *tỷ* = 10⁹) and areas in m².
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PropertyKind(str, Enum):
    """Six kinds covering ~99% of VN residential listings."""

    APARTMENT = "APARTMENT"  # chung cư
    HOUSE = "HOUSE"  # nhà phố
    VILLA = "VILLA"  # biệt thự
    LAND = "LAND"  # đất nền
    SHOPHOUSE = "SHOPHOUSE"  # shophouse / nhà mặt phố
    OTHER = "OTHER"


@dataclass(frozen=True, slots=True)
class Listing:
    """One normalised listing record."""

    listing_id: str
    kind: PropertyKind
    area_m2: int  # area in whole m² (rounded)
    price_vnd: int  # integer VND (no Decimal)
    province: str  # e.g. "TP. Hồ Chí Minh"
    district: str = ""  # e.g. "Quận 1", "Hoàn Kiếm"
    ward: str = ""  # e.g. "Phường Bến Nghé"
    bedrooms: int = 0
    bathrooms: int = 0

    def __post_init__(self) -> None:
        if not self.listing_id:
            raise ValueError("listing_id must be non-empty")
        if self.area_m2 <= 0:
            raise ValueError(f"area_m2 must be > 0, got {self.area_m2}")
        if self.price_vnd <= 0:
            raise ValueError(f"price_vnd must be > 0, got {self.price_vnd}")
        if not self.province:
            raise ValueError("province must be non-empty")
        if self.bedrooms < 0 or self.bathrooms < 0:
            raise ValueError("bedrooms / bathrooms must be >= 0")

    @property
    def price_per_m2_vnd(self) -> int:
        return self.price_vnd // self.area_m2

    @property
    def price_billions_vnd(self) -> float:
        """Convert to billions of VND (tỷ) — the user-facing display unit."""
        return self.price_vnd / 1_000_000_000


__all__ = ["Listing", "PropertyKind"]
