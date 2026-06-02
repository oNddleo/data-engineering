"""t-digest schema — Centroid + TDigest snapshot + BuildableTDigest.

A **t-digest** (Dunning & Ertl, *Computing Extremely Accurate
Quantiles Using t-digests*, 2014) is a probabilistic data structure
for streaming quantile estimation that trades a bounded number of
**centroids** (mean + weight pairs) for a tight tail accuracy
guarantee. Headline properties:

* Constant memory in ``compression`` parameter δ (typically 100–1000).
* p99 / p999 accurate to ~1/δ — better than a fixed-error histogram
  for the same memory.
* **Exactly mergeable** — two digests built on disjoint streams can
  be combined without revisiting raw data.

The buffer-then-merge variant (this implementation) keeps an
*unsorted* buffer alongside a *sorted* list of centroids:

* ``add(v)`` → append to buffer (O(1))
* Buffer full → ``compress()`` merges buffer + centroids into a new
  sorted centroid list under the scale-function size bound.
* Queries (``quantile``, ``cdf``) flush any pending buffer first.

The scale function ``k(q) = δ / (2π) · asin(2q − 1)`` ensures small
centroids near q=0 and q=1 (tails) and larger ones in the middle.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Centroid:
    """One (mean, weight) pair representing a cluster of input values."""

    mean: float
    weight: float

    def __post_init__(self) -> None:
        if self.weight < 0:
            raise ValueError(f"weight must be >= 0, got {self.weight}")
        # NaN guard — we accept ±inf for mean (degenerate but well-defined).
        if math.isnan(self.mean):
            raise ValueError("mean must not be NaN")


@dataclass(frozen=True, slots=True)
class TDigest:
    """Immutable snapshot of a t-digest.

    Centroids must be sorted by ``mean``. ``compression`` is the
    *δ* parameter that bounded their growth. ``min_value`` and
    ``max_value`` carry the exact extremes seen — this lets us pin
    the cdf at exactly 0 and 1 (Dunning's trick to avoid extrapolation).
    """

    compression: float
    centroids: tuple[Centroid, ...]
    total_weight: float
    min_value: float
    max_value: float

    def __post_init__(self) -> None:
        if self.compression < 1:
            raise ValueError(
                f"compression must be >= 1, got {self.compression}",
            )
        if self.total_weight < 0:
            raise ValueError(
                f"total_weight must be >= 0, got {self.total_weight}",
            )
        # Verify sortedness.
        for i in range(1, len(self.centroids)):
            if self.centroids[i].mean < self.centroids[i - 1].mean:
                raise ValueError(
                    f"centroids not sorted at index {i}: "
                    f"{self.centroids[i - 1].mean} > {self.centroids[i].mean}",
                )
        # Sum invariant.
        sum_w = sum(c.weight for c in self.centroids)
        if abs(sum_w - self.total_weight) > 1e-6 * max(1.0, self.total_weight):
            raise ValueError(
                f"centroid weights sum to {sum_w} but total_weight={self.total_weight}",
            )

    @property
    def n_centroids(self) -> int:
        return len(self.centroids)


@dataclass(slots=True)
class BuildableTDigest:
    """Mutable t-digest with a streaming-insert buffer.

    Inserts go to ``_buffer``; when ``len(_buffer) >= buffer_size`` we
    invoke ``compress()`` (in ``tdigest.digest``) which merges the
    buffer into the sorted ``_centroids`` list.
    """

    compression: float
    buffer_size: int
    _centroids: list[Centroid] = field(default_factory=list, repr=False)
    _buffer: list[Centroid] = field(default_factory=list, repr=False)
    total_weight: float = 0.0
    min_value: float = float("inf")
    max_value: float = float("-inf")

    def __post_init__(self) -> None:
        if self.compression < 1:
            raise ValueError(
                f"compression must be >= 1, got {self.compression}",
            )
        if self.buffer_size < 1:
            raise ValueError(
                f"buffer_size must be >= 1, got {self.buffer_size}",
            )


__all__ = ["BuildableTDigest", "Centroid", "TDigest"]
