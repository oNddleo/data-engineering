"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from vnprop.io_jsonl import (
    dump_listings,
    listing_from_dict,
    listing_to_dict,
    load_listings,
    raw_from_dict,
    raw_to_dict,
)
from vnprop.normalizer import RawListing, normalize
from vnprop.schema import Listing, PropertyKind


def test_listing_roundtrip() -> None:
    item = Listing(
        listing_id="L-1",
        kind=PropertyKind.APARTMENT,
        area_m2=80,
        price_vnd=3_500_000_000,
        province="TP. Hồ Chí Minh",
        district="Quận 2",
        ward="Phường Thảo Điền",
        bedrooms=3,
        bathrooms=2,
    )
    assert listing_from_dict(listing_to_dict(item)) == item


def test_raw_roundtrip() -> None:
    r = RawListing(
        listing_id="L-1",
        title="Chung cư",
        description="abc",
        price_text="2 tỷ",
        area_text="60m²",
    )
    assert raw_from_dict(raw_to_dict(r)) == r


def test_dump_load_listings() -> None:
    raws = [
        RawListing(
            listing_id=f"L-{i}",
            title="Chung cư cao cấp",
            description=f"Căn hộ tại Quận {i % 12 + 1}, TP. Hồ Chí Minh. Diện tích 60m².",
            price_text=f"{2 + i % 5} tỷ",
            area_text="60m²",
        )
        for i in range(5)
    ]
    listings = [normalize(r) for r in raws]
    assert load_listings(dump_listings(listings)) == listings


def test_load_rejects_non_object() -> None:
    with pytest.raises(TypeError):
        load_listings("[1,2,3]\n")
