"""Simulate frequency streams for testing Count-Min Sketch."""

from __future__ import annotations

import random

from cmsketch.sketch import CountMinSketch


def simulate_zipf(
    n_items: int = 10_000,
    vocab_size: int = 1_000,
    exponent: float = 1.1,
    width: int = 2048,
    depth: int = 5,
    seed: int = 42,
) -> tuple[CountMinSketch, dict[str, int]]:
    """Simulate a Zipfian frequency stream and return sketch + true counts.

    Args:
        n_items:    Number of update operations.
        vocab_size: Number of distinct items.
        exponent:   Zipf exponent (higher = more skewed).
        width:      CMS width.
        depth:      CMS depth.
        seed:       RNG seed.

    Returns:
        (sketch, true_counts) where true_counts maps item -> exact count.
    """
    rng = random.Random(seed)
    sketch = CountMinSketch(width=width, depth=depth, seed=seed)
    true_counts: dict[str, int] = {}

    # Zipf weights: w_k = 1/k^exponent
    weights = [1.0 / (i**exponent) for i in range(1, vocab_size + 1)]
    total_w = sum(weights)
    probs = [w / total_w for w in weights]

    # Build CDF for sampling
    cdf = []
    cumulative = 0.0
    for p in probs:
        cumulative += p
        cdf.append(cumulative)

    items = [f"item_{i}" for i in range(1, vocab_size + 1)]

    for _ in range(n_items):
        r = rng.random()
        # Binary search for item
        lo, hi = 0, vocab_size - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if cdf[mid] < r:
                lo = mid + 1
            else:
                hi = mid
        item = items[lo]
        sketch.update(item)
        true_counts[item] = true_counts.get(item, 0) + 1

    return sketch, true_counts
