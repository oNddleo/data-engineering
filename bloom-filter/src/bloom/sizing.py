"""Optimal Bloom-filter dimensioning.

Given ``n`` expected items and a target false-positive rate ``p``, the
classical formulas are:

* **Bits**  ``m = ceil( - n · ln(p) / (ln 2)^2 )``
* **Hashes** ``k = round( (m / n) · ln 2 )``  (clamped to ≥ 1)

The actual FPR with these parameters is
``(1 − e^(−k · n / m))^k`` which we expose as ``estimate_fpr`` for
reverse-direction sizing.

References
----------
Bloom, B.H. (1970). *Space/time trade-offs in hash coding with
allowable errors*. CACM 13(7).
"""

from __future__ import annotations

import math


def optimal_size_bits(capacity: int, target_fpr: float) -> int:
    """Optimal ``m`` for ``n=capacity`` items at FPR ``p=target_fpr``."""
    if capacity < 1:
        raise ValueError(f"capacity must be >= 1, got {capacity}")
    if not 0 < target_fpr < 1:
        raise ValueError(f"target_fpr must be in (0, 1), got {target_fpr}")
    m = -capacity * math.log(target_fpr) / (math.log(2) ** 2)
    return max(1, math.ceil(m))


def optimal_n_hashes(size_bits: int, capacity: int) -> int:
    """Optimal ``k = (m/n) · ln 2`` rounded to nearest int, ≥ 1."""
    if size_bits < 1:
        raise ValueError(f"size_bits must be >= 1, got {size_bits}")
    if capacity < 1:
        raise ValueError(f"capacity must be >= 1, got {capacity}")
    k = (size_bits / capacity) * math.log(2)
    return max(1, round(k))


def estimate_fpr(size_bits: int, n_hashes: int, n_items: int) -> float:
    """The textbook FPR formula for a filter with these parameters."""
    if size_bits < 1:
        raise ValueError(f"size_bits must be >= 1, got {size_bits}")
    if n_hashes < 1:
        raise ValueError(f"n_hashes must be >= 1, got {n_hashes}")
    if n_items < 0:
        raise ValueError(f"n_items must be >= 0, got {n_items}")
    if n_items == 0:
        return 0.0
    exponent = -n_hashes * n_items / size_bits
    return (1 - math.exp(exponent)) ** n_hashes


def estimate_fpr_from_fill(fill_ratio: float, n_hashes: int) -> float:
    """FPR estimated from current bit-fill ratio (the empirical form).

    When the filter is actually populated, ``fill = 1 − e^(−kn/m)``,
    so we can estimate FPR ≈ fill^k directly from observed fill — this
    is more accurate than the closed-form when items repeat.
    """
    if not 0 <= fill_ratio <= 1:
        raise ValueError(f"fill_ratio must be in [0, 1], got {fill_ratio}")
    if n_hashes < 1:
        raise ValueError(f"n_hashes must be >= 1, got {n_hashes}")
    return fill_ratio**n_hashes


def bits_per_item(target_fpr: float) -> float:
    """Bits required per inserted item for ``target_fpr`` (asymptotic).

    Reciprocal of ``(ln 2)^2 / |ln p|`` — useful for back-of-envelope
    sizing without specifying ``n`` (e.g. "1% needs 9.6 bits/item").
    """
    if not 0 < target_fpr < 1:
        raise ValueError(f"target_fpr must be in (0, 1), got {target_fpr}")
    return -math.log(target_fpr) / (math.log(2) ** 2)


__all__ = [
    "bits_per_item",
    "estimate_fpr",
    "estimate_fpr_from_fill",
    "optimal_n_hashes",
    "optimal_size_bits",
]
