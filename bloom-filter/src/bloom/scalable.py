"""Scalable Bloom filter — grows dynamically (Almeida et al. 2007).

Vanilla Bloom requires knowing ``n`` upfront; if you over-shoot you
waste memory, if you under-shoot the FPR explodes. The scalable
variant maintains a *chain* of sub-filters:

* Insert always goes into the latest (active) sub-filter.
* Lookup walks the chain and returns ``True`` on the first match.
* When the active filter approaches its capacity, append a new one
  with ``capacity_new = capacity_old * growth_factor`` and
  ``target_fpr_new = target_fpr_old * tightening_ratio``.

The per-slice FPRs form a geometric series:

    P_total ≤ sum_i (p_0 · r^i) = p_0 / (1 − r)

where ``r = tightening_ratio < 1``. With defaults (p_0 = 0.01, r = 0.5)
the cumulative FPR stays bounded by 2% — the price of unbounded growth.
"""

from __future__ import annotations

from bloom.filter import add, build, contains
from bloom.schema import ScalableBloom


def build_scalable(
    initial_capacity: int,
    target_fpr: float = 0.01,
    *,
    growth_factor: int = 2,
    tightening_ratio: float = 0.5,
) -> ScalableBloom:
    """Construct a scalable Bloom seeded with one slice at ``initial_capacity``."""
    sb = ScalableBloom(
        initial_capacity=initial_capacity,
        target_fpr=target_fpr,
        growth_factor=growth_factor,
        tightening_ratio=tightening_ratio,
        slices=[],
    )
    sb.slices.append(build(initial_capacity, target_fpr))
    return sb


def add_scalable(sb: ScalableBloom, value: str | bytes | int | float) -> None:
    """Insert ``value`` into the active slice — grow chain if full."""
    active = sb.slices[-1]
    if active.n_items >= active.capacity:
        # Spin up a new wider, tighter slice.
        new_capacity = active.capacity * sb.growth_factor
        new_fpr = active.target_fpr * sb.tightening_ratio
        sb.slices.append(build(new_capacity, new_fpr))
        active = sb.slices[-1]
    add(active, value)


def contains_scalable(
    sb: ScalableBloom,
    value: str | bytes | int | float,
) -> bool:
    """``True`` if ``value`` is in *any* slice."""
    return any(contains(s, value) for s in sb.slices)


def cumulative_fpr_bound(sb: ScalableBloom) -> float:
    """Theoretical upper bound on cumulative FPR for the current chain.

    Useful for monitoring — if this grows above your SLO, the
    filter has scaled past the design point.
    """
    total = 0.0
    rate = sb.target_fpr
    for _ in sb.slices:
        total += rate
        rate *= sb.tightening_ratio
    return total


__all__ = [
    "add_scalable",
    "build_scalable",
    "contains_scalable",
    "cumulative_fpr_bound",
]
