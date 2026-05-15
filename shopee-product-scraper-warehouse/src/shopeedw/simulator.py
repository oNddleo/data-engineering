"""Seeded synthetic Shopee VN dataset."""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from shopeedw.categories import CATEGORIES
from shopeedw.schema import VN_TZ, ShopeeProduct, ShopeeShop

_DEFAULT_BASE_TS = datetime(2026, 5, 14, 9, 0, 0, tzinfo=VN_TZ)


_PROVINCE_CODES = (
    "079",
    "001",
    "031",
    "048",
    "075",
    "077",
    "074",
    "022",
    "027",
    "092",
)
"""HCMC, Hà Nội, Hải Phòng, Đà Nẵng, Đồng Nai, BR-VT, Bình Dương, Quảng Ninh, Bắc Ninh, Cần Thơ."""


_SHOP_NAME_TEMPLATES = (
    "{prefix} Store",
    "{prefix} Official",
    "Cửa hàng {prefix}",
    "{prefix} VN",
    "Shop {prefix}",
)


def _random_shop_name(rng: random.Random) -> str:
    prefix = "".join(rng.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=4))
    return rng.choice(_SHOP_NAME_TEMPLATES).format(prefix=prefix)


def _random_product_name(rng: random.Random, category_key: str) -> str:
    template = {
        "fashion_women": "Áo {modifier} nữ thời trang",
        "fashion_men": "Áo {modifier} nam phong cách",
        "electronics": "Tai nghe {modifier} không dây",
        "computer_laptop": "Laptop {modifier} 14 inch",
        "phones_accessories": "Cáp sạc {modifier} type-C",
        "beauty_health": "Mặt nạ {modifier} dưỡng da",
        "home_living": "Đèn LED {modifier} trang trí",
        "food_beverages": "Cà phê {modifier} 500g",
        "appliances": "Nồi cơm điện {modifier} 1.8L",
    }.get(category_key, "{modifier}")
    modifier = "".join(rng.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=3))
    return template.format(modifier=modifier).strip()


def generate(
    *,
    n_shops: int = 20,
    n_products: int = 100,
    n_snapshots_per_product: int = 1,
    snapshot_interval_minutes: int = 60,
    seed: int = 0,
    base_time: datetime | None = None,
) -> tuple[list[ShopeeShop], list[ShopeeProduct]]:
    """Return ``(shops, products)`` — products may contain multiple snapshots
    per ``(item_id, shop_id)`` when ``n_snapshots_per_product > 1``.
    """
    rng = random.Random(seed)
    base = base_time or _DEFAULT_BASE_TS

    shops: list[ShopeeShop] = []
    for i in range(n_shops):
        shops.append(
            ShopeeShop(
                shop_id=100_000 + i,
                name=_random_shop_name(rng),
                location_province_code=rng.choice(_PROVINCE_CODES),
                rating_x100=rng.randint(420, 495),
                follower_count=rng.randint(100, 200_000),
                response_rate_pct=rng.randint(85, 100),
                is_official=rng.random() < 0.2,
                fetched_at=base,
            )
        )

    products: list[ShopeeProduct] = []
    for i in range(n_products):
        category = rng.choice(list(CATEGORIES.keys()))
        shop = rng.choice(shops)
        item_id = 500_000_000 + i
        original = rng.choice([99_000, 199_000, 299_000, 499_000, 999_000, 1_999_000, 4_999_000])
        # Initial discount between 0% and 30%.
        price = int(original * (1 - rng.uniform(0, 0.3)))
        sold = rng.randint(0, 5_000)
        stock = rng.randint(0, 1_000)
        for j in range(n_snapshots_per_product):
            t = base + timedelta(minutes=snapshot_interval_minutes * j)
            # Subsequent snapshots can drop price further to simulate flash sales.
            if j > 0:
                price = max(int(price * rng.uniform(0.85, 1.0)), 1_000)
            products.append(
                ShopeeProduct(
                    item_id=item_id,
                    shop_id=shop.shop_id,
                    name=_random_product_name(rng, category),
                    category_key=category,
                    price_vnd=price,
                    original_price_vnd=original,
                    stock=stock,
                    sold_count=sold + j * rng.randint(0, 50),
                    rating_x100=rng.randint(380, 500),
                    review_count=rng.randint(0, 10_000),
                    fetched_at=t,
                )
            )

    return shops, products


__all__ = ["generate"]
