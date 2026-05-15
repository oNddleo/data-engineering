"""ETL: orders + returns + reviews → ``FactSellerDay`` rows.

The pipeline is a three-stage roll-up:

1. **Bucket by (seller, day-in-VN_TZ)**. The day is derived from
   ``created_at`` converted to ``VN_TZ`` — UTC orders that crossed
   midnight in VN time bucket on the *VN* day, not the UTC day. This
   is the recurring bug in non-VN-aware marts.
2. **Aggregate** counts, GMV, returns, refund amount, review count and
   sum of ratings × 100 inside each bucket.
3. **Materialise** one ``FactSellerDay`` per bucket. Empty buckets
   (zero orders) are dropped — the mart is sparse.

Returns are joined to orders via ``order_id``; the return is credited
to the **order's** day, not the day the return was processed. This is
how Shopee Seller Center reports it.

Reviews use their own ``created_at`` for bucketing (a review filed
3 days after the order shows up on the review day's row, not the
order day's row). This matches the way ops watches the NPS proxy.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from sellermart.schema import VN_TZ, FactSellerDay, make_date_key

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime

    from sellermart.sources import Order, Return, Review


class _Bucket:
    """Mutable accumulator used during the roll-up. Never escapes the ETL."""

    __slots__ = (
        "buyers",
        "gmv_vnd",
        "n_orders",
        "n_returns",
        "n_reviews",
        "n_units",
        "refund_vnd",
        "sum_rating_x100",
    )

    def __init__(self) -> None:
        self.n_orders = 0
        self.n_units = 0
        self.gmv_vnd = 0
        self.n_returns = 0
        self.refund_vnd = 0
        self.n_reviews = 0
        self.sum_rating_x100 = 0
        self.buyers: set[str] = set()


def _vn_date_key(dt_value: datetime) -> int:
    """Convert a tz-aware datetime → ``YYYYMMDD`` int in ``VN_TZ``.

    UTC orders that crossed midnight in VN time bucket on the VN day,
    not the UTC day — the recurring bug in non-VN-aware marts.
    """
    if dt_value.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    local = dt_value.astimezone(VN_TZ)
    return make_date_key(local.date())


def build_fact_seller_day(
    orders: Iterable[Order],
    returns: Iterable[Return],
    reviews: Iterable[Review],
) -> list[FactSellerDay]:
    """Roll the three source streams into a sparse ``FactSellerDay`` list.

    The output is sorted by ``(seller_id, date_key)`` — stable for
    snapshot tests and downstream window functions.
    """
    buckets: dict[tuple[int, int], _Bucket] = defaultdict(_Bucket)

    # 1. Orders: open a bucket and seed n_orders / n_units / gmv / buyers.
    order_day: dict[str, tuple[int, int]] = {}
    for order in orders:
        key = (order.seller_id, _vn_date_key(order.created_at))
        order_day[order.order_id] = key
        bucket = buckets[key]
        bucket.n_orders += 1
        bucket.n_units += order.n_units
        bucket.gmv_vnd += order.gross_vnd
        bucket.buyers.add(order.buyer_id)

    # 2. Returns: credit the originating order's (seller, day) bucket.
    # Orphan returns (no matching order in the window) are dropped — the
    # source system can replay them in a later batch.
    for ret in returns:
        key_opt = order_day.get(ret.order_id)
        if key_opt is None:
            continue
        bucket = buckets[key_opt]
        bucket.n_returns += 1
        bucket.refund_vnd += ret.refund_vnd

    # 3. Reviews: bucket on the review's own day in VN_TZ.
    for review in reviews:
        key = (review.seller_id, _vn_date_key(review.created_at))
        bucket = buckets[key]
        bucket.n_reviews += 1
        bucket.sum_rating_x100 += review.rating_x100

    out: list[FactSellerDay] = []
    for (seller_id, date_key), bucket in sorted(buckets.items()):
        # Drop buckets that exist only because of an orphan review with
        # no orders that day — the grain demands at least one order.
        if bucket.n_orders == 0:
            continue
        out.append(
            FactSellerDay(
                seller_id=seller_id,
                date_key=date_key,
                n_orders=bucket.n_orders,
                n_units=bucket.n_units,
                gmv_vnd=bucket.gmv_vnd,
                n_returns=bucket.n_returns,
                refund_vnd=bucket.refund_vnd,
                n_reviews=bucket.n_reviews,
                sum_rating_x100=bucket.sum_rating_x100,
                n_unique_buyers=len(bucket.buyers),
            )
        )
    return out


__all__ = ["build_fact_seller_day"]
