"""End-to-end normalizer tests."""

from __future__ import annotations

from vnprop.normalizer import RawListing, normalize
from vnprop.schema import PropertyKind


def test_normalize_basic_apartment() -> None:
    raw = RawListing(
        listing_id="L-1",
        title="Chung cư cao cấp Q.2",
        description="Căn hộ 3 phòng ngủ, 2 WC tại Phường Thảo Điền, Quận 2, TP. Hồ Chí Minh. Diện tích 80m².",
        price_text="3.5 tỷ",
        area_text="80m²",
    )
    out = normalize(raw)
    assert out.kind is PropertyKind.APARTMENT
    assert out.area_m2 == 80
    assert out.price_vnd == 3_500_000_000
    assert "Hồ Chí Minh" in out.province
    assert out.bedrooms == 3
    assert out.bathrooms == 2


def test_normalize_villa() -> None:
    raw = RawListing(
        listing_id="L-2",
        title="Biệt thự Thảo Điền",
        description="Biệt thự sân vườn 4 phòng ngủ, 3 WC. Diện tích 300m².",
        price_text="25 tỷ",
        area_text="300m²",
    )
    out = normalize(raw)
    assert out.kind is PropertyKind.VILLA


def test_normalize_land() -> None:
    raw = RawListing(
        listing_id="L-3",
        title="Đất nền Củ Chi",
        description="Đất thổ cư tại Xã Tân Phú Trung, Huyện Củ Chi.",
        price_text="2,5 tỷ",
        area_text="500m²",
    )
    out = normalize(raw)
    assert out.kind is PropertyKind.LAND


def test_normalize_unknown_kind() -> None:
    """No matching keyword → OTHER."""
    raw = RawListing(
        listing_id="L-9",
        title="Listing X",
        description="Some place at TP. Hà Nội",
        price_text="1 tỷ",
        area_text="50m²",
    )
    out = normalize(raw)
    assert out.kind is PropertyKind.OTHER


def test_normalize_price_per_m2() -> None:
    raw = RawListing(
        listing_id="L-4",
        title="Chung cư cao cấp",
        description="Căn hộ 50m².",
        price_text="2 tỷ",
        area_text="50m²",
    )
    out = normalize(raw)
    # 2_000_000_000 / 50 = 40,000,000 VND/m²
    assert out.price_per_m2_vnd == 40_000_000
