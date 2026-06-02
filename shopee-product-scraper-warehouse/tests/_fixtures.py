"""Shared test fixtures + factories."""

from __future__ import annotations

from datetime import datetime, timedelta

from shopeedw.schema import VN_TZ, ShopeeProduct, ShopeeShop


def make_product(
    *,
    item_id: int = 500_000_001,
    shop_id: int = 100_000,
    name: str = "Sample product",
    category_key: str = "fashion_women",
    price: int = 199_000,
    original_price: int | None = None,
    stock: int = 100,
    sold: int = 50,
    rating_x100: int = 480,
    review_count: int = 25,
    fetched_at: datetime | None = None,
) -> ShopeeProduct:
    # Default original_price = price (no discount) if caller didn't supply one.
    # The schema invariant requires original >= price, so deriving it from the
    # caller's price avoids surprise validation errors in tests that pass a
    # bespoke `price` without thinking about the original.
    return ShopeeProduct(
        item_id=item_id,
        shop_id=shop_id,
        name=name,
        category_key=category_key,
        price_vnd=price,
        original_price_vnd=original_price if original_price is not None else price,
        stock=stock,
        sold_count=sold,
        rating_x100=rating_x100,
        review_count=review_count,
        fetched_at=fetched_at or datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ),
    )


def make_shop(
    *,
    shop_id: int = 100_000,
    name: str = "Test Shop",
    province: str = "079",
    rating_x100: int = 480,
    follower_count: int = 5_000,
    response_rate_pct: int = 95,
    is_official: bool = False,
    fetched_at: datetime | None = None,
) -> ShopeeShop:
    return ShopeeShop(
        shop_id=shop_id,
        name=name,
        location_province_code=province,
        rating_x100=rating_x100,
        follower_count=follower_count,
        response_rate_pct=response_rate_pct,
        is_official=is_official,
        fetched_at=fetched_at or datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ),
    )


def t_at(minutes: int) -> datetime:
    return datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ) + timedelta(minutes=minutes)


__all__ = ["make_product", "make_shop", "t_at"]
