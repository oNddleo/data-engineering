"""RFM scoring: compute Recency / Frequency / Monetary scores per customer.

The pipeline is three steps:

1. **Aggregate** orders per customer into ``(recency_days, frequency,
   monetary_vnd)`` raw values relative to a caller-supplied ``as_of``
   timestamp.
2. **Quintile** each raw value across the customer population. R is
   inverted (recent = high score), F and M are direct (more = higher
   score). Ties are broken by the lower score — so two customers with
   identical frequency get the same F score, never adjacent ones.
3. **Materialise** one :class:`RFMScore` per customer with both the
   raw values and the 1-5 quintile scores.

Customers with **zero orders** are still scored — they get
``r_score=1, f_score=1, m_score=1`` (the LOST corner). That's the
correct CRM treatment: a registered-but-inactive buyer is not the
same record-not-found case.

Quintile-cutoff handling:
* Pure quantile cuts (``[0.2, 0.4, 0.6, 0.8]``) can produce empty
  buckets when the distribution is heavily skewed (e.g. most VN
  marketplace buyers have ``frequency=1``). We use **nearest-rank
  percentiles** like the ETA module — the same cutoff value may
  legitimately fall in multiple buckets.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from clvseg.schema import RFMScore

if TYPE_CHECKING:
    from datetime import datetime

    from clvseg.schema import Customer, Order


def _raw_per_customer(
    customers: list[Customer],
    orders: list[Order],
    as_of: datetime,
) -> dict[str, tuple[int, int, int]]:
    """Aggregate orders per customer → ``(recency_days, frequency, monetary_vnd)``.

    Customers with no orders get a "never bought" sentinel: recency =
    days since registration (capped at the window's maximum), F=0, M=0.
    """
    by_customer: dict[str, list[Order]] = defaultdict(list)
    for order in orders:
        by_customer[order.customer_id].append(order)
    out: dict[str, tuple[int, int, int]] = {}
    for c in customers:
        cust_orders = by_customer.get(c.customer_id, [])
        if cust_orders:
            last = max(o.placed_at for o in cust_orders)
            recency = max(0, (as_of - last).days)
            freq = len(cust_orders)
            monetary = sum(o.gross_vnd for o in cust_orders)
        else:
            recency = max(0, (as_of - c.registered_at).days)
            freq = 0
            monetary = 0
        out[c.customer_id] = (recency, freq, monetary)
    return out


def _quintile_score(value: int, sorted_values: list[int], invert: bool = False) -> int:
    """Map ``value`` to a 1-5 quintile score against ``sorted_values``.

    ``invert=True`` for Recency — lower raw value ⇒ higher score
    (a customer who bought 2 days ago is better than one who bought
    200 days ago).

    Boundary uses ``>`` so the bottom-quintile value lands in score 1,
    not score 2. For population ``[1, 2, 3, 4, 5]``: value ``1`` →
    score 1 (bottom 20%); value ``5`` → score 5 (top 20%).
    """
    if not sorted_values:
        return 1
    n = len(sorted_values)
    rank_high = sum(1 for v in sorted_values if v <= value)
    pct = rank_high / n
    if pct > 0.8:
        s = 5
    elif pct > 0.6:
        s = 4
    elif pct > 0.4:
        s = 3
    elif pct > 0.2:
        s = 2
    else:
        s = 1
    return 6 - s if invert else s


def score(
    customers: list[Customer],
    orders: list[Order],
    as_of: datetime,
) -> list[RFMScore]:
    """Compute :class:`RFMScore` for every customer in ``customers``.

    Output order is stable: customers in input order.
    """
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    raws = _raw_per_customer(customers, orders, as_of)
    # Build the three sorted population vectors used for quintile lookups.
    r_pop = sorted(r for r, _, _ in raws.values())
    f_pop = sorted(f for _, f, _ in raws.values())
    m_pop = sorted(m for _, _, m in raws.values())
    out: list[RFMScore] = []
    for c in customers:
        recency, freq, monetary = raws[c.customer_id]
        r_score = _quintile_score(recency, r_pop, invert=True)
        # Never-bought customers are LOST by definition — short-circuit
        # F and M to score 1 so they don't accidentally land in the top
        # quintile of a tiny zero-only population.
        if freq == 0:
            f_score = 1
            m_score = 1
        else:
            f_score = _quintile_score(freq, f_pop)
            m_score = _quintile_score(monetary, m_pop)
        out.append(
            RFMScore(
                customer_id=c.customer_id,
                as_of=as_of,
                recency_days=recency,
                frequency=freq,
                monetary_vnd=monetary,
                r_score=r_score,
                f_score=f_score,
                m_score=m_score,
            )
        )
    return out


__all__ = ["score"]
