"""Seeded synthetic value streams for testing + benchmarking.

Three patterns:

* **UNIFORM** — every value chosen uniformly from a vocabulary
  of size ``vocab_size``. Heavy-tail-free.
* **ZIPF** — Zipf-distributed picks with configurable exponent.
  A few values dominate (realistic e-commerce / web log).
* **HEAVY_HITTERS** — a fixed set of K "heavy" values dominate,
  with a uniform tail. Best-case input for top-K accuracy.

Values are seed-namespaced (``s<seed>_v_<i>``) so disjoint seeds
produce disjoint vocabularies — useful for merging tests.
"""

from __future__ import annotations

import random
from enum import Enum


class StreamPattern(str, Enum):
    """Three input stream patterns."""

    UNIFORM = "UNIFORM"
    ZIPF = "ZIPF"
    HEAVY_HITTERS = "HEAVY_HITTERS"


def generate(
    *,
    n: int = 10_000,
    vocab_size: int = 1_000,
    pattern: StreamPattern = StreamPattern.ZIPF,
    skew: float = 1.5,
    n_heavy: int = 10,
    heavy_fraction: float = 0.6,
    seed: int = 0,
) -> list[str]:
    """Generate ``n`` values drawn from the chosen distribution.

    * ``UNIFORM`` — flat over ``vocab_size`` distinct values.
    * ``ZIPF`` — Zipf weights ``1/i^skew`` over ``vocab_size`` items.
    * ``HEAVY_HITTERS`` — ``heavy_fraction`` of mass on ``n_heavy``
      values, rest uniform over the tail.
    """
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    if vocab_size < 1:
        raise ValueError(f"vocab_size must be >= 1, got {vocab_size}")
    if skew < 0:
        raise ValueError(f"skew must be >= 0, got {skew}")
    if not 0 <= heavy_fraction <= 1:
        raise ValueError(f"heavy_fraction must be in [0, 1], got {heavy_fraction}")
    if n_heavy < 1:
        raise ValueError(f"n_heavy must be >= 1, got {n_heavy}")

    rng = random.Random(seed)
    prefix = f"s{seed}"
    vocab = [f"{prefix}_v_{i:08d}" for i in range(vocab_size)]
    if pattern is StreamPattern.UNIFORM:
        return [rng.choice(vocab) for _ in range(n)]
    if pattern is StreamPattern.ZIPF:
        weights = [1.0 / ((i + 1) ** skew) for i in range(vocab_size)]
        return rng.choices(vocab, weights=weights, k=n)
    # HEAVY_HITTERS
    heavy = vocab[:n_heavy]
    tail = vocab[n_heavy:] or heavy  # avoid empty tail
    out: list[str] = []
    for _ in range(n):
        if rng.random() < heavy_fraction:
            out.append(rng.choice(heavy))
        else:
            out.append(rng.choice(tail))
    return out


__all__ = ["StreamPattern", "generate"]
