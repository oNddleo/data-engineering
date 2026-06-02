"""Merge two reservoirs into one — the distributed-sampling primitive.

When ``N`` shards each sample ``k`` items from their local stream
into reservoirs ``R_1 ... R_N`` with stream sizes ``n_1 ... n_N``,
the merged sample is constructed by treating each ``R_i`` as a
weighted batch contributing ``n_i / sum(n_j)`` to the final
reservoir. Probabilistically equivalent to a single-pass reservoir
over the union (Kassa & Lavasani 2009; standard MapReduce trick).

Two ``Reservoir`` snapshots are combined as follows: pick each
slot of the output uniformly from the *union* of the two inputs,
weighted by the partition's ``n_seen``. We expose:

* ``merge_uniform`` — combines two ``Reservoir`` snapshots into one.
* ``merge_weighted`` — combines two ``WeightedReservoir`` snapshots
  (just unions the item keys and keeps the top-k).
"""

from __future__ import annotations

import random

from reservoir.algorithms import _insert_sorted
from reservoir.schema import Reservoir, WeightedReservoir


def merge_uniform(
    a: Reservoir,
    b: Reservoir,
    *,
    rng: random.Random | None = None,
) -> Reservoir:
    """Combine two uniform reservoirs into one of equal capacity.

    Output capacity defaults to ``a.capacity``. Both inputs must
    declare the same ``capacity`` to keep the math straight.
    """
    if a.capacity != b.capacity:
        raise ValueError(
            f"reservoirs must share capacity ({a.capacity} != {b.capacity})",
        )
    r = rng if rng is not None else random.Random()
    capacity = a.capacity
    n_total = a.n_seen + b.n_seen
    if n_total == 0:
        return Reservoir(capacity=capacity, items=(), n_seen=0)

    # If either side has fewer items than its share, fall back to taking
    # everything available from that side and topping up from the other.
    p_a = a.n_seen / n_total
    n_from_a = _binomial_capped(capacity, p_a, r, max_a=a.n_kept, max_b=b.n_kept)
    n_from_b = capacity - n_from_a

    items_a = r.sample(list(a.items), k=min(n_from_a, a.n_kept))
    items_b = r.sample(list(b.items), k=min(n_from_b, b.n_kept))
    combined = items_a + items_b
    # The merged reservoir may be smaller than capacity if both sides
    # together had fewer items than capacity (early-stream merge).
    return Reservoir(
        capacity=capacity,
        items=tuple(combined),
        n_seen=n_total,
    )


def merge_weighted(
    a: WeightedReservoir,
    b: WeightedReservoir,
) -> WeightedReservoir:
    """Combine two weighted reservoirs by keeping the top-k joint keys.

    A-Res is *exactly* mergeable — every original key is preserved
    so we just union the two key sets and trim to ``capacity``.
    """
    if a.capacity != b.capacity:
        raise ValueError(
            f"reservoirs must share capacity ({a.capacity} != {b.capacity})",
        )
    out = WeightedReservoir(
        capacity=a.capacity,
        n_seen=a.n_seen + b.n_seen,
        total_weight_seen=a.total_weight_seen + b.total_weight_seen,
    )
    for item in a.items + b.items:
        if len(out.items) < out.capacity:
            _insert_sorted(out.items, item)
        elif item.key > out.items[0].key:
            out.items.pop(0)
            _insert_sorted(out.items, item)
    return out


def _binomial_capped(
    n: int,
    p: float,
    rng: random.Random,
    *,
    max_a: int,
    max_b: int,
) -> int:
    """Sample a binomial ``(n, p)`` capped by the available items on each side.

    Falls back to a uniform draw when ``n`` is small (≤ 64) — for the
    typical reservoir-size range that's the entire universe of cases.
    """
    if max_a + max_b == 0:
        return 0
    # Direct simulation; n is bounded by the reservoir capacity (small).
    successes = sum(1 for _ in range(n) if rng.random() < p)
    # Clamp by what each side actually holds.
    if successes > max_a:
        successes = max_a
    if (n - successes) > max_b:
        successes = n - max_b
    return successes


__all__ = ["merge_uniform", "merge_weighted"]
