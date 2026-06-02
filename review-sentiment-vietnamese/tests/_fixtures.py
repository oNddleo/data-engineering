"""Shared test fixtures."""

from __future__ import annotations

from datetime import datetime

from sentvn.schema import VN_TZ, Review


def make_review(
    *,
    review_id: str = "R-1",
    text: str = "Sản phẩm tốt",
    seller_id: int = 100_000,
    product_id: int = 500_000_001,
    category_key: str = "fashion_women",
    rating_x100: int = 450,
    posted_at: datetime | None = None,
) -> Review:
    return Review(
        review_id=review_id,
        text=text,
        seller_id=seller_id,
        product_id=product_id,
        category_key=category_key,
        rating_x100=rating_x100,
        posted_at=posted_at or datetime(2026, 5, 14, 9, 0, tzinfo=VN_TZ),
    )


__all__ = ["make_review"]
