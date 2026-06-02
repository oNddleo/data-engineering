"""Reservoir-sampling schema — frozen snapshot + mutable builders.

A **reservoir sample** is a uniform random sample of size ``k`` drawn
from a stream of unknown length ``N``. The classical guarantee
(Vitter 1985): every item that appears in the stream has an exact
``k/N`` probability of ending up in the final reservoir.

We expose three buildable shapes covering the canonical algorithm
trio plus an immutable snapshot:

| Class                  | Mutable? | Variant                              |
| ---------------------- | -------- | ------------------------------------ |
| ``Reservoir``          | no       | frozen snapshot (serialization)      |
| ``BuildableReservoir`` | yes      | Algorithm R *and* Algorithm L share  |
|                        |          | this shape (the algorithm picks how  |
|                        |          | to feed it).                         |
| ``WeightedReservoir``  | yes      | Efraimidis–Spirakis A-Res — every    |
|                        |          | item carries a positive weight.      |

Items are typed as ``str`` for codec friendliness. Larger structures
can be serialised at the caller boundary and stored as their JSON
string form.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Reservoir:
    """Immutable, on-the-wire-friendly reservoir snapshot."""

    capacity: int  # k — target sample size
    items: tuple[str, ...]  # the sampled items (len ≤ capacity)
    n_seen: int  # how many stream items were observed

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError(f"capacity must be >= 1, got {self.capacity}")
        if self.n_seen < 0:
            raise ValueError(f"n_seen must be >= 0, got {self.n_seen}")
        if len(self.items) > self.capacity:
            raise ValueError(
                f"reservoir overfull: {len(self.items)} items > capacity={self.capacity}",
            )

    @property
    def n_kept(self) -> int:
        return len(self.items)

    @property
    def fill_ratio(self) -> float:
        """Fraction of the reservoir's slots that are populated."""
        return self.n_kept / self.capacity if self.capacity > 0 else 0.0


@dataclass(slots=True)
class BuildableReservoir:
    """Mutable reservoir backing Algorithm R or Algorithm L.

    Items are stored in a plain list. The algorithms in
    ``reservoir.algorithms`` operate on this struct in-place.
    """

    capacity: int
    items: list[str] = field(default_factory=list)
    n_seen: int = 0
    # Algorithm L's internal state: probabilistic "skip cursor" W.
    # We store it here so callers can drive a long stream piecewise.
    _w: float = 1.0
    _next_index: int = 0

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError(f"capacity must be >= 1, got {self.capacity}")
        if self.n_seen < 0:
            raise ValueError(f"n_seen must be >= 0, got {self.n_seen}")
        if len(self.items) > self.capacity:
            raise ValueError(
                f"reservoir overfull: {len(self.items)} items > capacity={self.capacity}",
            )
        if not math.isfinite(self._w) or self._w <= 0:
            raise ValueError(f"_w must be a positive finite float, got {self._w}")


@dataclass(frozen=True, slots=True)
class WeightedItem:
    """One sampled item with its priority key (Efraimidis–Spirakis)."""

    value: str
    weight: float  # original weight (positive)
    key: float  # u^(1/w) — keep the largest keys

    def __post_init__(self) -> None:
        if self.weight <= 0:
            raise ValueError(f"weight must be > 0, got {self.weight}")
        if not 0 <= self.key <= 1:
            raise ValueError(f"key must be in [0, 1], got {self.key}")


@dataclass(slots=True)
class WeightedReservoir:
    """Mutable weighted-reservoir for Efraimidis–Spirakis A-Res.

    Maintains the top-``capacity`` items by ``key = u^(1/w_i)``.
    Stored sorted by ``key`` ascending so the smallest key is at
    index 0 (the cheap-to-evict slot).
    """

    capacity: int
    items: list[WeightedItem] = field(default_factory=list)
    n_seen: int = 0
    total_weight_seen: float = 0.0

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError(f"capacity must be >= 1, got {self.capacity}")
        if self.n_seen < 0:
            raise ValueError(f"n_seen must be >= 0, got {self.n_seen}")
        if self.total_weight_seen < 0:
            raise ValueError(
                f"total_weight_seen must be >= 0, got {self.total_weight_seen}",
            )
        if len(self.items) > self.capacity:
            raise ValueError(
                f"weighted reservoir overfull: {len(self.items)} > {self.capacity}",
            )
        # Verify sortedness on construction.
        for i in range(1, len(self.items)):
            if self.items[i].key < self.items[i - 1].key:
                raise ValueError(
                    f"items not sorted ascending by key at index {i}",
                )


__all__ = [
    "BuildableReservoir",
    "Reservoir",
    "WeightedItem",
    "WeightedReservoir",
]
