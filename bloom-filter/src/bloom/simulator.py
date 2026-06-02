"""Synthetic value streams for benchmarking Bloom filters.

Three generators:

* ``zipf_stream`` — Zipf-distributed strings (heavy head, long tail).
  Models real-world request streams (URLs, query terms).
* ``uniform_stream`` — uniformly random strings; FPR worst case.
* ``mixed_stream`` — a known set of "positive" strings interleaved
  with novel "negative" probes; useful for FPR measurement.

All seeded for reproducibility.
"""

from __future__ import annotations

import random


def uniform_stream(n: int, *, seed: int = 0, prefix: str = "v") -> list[str]:
    """``n`` uniformly random values, e.g. ``v-0001234567``."""
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    rng = random.Random(seed)
    return [f"{prefix}-{rng.randint(0, 10_000_000_000):010d}" for _ in range(n)]


def zipf_stream(
    n: int,
    *,
    vocab_size: int = 10_000,
    alpha: float = 1.2,
    seed: int = 0,
    prefix: str = "w",
) -> list[str]:
    """``n`` samples from a Zipf distribution over a vocabulary of ``vocab_size``.

    ``alpha > 1`` controls skew (1.2 is web-traffic-like).
    """
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    if vocab_size < 1:
        raise ValueError(f"vocab_size must be >= 1, got {vocab_size}")
    if alpha <= 1:
        raise ValueError(f"alpha must be > 1, got {alpha}")
    rng = random.Random(seed)
    # Sample from Zipf via rank-truncated geometric — accept-reject.
    out: list[str] = []
    while len(out) < n:
        # Standard Zipf rejection: sample k ~ Pareto, accept if k ≤ vocab_size.
        u = rng.random()
        k = int((1 - u) ** (-1 / (alpha - 1)))
        if 1 <= k <= vocab_size:
            out.append(f"{prefix}-{k:08d}")
    return out


def mixed_stream(
    n_positive: int,
    n_negative: int,
    *,
    seed: int = 0,
) -> tuple[list[str], list[str]]:
    """Disjoint sets of "true-positive" and "true-negative" probes.

    Returns ``(positives, negatives)`` where the two lists share no
    elements — useful for measuring the empirical false-positive rate
    of a populated filter.
    """
    if n_positive < 0 or n_negative < 0:
        raise ValueError("n_positive / n_negative must be >= 0")
    positives = uniform_stream(n_positive, seed=seed, prefix="pos")
    negatives = uniform_stream(n_negative, seed=seed + 1, prefix="neg")
    return positives, negatives


__all__ = ["mixed_stream", "uniform_stream", "zipf_stream"]
