"""Simulate VN e-commerce order streams."""

from __future__ import annotations

import random

from vnecommerce.schema import Platform, RawOrder

_PLATFORM_DATA: dict[Platform, dict[str, list[str]]] = {
    Platform.SHOPEE: {
        "statuses": ["UNPAID", "READY_TO_SHIP", "SHIPPED", "COMPLETED", "CANCELLED"],
        "payments": ["cod", "shopeepay", "credit_card", "vnpay"],
        "shippings": ["spx_express", "spx_standard", "spx_economy"],
    },
    Platform.TIKI: {
        "statuses": ["queued", "processing", "shipping", "successful", "canceled"],
        "payments": ["cod", "tiki_wallet", "credit_card", "installment"],
        "shippings": ["tiki_delivery", "fast_delivery", "standard_delivery"],
    },
    Platform.LAZADA: {
        "statuses": ["pending", "packed", "shipped", "delivered", "canceled"],
        "payments": ["cod", "credit_card", "lazadawallet", "bank_transfer"],
        "shippings": ["lazada_express", "lazada_standard", "lex"],
    },
}

_VN_PROVINCES = [
    "Hồ Chí Minh",
    "Hà Nội",
    "Đà Nẵng",
    "Bình Dương",
    "Đồng Nai",
    "Hải Phòng",
    "Cần Thơ",
    "An Giang",
]


def simulate_orders(
    n: int = 100,
    seed: int = 42,
) -> list[RawOrder]:
    """Generate *n* synthetic raw orders across platforms."""
    rng = random.Random(seed)
    orders: list[RawOrder] = []
    platforms = list(_PLATFORM_DATA.keys())

    for i in range(n):
        platform = rng.choice(platforms)
        data = _PLATFORM_DATA[platform]
        item_total = rng.randint(50_000, 5_000_000)
        shipping_fee = rng.choice([0, 15_000, 25_000, 35_000, 50_000])
        platform_disc = rng.randint(0, min(50_000, item_total // 10))
        seller_disc = rng.randint(0, min(20_000, item_total // 20))
        buyer_paid = max(0, item_total + shipping_fee - platform_disc - seller_disc)
        commission_rate = rng.uniform(0.05, 0.15)
        seller_receives = int(item_total * (1 - commission_rate))
        buyer_prov = rng.choice(_VN_PROVINCES)
        seller_prov = rng.choice(_VN_PROVINCES)

        orders.append(
            RawOrder(
                platform=platform,
                platform_order_id=f"{platform.value[:3]}-{i:06d}",
                raw_status=rng.choice(data["statuses"]),
                raw_payment=rng.choice(data["payments"]),
                raw_shipping=rng.choice(data["shippings"]),
                item_total_vnd=item_total,
                shipping_fee_vnd=shipping_fee,
                platform_discount_vnd=platform_disc,
                seller_discount_vnd=seller_disc,
                buyer_paid_vnd=buyer_paid,
                seller_receives_vnd=seller_receives,
                tracking_number=f"VN{rng.randint(10**9, 10**10-1)}",
                estimated_delivery_date="2025-06-01",
                buyer_province=buyer_prov,
                seller_province=seller_prov,
            )
        )
    return orders
