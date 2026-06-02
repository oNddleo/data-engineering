"""KPI views over ``FactSellerDay`` — what the dashboard reads.

The fact table is the raw shape; the views are the cooked numbers ops
actually looks at. Every view here is a pure function over a list of
``FactSellerDay`` rows — no I/O, no time-zone gotchas (those are
already baked into ``date_key``).

Views:

* :func:`seller_summary`     — per-seller roll-up across the input window.
* :func:`daily_trend`        — per-day roll-up across all sellers.
* :func:`top_sellers_by_gmv` — leaderboard. Returns highest first.
* :func:`worst_sellers_by_return_rate` — surfaces problem shops.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sellermart.schema import FactSellerDay


@dataclass(frozen=True, slots=True)
class SellerSummary:
    """A seller's performance across the input window."""

    seller_id: int
    n_days_active: int
    n_orders: int
    n_units: int
    gmv_vnd: int
    n_returns: int
    refund_vnd: int
    n_reviews: int
    sum_rating_x100: int
    n_unique_buyer_days: int  # sum of n_unique_buyers across days; not de-duplicated

    @property
    def aov_vnd(self) -> int:
        """Average order value, integer VND. ``0`` when there are no orders."""
        if self.n_orders == 0:
            return 0
        return self.gmv_vnd // self.n_orders

    @property
    def return_rate_pct(self) -> float:
        """Returns ÷ orders × 100. ``0.0`` when there are no orders."""
        if self.n_orders == 0:
            return 0.0
        return self.n_returns / self.n_orders * 100

    @property
    def refund_rate_pct(self) -> float:
        """Refund VND ÷ GMV VND × 100. ``0.0`` when GMV is zero."""
        if self.gmv_vnd == 0:
            return 0.0
        return self.refund_vnd / self.gmv_vnd * 100

    @property
    def avg_rating_x100(self) -> float:
        """Mean star rating × 100. ``0.0`` when there are no reviews."""
        if self.n_reviews == 0:
            return 0.0
        return self.sum_rating_x100 / self.n_reviews

    @property
    def nps_proxy(self) -> float:
        """Net-promoter-style proxy in ``[-100, +100]``.

        Promoters are reviews ≥ 4.5★ (rating ≥ 450); detractors are
        ≤ 3.0★ (rating ≤ 300). Without per-review buckets here, we use
        a linear approximation: ``(avg_rating - 350) / 1.50``. At
        avg 5★ → +100, at avg 2★ → -100.
        """
        if self.n_reviews == 0:
            return 0.0
        return (self.avg_rating_x100 - 350) / 1.50


@dataclass(frozen=True, slots=True)
class DailyTrend:
    """One day across all sellers."""

    date_key: int
    n_orders: int
    n_units: int
    gmv_vnd: int
    n_returns: int
    refund_vnd: int

    @property
    def return_rate_pct(self) -> float:
        if self.n_orders == 0:
            return 0.0
        return self.n_returns / self.n_orders * 100


def seller_summary(rows: list[FactSellerDay]) -> dict[int, SellerSummary]:
    """Roll up per-seller across the input window."""
    by_seller: dict[int, list[FactSellerDay]] = defaultdict(list)
    for row in rows:
        by_seller[row.seller_id].append(row)
    out: dict[int, SellerSummary] = {}
    for seller_id, seller_rows in by_seller.items():
        out[seller_id] = SellerSummary(
            seller_id=seller_id,
            n_days_active=len(seller_rows),
            n_orders=sum(r.n_orders for r in seller_rows),
            n_units=sum(r.n_units for r in seller_rows),
            gmv_vnd=sum(r.gmv_vnd for r in seller_rows),
            n_returns=sum(r.n_returns for r in seller_rows),
            refund_vnd=sum(r.refund_vnd for r in seller_rows),
            n_reviews=sum(r.n_reviews for r in seller_rows),
            sum_rating_x100=sum(r.sum_rating_x100 for r in seller_rows),
            n_unique_buyer_days=sum(r.n_unique_buyers for r in seller_rows),
        )
    return out


def daily_trend(rows: list[FactSellerDay]) -> list[DailyTrend]:
    """Roll up per-day across all sellers, sorted ascending by ``date_key``."""
    by_day: dict[int, list[FactSellerDay]] = defaultdict(list)
    for row in rows:
        by_day[row.date_key].append(row)
    out: list[DailyTrend] = []
    for date_key in sorted(by_day):
        day_rows = by_day[date_key]
        out.append(
            DailyTrend(
                date_key=date_key,
                n_orders=sum(r.n_orders for r in day_rows),
                n_units=sum(r.n_units for r in day_rows),
                gmv_vnd=sum(r.gmv_vnd for r in day_rows),
                n_returns=sum(r.n_returns for r in day_rows),
                refund_vnd=sum(r.refund_vnd for r in day_rows),
            )
        )
    return out


def top_sellers_by_gmv(summaries: dict[int, SellerSummary], n: int = 10) -> list[SellerSummary]:
    """Highest GMV first; ties broken by ``seller_id`` ascending."""
    if n <= 0:
        raise ValueError("n must be > 0")
    items = list(summaries.values())
    items.sort(key=lambda s: (-s.gmv_vnd, s.seller_id))
    return items[:n]


def worst_sellers_by_return_rate(
    summaries: dict[int, SellerSummary],
    n: int = 10,
    min_orders: int = 10,
) -> list[SellerSummary]:
    """Highest return rate first, filtered to sellers with ≥ ``min_orders`` orders.

    The ``min_orders`` filter suppresses the "1-order shop with a 100%
    return rate" noise that swamps the actual problem sellers.
    """
    if n <= 0:
        raise ValueError("n must be > 0")
    if min_orders < 0:
        raise ValueError("min_orders must be >= 0")
    items = [s for s in summaries.values() if s.n_orders >= min_orders]
    items.sort(key=lambda s: (-s.return_rate_pct, s.seller_id))
    return items[:n]


__all__ = [
    "DailyTrend",
    "SellerSummary",
    "daily_trend",
    "seller_summary",
    "top_sellers_by_gmv",
    "worst_sellers_by_return_rate",
]
