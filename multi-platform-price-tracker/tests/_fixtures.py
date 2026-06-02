"""Shared test fixtures + factories."""

from __future__ import annotations

from datetime import datetime, timedelta

from multiprice.schema import VN_TZ, Platform, ProductObservation, SkuMapping


def make_mapping(
    *,
    canonical_sku: str = "SKU-1",
    platform: Platform = Platform.SHOPEE,
    platform_item_id: str = "sp-001",
) -> SkuMapping:
    return SkuMapping(
        canonical_sku=canonical_sku,
        platform=platform,
        platform_item_id=platform_item_id,
    )


def make_obs(
    *,
    canonical_sku: str = "SKU-1",
    platform: Platform = Platform.SHOPEE,
    platform_item_id: str = "sp-001",
    name: str = "Sample",
    price: int = 100_000,
    original_price: int | None = None,
    stock: int = 50,
    observed_at: datetime | None = None,
) -> ProductObservation:
    return ProductObservation(
        canonical_sku=canonical_sku,
        platform=platform,
        platform_item_id=platform_item_id,
        name=name,
        price_vnd=price,
        original_price_vnd=original_price if original_price is not None else price,
        stock=stock,
        observed_at=observed_at or datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ),
    )


def t_at(minutes: int) -> datetime:
    return datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ) + timedelta(minutes=minutes)


__all__ = ["make_mapping", "make_obs", "t_at"]
