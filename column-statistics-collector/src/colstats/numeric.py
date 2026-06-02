"""Numeric stats — min / max / mean / std + percentiles.

The mean and std come from **Welford's online algorithm** (Knuth
TAOCP Vol 2 §4.2.2.A2) — numerically stable, single-pass, no
catastrophic cancellation on values of differing magnitude.

Percentiles use **nearest-rank** over a sorted copy (O(n log n))
since we need to materialize the column for downstream histogram
construction anyway. For streaming use, callers should embed a
streaming quantile sketch (P² or t-digest) — out of scope here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from colstats.schema import NumericStats


@dataclass(slots=True)
class WelfordAccumulator:
    """Online mean + variance via Welford's algorithm."""

    n: int = 0
    mean: float = 0.0
    m2: float = field(default=0.0)  # sum of squared deviations from mean

    def add(self, x: float) -> None:
        """Add one observation, updating mean and m2 in place."""
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        delta2 = x - self.mean
        self.m2 += delta * delta2

    @property
    def variance(self) -> float:
        """Sample variance (Bessel-corrected). 0 when n < 2."""
        if self.n < 2:
            return 0.0
        return self.m2 / (self.n - 1)

    @property
    def std(self) -> float:
        return float(self.variance**0.5)


def numeric_stats(values: list[float]) -> NumericStats:
    """Compute the full ``NumericStats`` over a non-empty value list.

    Empty input returns an all-zero stats record.
    """
    if not values:
        return NumericStats(
            min=0.0,
            max=0.0,
            mean=0.0,
            std=0.0,
            p25=0.0,
            p50=0.0,
            p75=0.0,
            p95=0.0,
            p99=0.0,
        )
    accumulator = WelfordAccumulator()
    for v in values:
        accumulator.add(v)
    sorted_values = sorted(values)
    return NumericStats(
        min=sorted_values[0],
        max=sorted_values[-1],
        mean=accumulator.mean,
        std=accumulator.std,
        p25=_nearest_rank(sorted_values, 25),
        p50=_nearest_rank(sorted_values, 50),
        p75=_nearest_rank(sorted_values, 75),
        p95=_nearest_rank(sorted_values, 95),
        p99=_nearest_rank(sorted_values, 99),
    )


def _nearest_rank(sorted_values: list[float], pct: int) -> float:
    """Nearest-rank percentile over a pre-sorted list.

    Uses ``ceil(p/100 * n)`` per the standard NIST e-Handbook
    §1.3.5.6 / Hyndman & Fan 1996 type 1 definition.
    """
    import math

    if not sorted_values:
        return 0.0
    if not 0 <= pct <= 100:
        raise ValueError(f"pct must be in [0, 100], got {pct}")
    rank = max(1, math.ceil(pct / 100 * len(sorted_values)))
    return sorted_values[min(len(sorted_values), rank) - 1]


__all__ = ["WelfordAccumulator", "numeric_stats"]
