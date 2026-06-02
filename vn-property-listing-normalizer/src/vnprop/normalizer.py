"""End-to-end normaliser — free-text listing → ``Listing``."""

from __future__ import annotations

import re
from dataclasses import dataclass

from vnprop.area import parse_area_m2
from vnprop.location import parse_district, parse_province, parse_ward
from vnprop.price import parse_price_vnd
from vnprop.schema import Listing, PropertyKind

# Kind keywords (VN + EN).
_KIND_KEYWORDS: dict[PropertyKind, tuple[str, ...]] = {
    PropertyKind.APARTMENT: ("chung cư", "căn hộ", "apartment", "ch."),
    PropertyKind.HOUSE: ("nhà phố", "nhà riêng", "nhà cấp 4", "house"),
    PropertyKind.VILLA: ("biệt thự", "villa"),
    PropertyKind.LAND: ("đất nền", "đất thổ cư", "đất bán", "land"),
    PropertyKind.SHOPHOUSE: ("shophouse", "nhà mặt phố", "mặt tiền"),
}

_BEDROOM_RE = re.compile(r"(\d+)\s*(?:phòng\s*ngủ|pn|bedroom|br)", re.IGNORECASE)
_BATHROOM_RE = re.compile(r"(\d+)\s*(?:phòng\s*tắm|wc|toilet|bathroom)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class RawListing:
    """Raw free-text input record."""

    listing_id: str
    title: str
    description: str
    price_text: str
    area_text: str


def normalize(raw: RawListing) -> Listing:
    """Parse a free-text listing into a normalised ``Listing``."""
    combined = f"{raw.title} {raw.description}".lower()
    kind = _detect_kind(combined)
    area = parse_area_m2(raw.area_text or combined)
    price = parse_price_vnd(raw.price_text)
    full_location = f"{raw.title} {raw.description}"
    return Listing(
        listing_id=raw.listing_id,
        kind=kind,
        area_m2=area,
        price_vnd=price,
        province=parse_province(full_location) or "Unknown",
        district=parse_district(full_location),
        ward=parse_ward(full_location),
        bedrooms=_extract_int(_BEDROOM_RE, combined),
        bathrooms=_extract_int(_BATHROOM_RE, combined),
    )


def _detect_kind(text: str) -> PropertyKind:
    for kind, keywords in _KIND_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return kind
    return PropertyKind.OTHER


def _extract_int(pattern: re.Pattern[str], text: str) -> int:
    m = pattern.search(text)
    if m is None:
        return 0
    return int(m.group(1))


__all__ = ["RawListing", "normalize"]
