"""Synthetic value streams for benchmarking t-digest accuracy.

Four generators covering the common ``latency-monitoring`` distributions:

* ``uniform_stream`` — uniform on [0, 1). Worst case for the tails.
* ``gaussian_stream`` — N(μ, σ). Standard service-time model.
* ``lognormal_stream`` — exp(N(μ, σ)) — heavy right tail, classic web
  latency / payload-size shape.
* ``pareto_stream`` — power-law tail, very heavy. Models DoS bursts
  and cache-miss latencies.

All seeded.
"""

from __future__ import annotations

import math
import random


def uniform_stream(n: int, *, seed: int = 0) -> list[float]:
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    rng = random.Random(seed)
    return [rng.random() for _ in range(n)]


def gaussian_stream(
    n: int,
    *,
    mu: float = 0.0,
    sigma: float = 1.0,
    seed: int = 0,
) -> list[float]:
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    if sigma <= 0:
        raise ValueError(f"sigma must be > 0, got {sigma}")
    rng = random.Random(seed)
    return [rng.gauss(mu, sigma) for _ in range(n)]


def lognormal_stream(
    n: int,
    *,
    mu: float = 0.0,
    sigma: float = 1.0,
    seed: int = 0,
) -> list[float]:
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    if sigma <= 0:
        raise ValueError(f"sigma must be > 0, got {sigma}")
    rng = random.Random(seed)
    return [math.exp(rng.gauss(mu, sigma)) for _ in range(n)]


def pareto_stream(
    n: int,
    *,
    alpha: float = 1.5,
    seed: int = 0,
) -> list[float]:
    """Pareto Type I with scale 1: P(X > x) = x^{-α} for x ≥ 1."""
    if n < 0:
        raise ValueError(f"n must be >= 0, got {n}")
    if alpha <= 0:
        raise ValueError(f"alpha must be > 0, got {alpha}")
    rng = random.Random(seed)
    # Inverse-CDF: X = (1 - U)^{-1/α}.
    return [(1.0 - rng.random()) ** (-1.0 / alpha) for _ in range(n)]


def exact_quantile(values: list[float], q: float) -> float:
    """Reference exact quantile via sort. Used to score the digest."""
    if not values:
        raise ValueError("values must be non-empty")
    if not 0 <= q <= 1:
        raise ValueError(f"q must be in [0, 1], got {q}")
    s = sorted(values)
    if q == 0:
        return s[0]
    if q == 1:
        return s[-1]
    # Linear interpolation between adjacent ranks.
    pos = q * (len(s) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(s) - 1)
    frac = pos - lo
    return s[lo] + frac * (s[hi] - s[lo])


__all__ = [
    "exact_quantile",
    "gaussian_stream",
    "lognormal_stream",
    "pareto_stream",
    "uniform_stream",
]
