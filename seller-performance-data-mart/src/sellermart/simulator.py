"""Seeded synthetic source streams for the data mart.

Generates a coherent (orders, returns, reviews) triple where:

* every return references a real order;
* every review references a real order;
* return / review timestamps come *after* the order timestamp;
* per-seller order rate follows a deterministic distribution so
  ranking tests are stable.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from sellermart.schema import VN_TZ
from sellermart.sources import Order, Return, Review

_DEFAULT_BASE_TS = datetime(2026, 5, 1, 9, 0, 0, tzinfo=VN_TZ)

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
    n_days: int = 14,
    n_sellers: int = 12,
    n_buyers: int = 300,
    avg_orders_per_seller_per_day: float = 6.0,
    return_rate: float = 0.08,
    review_rate: float = 0.45,
    seed: int = 0,
    base_time: datetime | None = None,
) -> tuple[list[Order], list[Return], list[Review]]:
    """Generate three coherent source streams.

    Sellers are not uniform — seller 0 gets a 3× weight so leaderboard
    tests have a clear winner.
    """
    if n_days < 1:
        raise ValueError("n_days must be >= 1")
    if n_sellers < 1:
        raise ValueError("n_sellers must be >= 1")
    if n_buyers < 1:
        raise ValueError("n_buyers must be >= 1")
    if not 0.0 <= return_rate <= 1.0:
        raise ValueError("return_rate must be in [0, 1]")
    if not 0.0 <= review_rate <= 1.0:
        raise ValueError("review_rate must be in [0, 1]")
    rng = random.Random(seed)
    base = base_time or _DEFAULT_BASE_TS

    seller_ids = [100_000 + i for i in range(n_sellers)]
    weights = [3.0 if i == 0 else 1.0 for i in range(n_sellers)]
    buyer_ids = [f"B-{i:05d}" for i in range(n_buyers)]

    orders: list[Order] = []
    order_counter = 0
    for day in range(n_days):
        for _ in range(int(avg_orders_per_seller_per_day * n_sellers)):
            seller_id = rng.choices(seller_ids, weights=weights, k=1)[0]
            buyer = rng.choice(buyer_ids)
            category = rng.choice(_CATEGORIES)
            units = rng.choice((1, 1, 1, 2, 2, 3))
            unit_price = rng.choice((49_000, 99_000, 199_000, 299_000, 499_000, 990_000))
            created = base + timedelta(days=day, minutes=rng.randint(0, 23 * 60))
            orders.append(
                Order(
                    order_id=f"O-{order_counter:08d}",
                    seller_id=seller_id,
                    buyer_id=buyer,
                    category_key=category,
                    n_units=units,
                    gross_vnd=units * unit_price,
                    created_at=created,
                )
            )
            order_counter += 1

    returns: list[Return] = []
    for order in orders:
        if rng.random() < return_rate:
            refund = int(order.gross_vnd * rng.choice((0.5, 1.0, 1.0, 1.0)))
            returns.append(
                Return(
                    return_id=f"RT-{order.order_id}",
                    order_id=order.order_id,
                    seller_id=order.seller_id,
                    refund_vnd=refund,
                    created_at=order.created_at + timedelta(days=rng.randint(1, 7)),
                )
            )

    reviews: list[Review] = []
    for order in orders:
        if rng.random() < review_rate:
            rating = rng.choices(
                (500, 450, 400, 350, 300, 200, 100),
                weights=(40, 25, 15, 8, 5, 4, 3),
                k=1,
            )[0]
            reviews.append(
                Review(
                    review_id=f"RV-{order.order_id}",
                    order_id=order.order_id,
                    seller_id=order.seller_id,
                    rating_x100=rating,
                    created_at=order.created_at + timedelta(days=rng.randint(1, 10)),
                )
            )

    return orders, returns, reviews


__all__ = ["generate"]
