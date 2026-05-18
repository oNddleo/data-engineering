"""Seeded synthetic value generator for testing HLL accuracy.

Three patterns:

* **UNIQUE** — every value is distinct (``v_0``, ``v_1``, …). The
  HLL estimate should be very close to ``n``.
* **DUPLICATED** — n unique values, repeated k times each. Tests
  that duplicates don't inflate the estimate (HLL is set-additive).
* **POWER_LAW** — Zipf-distributed: a few values appear millions of
  times, most appear once. Production-realistic.
"""

from __future__ import annotations

import random
from enum import Enum


class StreamPattern(str, Enum):
    """Three input stream patterns."""

    UNIQUE = "UNIQUE"
    DUPLICATED = "DUPLICATED"
    POWER_LAW = "POWER_LAW"


def generate(
    *,
    n: int = 10_000,
    pattern: StreamPattern = StreamPattern.UNIQUE,
    duplication: int = 5,
    skew: float = 1.5,
    seed: int = 0,
) -> list[str]:
    """Generate ``n`` values according to ``pattern``.

    * ``UNIQUE`` — exactly ``n`` distinct values.
    * ``DUPLICATED`` — ``n // duplication`` distinct values, each
      emitted ``duplication`` times.
    * ``POWER_LAW`` — Zipf with exponent ``skew`` over ``n`` distinct
      ranks (head dominates).
    """
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    if duplication < 1:
        raise ValueError(f"duplication must be >= 1, got {duplication}")
    if skew < 0:
        raise ValueError(f"skew must be >= 0, got {skew}")
    rng = random.Random(seed)
    # Namespace values by seed so different seeds produce disjoint streams
    # (otherwise merging two same-pattern sketches gives the same cardinality).
    prefix = f"s{seed}"
    if pattern is StreamPattern.UNIQUE:
        return [f"{prefix}_v_{i:012d}" for i in range(n)]
    if pattern is StreamPattern.DUPLICATED:
        distinct = max(1, n // duplication)
        base = [f"{prefix}_v_{i:012d}" for i in range(distinct)]
        return [rng.choice(base) for _ in range(n)]
    # POWER_LAW
    if n == 0:
        return []
    weights = [1.0 / ((i + 1) ** skew) for i in range(n)]
    base = [f"{prefix}_v_{i:012d}" for i in range(n)]
    return rng.choices(base, weights=weights, k=n)


__all__ = ["StreamPattern", "generate"]
