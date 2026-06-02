"""Scale function k(q) for t-digest centroid bounding.

The merging rule is: two adjacent centroids may be combined into
one *super-centroid* iff ``k(q_right_end) − k(q_left_end) ≤ 1``,
where ``q_left_end`` and ``q_right_end`` are the cumulative-weight
quantile boundaries of the combined centroid.

Dunning's scale function (``k1`` in the paper):

.. math:: k(q) = \\frac{\\delta}{2\\pi} \\arcsin(2q - 1)

Near the tails (q → 0 or q → 1) the derivative blows up, so a unit
step in *k* corresponds to a *small* step in *q* — that's what
forces centroids to stay small in the tails (high relative accuracy)
while allowing them to grow in the middle (where absolute accuracy
matters less).

We expose:

* ``k(q, compression)`` — the scale function itself
* ``max_combined_weight(q_left, total_weight, compression)`` — the
  weight ceiling for a centroid that starts at cumulative quantile
  ``q_left``. Used by the merge step.
"""

from __future__ import annotations

import math


def k(q: float, compression: float) -> float:
    """The k1 scale function value at quantile ``q`` for compression ``δ``."""
    if not 0 <= q <= 1:
        raise ValueError(f"q must be in [0, 1], got {q}")
    if compression < 1:
        raise ValueError(f"compression must be >= 1, got {compression}")
    return compression / (2 * math.pi) * math.asin(2 * q - 1)


def q_from_k(k_val: float, compression: float) -> float:
    """Inverse of ``k(q, δ)`` — recover ``q`` from a scale-function value."""
    if compression < 1:
        raise ValueError(f"compression must be >= 1, got {compression}")
    arg = math.sin(k_val * 2 * math.pi / compression)
    return (arg + 1) / 2


def max_combined_weight(
    q_left: float,
    total_weight: float,
    compression: float,
) -> float:
    """Max weight of a centroid starting at cumulative quantile ``q_left``.

    Derived from the constraint ``k(q_right) − k(q_left) ≤ 1`` →
    ``q_right ≤ q_from_k(k(q_left) + 1, δ)`` →
    ``weight_max = (q_right − q_left) · total_weight``.
    """
    if not 0 <= q_left <= 1:
        raise ValueError(f"q_left must be in [0, 1], got {q_left}")
    if total_weight < 0:
        raise ValueError(f"total_weight must be >= 0, got {total_weight}")
    if compression < 1:
        raise ValueError(f"compression must be >= 1, got {compression}")
    k_left = k(q_left, compression)
    q_right = q_from_k(k_left + 1, compression)
    # Clamp — the inverse can sin-wrap slightly past 1.
    q_right = min(1.0, max(q_left, q_right))
    return (q_right - q_left) * total_weight


__all__ = ["k", "max_combined_weight", "q_from_k"]
