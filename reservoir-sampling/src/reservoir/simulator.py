"""Synthetic stream generators for reservoir-sampling benchmarks.

* ``uniform_stream`` — N unique tokens "v-0000000001"..., uniform.
* ``zipf_stream`` — Zipf-distributed (heavy head) tokens.
* ``weighted_pairs`` — (value, weight) pairs with a configurable
  weight distribution: ``uniform``, ``zipf``, or ``power``.
"""

from __future__ import annotations

import random


def uniform_stream(n: int, *, seed: int = 0, prefix: str = "v") -> list[str]:
    """``n`` unique tokens, deterministic order."""
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    return [f"{prefix}-{i:010d}" for i in range(n)]


def zipf_stream(
    n: int,
    *,
    vocab_size: int = 1_000,
    alpha: float = 1.2,
    seed: int = 0,
    prefix: str = "z",
) -> list[str]:
    """``n`` tokens drawn from a Zipf(α) distribution over ``vocab_size`` keys."""
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    if vocab_size < 1:
        raise ValueError(f"vocab_size must be >= 1, got {vocab_size}")
    if alpha <= 1:
        raise ValueError(f"alpha must be > 1, got {alpha}")
    rng = random.Random(seed)
    out: list[str] = []
    while len(out) < n:
        u = rng.random()
        k = int((1.0 - u) ** (-1.0 / (alpha - 1.0)))
        if 1 <= k <= vocab_size:
            out.append(f"{prefix}-{k:08d}")
    return out


def weighted_pairs(
    n: int,
    *,
    distribution: str = "uniform",
    seed: int = 0,
    prefix: str = "w",
) -> list[tuple[str, float]]:
    """``n`` ``(value, weight)`` pairs.

    Weight distributions:

    * ``uniform``: weight ∼ Uniform(1, 10)
    * ``power``:   weight ∼ Pareto(α = 2)
    * ``binary``:  90% weight=1, 10% weight=100 (heavy-hitter shape)
    """
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    rng = random.Random(seed)
    out: list[tuple[str, float]] = []
    for i in range(n):
        value = f"{prefix}-{i:010d}"
        if distribution == "uniform":
            weight = rng.uniform(1.0, 10.0)
        elif distribution == "power":
            weight = (1.0 - rng.random()) ** (-1.0 / 2.0)
        elif distribution == "binary":
            weight = 100.0 if rng.random() < 0.10 else 1.0
        else:
            raise ValueError(f"unknown distribution {distribution!r}")
        out.append((value, weight))
    return out


__all__ = ["uniform_stream", "weighted_pairs", "zipf_stream"]
