"""Seeded synthetic customer + order streams.

Generates a coherent dataset where the population spans all 10 RFM
segments roughly proportionally — so leaderboard tests and CLV
rollups have something interesting to surface.

The generator works in **two passes**:

1. Assign each customer to a behavioural archetype (champion,
   loyalist, dormant, etc.) — this controls how many orders they
   place and how recently.
2. Emit orders within the observation window with archetype-dependent
   frequency, recency, and gross.

Archetype distributions are chosen to match the empirical buyer
mix on Shopee VN (skewed toward single-order tail, with a thin head
of high-frequency buyers).
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from clvseg.schema import VN_TZ, Customer, Order

_DEFAULT_BASE_TS = datetime(2026, 5, 14, 9, 0, 0, tzinfo=VN_TZ)
_CITIES = ("HCMC", "HN", "DN", "CT", "HP", "NT", "BD", "BTH")


# (label, weight, recency_bias_days, order_count_range, gross_range_vnd)
_ARCHETYPES: tuple[tuple[str, float, tuple[int, int], tuple[int, int], tuple[int, int]], ...] = (
    # Champions: bought today/yesterday, many orders, high gross.
    ("champion", 0.05, (0, 7), (8, 20), (500_000, 3_000_000)),
    # Loyal: recent buyers, moderate frequency.
    ("loyal", 0.10, (3, 30), (4, 10), (200_000, 1_500_000)),
    # Potential loyalists: recent, lower freq.
    ("potential", 0.15, (15, 60), (2, 5), (150_000, 800_000)),
    # New: just bought once.
    ("new", 0.12, (0, 30), (1, 2), (100_000, 500_000)),
    # Need attention: middling recency, low freq.
    ("attention", 0.13, (60, 120), (1, 4), (100_000, 500_000)),
    # Sleeping: old buyers, low spend.
    ("sleep", 0.15, (120, 180), (1, 3), (50_000, 300_000)),
    # At risk: long dormant, high historical freq.
    ("atrisk", 0.08, (180, 270), (5, 15), (300_000, 1_500_000)),
    # Hibernating: long dormant, medium freq.
    ("hibernate", 0.12, (270, 365), (1, 4), (50_000, 250_000)),
    # Lost: very dormant, single order.
    ("lost", 0.10, (365, 730), (1, 2), (50_000, 200_000)),
)


def generate(
    *,
    n_customers: int = 500,
    window_days: int = 180,
    seed: int = 0,
    as_of: datetime | None = None,
) -> tuple[list[Customer], list[Order], datetime]:
    """Generate ``(customers, orders, as_of)`` triple.

    ``window_days`` is the observation window length — must match
    what's passed to ``rfm.score`` and ``clv.forecast``.
    """
    if n_customers < 1:
        raise ValueError("n_customers must be >= 1")
    if window_days < 1:
        raise ValueError("window_days must be >= 1")
    rng = random.Random(seed)
    pivot = as_of or _DEFAULT_BASE_TS

    arche_labels = [a[0] for a in _ARCHETYPES]
    arche_weights = [a[1] for a in _ARCHETYPES]
    by_label = {a[0]: a for a in _ARCHETYPES}

    customers: list[Customer] = []
    orders: list[Order] = []
    order_counter = 0
    for i in range(n_customers):
        archetype = rng.choices(arche_labels, weights=arche_weights, k=1)[0]
        _, _, recency_range, n_orders_range, gross_range = by_label[archetype]
        # Customer registered 1-3 years before the pivot.
        registered = pivot - timedelta(days=rng.randint(180, 1_095))
        cust = Customer(
            customer_id=f"C-{i:06d}",
            registered_at=registered,
            city_key=rng.choice(_CITIES),
        )
        customers.append(cust)
        # Emit orders. The most-recent order falls in the archetype's recency
        # range; older orders are scattered earlier.
        n_orders = rng.randint(*n_orders_range)
        last_recency = rng.randint(*recency_range)
        # Walk backward in time for older orders.
        for j in range(n_orders):
            extra = j * rng.randint(7, 30)  # older orders are 1-4 weeks apart
            days_ago = last_recency + extra
            placed = pivot - timedelta(days=days_ago, hours=rng.randint(0, 23))
            # Only emit orders that fall inside the observation window
            # — older orders are pre-window and not visible to the scorer.
            if days_ago > window_days:
                continue
            orders.append(
                Order(
                    order_id=f"O-{order_counter:08d}",
                    customer_id=cust.customer_id,
                    gross_vnd=rng.randint(*gross_range),
                    n_items=rng.randint(1, 5),
                    placed_at=placed,
                )
            )
            order_counter += 1

    return customers, orders, pivot


__all__ = ["generate"]
