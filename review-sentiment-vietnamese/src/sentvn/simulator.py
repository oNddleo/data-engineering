"""Seeded synthetic Vietnamese review generator."""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from sentvn.schema import VN_TZ, Review

_DEFAULT_BASE_TS = datetime(2026, 5, 14, 9, 0, 0, tzinfo=VN_TZ)


# Canned VN review templates spanning the three sentiment classes.
_POSITIVE_TEMPLATES = (
    "Sản phẩm rất tốt, giao hàng nhanh",
    "Tuyệt vời, mặc đẹp lắm",
    "Ưng quá, mua thêm lần nữa, shop rất nhanh",
    "Chất lượng đỉnh, đáng đồng tiền",
    "Yêu shop, sản phẩm xinh lắm",
    "Hài lòng, sẽ ủng hộ tiếp",
)

_NEGATIVE_TEMPLATES = (
    "Sản phẩm tệ, không như mô tả",
    "Giao hàng quá chậm, kém chất lượng",
    "Hàng giả, không nên mua",
    "Hỏng ngay sau khi mở hộp",
    "Đắt mà chán, không đáng tiền",
    "Bẩn, rách, shop lừa",
)

_NEUTRAL_TEMPLATES = (
    "Sản phẩm tạm được",
    "Cũng bình thường, không có gì đặc biệt",
    "Sản phẩm ok, giao hàng cũng tạm",
    "Không có nhận xét gì thêm",
    "Bình thường, đúng như giá tiền",
)

_NEGATED_POSITIVE = (
    "Không tốt như mô tả",
    "Không đẹp lắm",
    "Chẳng nhanh như quảng cáo",
)


_CATEGORIES = (
    "fashion_women",
    "fashion_men",
    "electronics",
    "computer_laptop",
    "phones_accessories",
    "beauty_health",
    "home_living",
    "food_beverages",
    "appliances",
)


def generate(
    *,
    n_reviews: int = 200,
    n_sellers: int = 20,
    n_products: int = 60,
    seed: int = 0,
    base_time: datetime | None = None,
    pct_positive: float = 0.55,
    pct_negative: float = 0.25,
    pct_negated_positive: float = 0.05,
) -> list[Review]:
    """Build ``n_reviews`` reviews with controllable sentiment mix.

    The remaining fraction (``1 − pos − neg − negated``) is neutral.
    ``pct_negated_positive`` exercises the negator handling — those
    reviews use a positive word but with a leading negator, so a
    naive bag-of-words classifier mis-labels them.
    """
    if not 0 <= pct_positive + pct_negative + pct_negated_positive <= 1:
        raise ValueError("sentiment percentages must sum to <= 1")
    rng = random.Random(seed)
    base = base_time or _DEFAULT_BASE_TS
    sellers = list(range(100_000, 100_000 + n_sellers))
    products = list(range(500_000_000, 500_000_000 + n_products))
    out: list[Review] = []
    for i in range(n_reviews):
        roll = rng.random()
        if roll < pct_positive:
            text = rng.choice(_POSITIVE_TEMPLATES)
            rating = rng.randint(450, 500)
        elif roll < pct_positive + pct_negative:
            text = rng.choice(_NEGATIVE_TEMPLATES)
            rating = rng.randint(100, 250)
        elif roll < pct_positive + pct_negative + pct_negated_positive:
            text = rng.choice(_NEGATED_POSITIVE)
            rating = rng.randint(150, 300)
        else:
            text = rng.choice(_NEUTRAL_TEMPLATES)
            rating = rng.randint(300, 400)
        out.append(
            Review(
                review_id=f"R-{i:06d}",
                text=text,
                seller_id=rng.choice(sellers),
                product_id=rng.choice(products),
                category_key=rng.choice(_CATEGORIES),
                rating_x100=rating,
                posted_at=base + timedelta(minutes=i * 5),
            )
        )
    return out


__all__ = ["generate"]
