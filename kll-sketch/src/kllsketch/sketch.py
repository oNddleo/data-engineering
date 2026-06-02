"""KLL (Karnin-Lang-Liberty) quantile sketch.

Reference: "Better and More Practical Sketches for Estimating Quantiles"
           Karnin, Lang, Liberty (2016).

This implementation uses the simplified "KLL" approach:
- Items arrive in a stream and are stored in compactors (one per level).
- When a compactor is full (size >= 2*capacity), it "compacts":
  sorts, keeps every other element (random phase), and propagates survivors
  to the next level.
- Quantile queries sort all retained items (with implicit weights) and binary
  search for the rank.

For production use the c = 2/3 capacity reduction schedule gives
O(log^2(1/eps) / eps) space.  For simplicity we use a fixed k (sketch size)
and capacity(level) = max(2, k * c^level).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


@dataclass
class KLLSketch:
    """Streaming quantile sketch with O(log^2(1/eps) / eps) space."""

    k: int = 200  # sketch accuracy parameter; larger = more accurate
    seed: int | None = None  # optional RNG seed for reproducibility
    _compactors: list[list[float]] = field(default_factory=list, init=False)
    _n: int = field(default=0, init=False)
    _rng: random.Random = field(default_factory=random.Random, init=False)

    def __post_init__(self) -> None:
        if self.k < 2:
            raise ValueError("k must be >= 2")
        if self.seed is not None:
            self._rng = random.Random(self.seed)
        self._compactors = [[]]  # start with one level

    def _capacity(self, level: int) -> int:
        """Capacity for compactor at given level."""
        # Each higher level has ~2/3 the capacity
        c = max(2, int(self.k * (2.0 / 3.0) ** level))
        return c * 2  # 2x to trigger compaction at 2*capacity

    def update(self, value: float) -> None:
        """Insert one item into the sketch."""
        self._compactors[0].append(value)
        self._n += 1
        self._compact_if_needed(0)

    def _compact_if_needed(self, level: int) -> None:
        """Compact level if it exceeds capacity; recurse upward."""
        if len(self._compactors[level]) < self._capacity(level):
            return
        # Sort and sub-sample: keep every other element starting at random offset
        self._compactors[level].sort()
        offset = self._rng.randint(0, 1)
        survivors = self._compactors[level][offset::2]
        self._compactors[level] = []

        # Propagate survivors to next level
        if level + 1 == len(self._compactors):
            self._compactors.append([])
        self._compactors[level + 1].extend(survivors)
        self._compact_if_needed(level + 1)

    def _all_items_with_weights(self) -> list[tuple[float, int]]:
        """Return (value, weight) pairs where weight = 2^level."""
        items: list[tuple[float, int]] = []
        for level, compactor in enumerate(self._compactors):
            weight = 1 << level  # 2^level
            for v in compactor:
                items.append((v, weight))
        return items

    def quantile(self, phi: float) -> float:
        """Approximate phi-quantile (0 < phi ≤ 1)."""
        if not 0.0 < phi <= 1.0:
            raise ValueError(f"phi must be in (0, 1], got {phi}")
        if self._n == 0:
            raise ValueError("Sketch is empty")
        items = sorted(self._all_items_with_weights(), key=lambda x: x[0])
        total = sum(w for _, w in items)
        target = math.ceil(phi * total)
        cum = 0
        for v, w in items:
            cum += w
            if cum >= target:
                return v
        return items[-1][0]  # should not reach here

    def merge(self, other: KLLSketch) -> KLLSketch:
        """Return a new sketch containing all items from both."""
        merged = KLLSketch(k=min(self.k, other.k))
        for level, compactor in enumerate(self._compactors):
            while level >= len(merged._compactors):
                merged._compactors.append([])
            merged._compactors[level].extend(compactor)
        for level, compactor in enumerate(other._compactors):
            while level >= len(merged._compactors):
                merged._compactors.append([])
            merged._compactors[level].extend(compactor)
        merged._n = self._n + other._n
        # Re-compact all levels
        for lvl in range(len(merged._compactors)):
            merged._compact_if_needed(lvl)
        return merged

    @property
    def n(self) -> int:
        """Total number of items inserted."""
        return self._n

    def size(self) -> int:
        """Total number of items retained in the sketch."""
        return sum(len(c) for c in self._compactors)

    def cdf(self, value: float) -> float:
        """Approximate CDF: fraction of items ≤ value."""
        items = self._all_items_with_weights()
        total = sum(w for _, w in items)
        if total == 0:
            return 0.0
        below = sum(w for v, w in items if v <= value)
        return below / total
