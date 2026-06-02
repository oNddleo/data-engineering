"""Map RFM scores → named CRM segments.

The mapping function ``rfm_to_segment(r, f, m)`` is **pure** — no
ordering dependencies, no I/O — so it composes cleanly with the
scoring engine and the transition tracker.

The mapping is the standard one used by major VN-marketplace CRM
teams (Shopee Seller Hub, Lazada Retention Tools):

| R   | F   | Segment             | Action                          |
| --- | --- | ------------------- | ------------------------------- |
| 5   | 5   | CHAMPIONS           | reward, upsell, ask for review  |
| 4-5 | 3-4 | LOYAL_CUSTOMERS     | retention campaign              |
| 5   | 1-2 | NEW_CUSTOMERS       | welcome flow, 2nd-order push    |
| 3-4 | 4-5 | POTENTIAL_LOYALISTS | nurture                         |
| 3   | 1-3 | NEED_ATTENTION      | reactivation offer              |
| 2-3 | 2-3 | ABOUT_TO_SLEEP      | win-back coupon                 |
| 1-2 | 4-5 | AT_RISK             | high-value reactivation         |
| 1   | 4-5 | CANT_LOSE_THEM      | escalation: CS phone outreach   |
| 1-2 | 1-3 | HIBERNATING         | low-cost email blast            |
| 1   | 1   | LOST                | suppress / re-acquisition only  |

``m_score`` is intentionally **not** part of the segment mapping —
that mirrors industry practice. Monetary is used for ranking
*within* a segment (top spenders in CHAMPIONS get the upsell, not
just "any champion"), not for picking the segment itself.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from clvseg.schema import Segment

if TYPE_CHECKING:
    from clvseg.schema import RFMScore


def rfm_to_segment(r: int, f: int, m: int) -> Segment:
    """Pure mapping from ``(R, F, M)`` to a named :class:`Segment`.

    ``m`` is part of the signature for forward-compatibility (some
    CRM teams swap in a monetary-aware variant) but the canonical
    mapping ignores it.
    """
    if not all(1 <= v <= 5 for v in (r, f, m)):
        raise ValueError(f"R, F, M must each be in [1, 5]; got ({r}, {f}, {m})")
    if r == 5 and f == 5:
        return Segment.CHAMPIONS
    if r == 5 and f >= 3:
        return Segment.LOYAL_CUSTOMERS
    if r == 5:
        return Segment.NEW_CUSTOMERS
    if r == 4 and f >= 3:
        return Segment.LOYAL_CUSTOMERS
    if r == 4 and f >= 1:
        return Segment.POTENTIAL_LOYALISTS
    if r == 3 and f >= 4:
        return Segment.POTENTIAL_LOYALISTS
    if r == 3:
        return Segment.NEED_ATTENTION
    if r == 2 and f >= 4:
        return Segment.AT_RISK
    if r == 2:
        return Segment.ABOUT_TO_SLEEP
    # r == 1
    if f == 5:
        return Segment.CANT_LOSE_THEM
    if f >= 4:
        return Segment.AT_RISK
    if f >= 2:
        return Segment.HIBERNATING
    return Segment.LOST


def classify_all(scores: list[RFMScore]) -> dict[str, Segment]:
    """Build ``{customer_id: Segment}`` from a list of RFM scores."""
    return {s.customer_id: rfm_to_segment(s.r_score, s.f_score, s.m_score) for s in scores}


def segment_distribution(assignments: dict[str, Segment]) -> dict[Segment, int]:
    """Count of customers per segment — for dashboards. Zero-filled."""
    counts: dict[Segment, int] = {seg: 0 for seg in Segment}
    for seg in assignments.values():
        counts[seg] += 1
    return counts


def top_in_segment(
    scores: list[RFMScore],
    assignments: dict[str, Segment],
    segment: Segment,
    n: int = 10,
) -> list[RFMScore]:
    """Top ``n`` customers within ``segment``, ranked by monetary spend desc.

    Ties broken by recency (lower ``recency_days`` first), then
    ``customer_id`` ascending — so the output is fully deterministic.
    """
    if n <= 0:
        raise ValueError("n must be > 0")
    in_seg = [s for s in scores if assignments.get(s.customer_id) is segment]
    in_seg.sort(key=lambda s: (-s.monetary_vnd, s.recency_days, s.customer_id))
    return in_seg[:n]


def transitions(
    before: dict[str, Segment],
    after: dict[str, Segment],
) -> dict[tuple[Segment, Segment], int]:
    """Count transitions ``(before, after)`` for customers present in both maps.

    Customers in only one map are skipped — they're a new acquisition
    or a churned record and belong on a separate dashboard.
    """
    out: dict[tuple[Segment, Segment], int] = defaultdict(int)
    for cid, before_seg in before.items():
        after_seg = after.get(cid)
        if after_seg is None:
            continue
        out[(before_seg, after_seg)] += 1
    return dict(out)


__all__ = [
    "classify_all",
    "rfm_to_segment",
    "segment_distribution",
    "top_in_segment",
    "transitions",
]
