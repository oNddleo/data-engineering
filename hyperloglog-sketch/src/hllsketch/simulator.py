"""Simulate distinct-element streams for testing HyperLogLog."""

from __future__ import annotations

import random

from hllsketch.sketch import HyperLogLog


def simulate_distinct(
    n_distinct: int = 10_000,
    repetitions: int = 3,
    precision: int = 12,
    seed: int = 42,
) -> tuple[HyperLogLog, int]:
    """Simulate a stream with n_distinct unique elements (each appearing `repetitions` times).

    Returns:
        (hll, true_distinct) — sketch and the exact cardinality.
    """
    rng = random.Random(seed)
    hll = HyperLogLog(precision=precision)
    # Generate distinct item pool
    items = [f"user_{rng.randint(0, 10**9)}" for _ in range(n_distinct)]
    # Shuffle repetitions
    stream = items * repetitions
    rng.shuffle(stream)
    for item in stream:
        hll.add(item)
    return hll, n_distinct
