"""Count-Min Sketch implementation.

Reference: Cormode & Muthukrishnan (2005) "An Improved Data Stream Summary:
The Count-Min Sketch and its Applications".

Properties:
  - Space: O(w * d) counters where w = ceil(e/ε), d = ceil(ln(1/δ))
  - Update: O(d) — one hash per row
  - Query: O(d) — take minimum across all rows
  - Error guarantee: P(estimate > true + ε * N) < δ

The hash family uses pairwise-independent hashing:
    h_{a,b}(x) = ((a * hash(x) + b) mod p) mod w
where p = 2^61 - 1 (Mersenne prime, >> any 64-bit hash value).
"""

from __future__ import annotations

import hashlib
import math
import struct
from dataclasses import dataclass, field

# Mersenne prime 2^61 - 1: larger than any 64-bit hash value, enabling
# collision-free pairwise-independent hashing over the full hash space.
_M61: int = (1 << 61) - 1


def _hash_item(item: str | bytes | int | float) -> int:
    """Deterministic hash of any item to a non-negative integer."""
    if isinstance(item, int):
        raw = struct.pack(">q", item & 0xFFFFFFFFFFFFFFFF)
    elif isinstance(item, float):
        raw = struct.pack(">d", item)
    elif isinstance(item, str):
        raw = item.encode()
    else:
        raw = item
    digest = hashlib.sha256(raw).digest()
    return int.from_bytes(digest[:8], "big")


@dataclass
class CountMinSketch:
    """Count-Min Sketch for frequency estimation of a stream.

    Args:
        width: Number of counters per row (higher = less error).
               Default gives ε ≈ e/width ≈ 2.718/width.
        depth: Number of hash functions / rows (higher = lower failure prob).
               Default gives δ = e^(-depth) ≈ e^(-5) ≈ 0.0067.
        seed: Optional integer seed for reproducible hash coefficients.
    """

    width: int = 2048
    depth: int = 5
    seed: int = 0

    _table: list[list[int]] = field(default_factory=list, init=False)
    _n: int = field(default=0, init=False)
    # Pairwise-independent hash coefficients (a, b) per row
    _coeffs: list[tuple[int, int]] = field(default_factory=list, init=False)
    _prime: int = field(default=0, init=False)

    def __post_init__(self) -> None:
        if self.width < 2:
            raise ValueError("width must be >= 2")
        if self.depth < 1:
            raise ValueError("depth must be >= 1")
        self._prime = _M61
        self._table = [[0] * self.width for _ in range(self.depth)]
        # Generate (a, b) pairs from seed deterministically
        import random

        rng = random.Random(self.seed)
        self._coeffs = [
            (rng.randint(1, _M61 - 1), rng.randint(0, _M61 - 1)) for _ in range(self.depth)
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def n(self) -> int:
        """Total number of items added."""
        return self._n

    @classmethod
    def from_error_params(cls, epsilon: float, delta: float, seed: int = 0) -> CountMinSketch:
        """Construct with given error guarantees.

        Args:
            epsilon: Additive error as fraction of total count N.
                     estimate <= true + epsilon * N with probability >= 1 - delta.
            delta:   Failure probability.
        """
        if not 0 < epsilon < 1:
            raise ValueError("epsilon must be in (0, 1)")
        if not 0 < delta < 1:
            raise ValueError("delta must be in (0, 1)")
        width = math.ceil(math.e / epsilon)
        depth = math.ceil(math.log(1.0 / delta))
        return cls(width=width, depth=depth, seed=seed)

    def update(self, item: str | bytes | int | float, count: int = 1) -> None:
        """Add *count* occurrences of *item* to the sketch."""
        if count < 1:
            raise ValueError("count must be >= 1")
        h = _hash_item(item)
        p = self._prime
        for row, (a, b) in enumerate(self._coeffs):
            col = ((a * h + b) % p) % self.width
            self._table[row][col] += count
        self._n += count

    def query(self, item: str | bytes | int | float) -> int:
        """Return the estimated frequency of *item* (>= true count)."""
        h = _hash_item(item)
        p = self._prime
        return min(
            self._table[row][((a * h + b) % p) % self.width]
            for row, (a, b) in enumerate(self._coeffs)
        )

    def merge(self, other: CountMinSketch) -> CountMinSketch:
        """Return a new sketch representing the union of two streams.

        Both sketches must have identical width, depth, seed (same hash family).
        """
        if self.width != other.width or self.depth != other.depth or self.seed != other.seed:
            raise ValueError("Sketches must have identical width, depth, and seed to merge")
        merged = CountMinSketch(width=self.width, depth=self.depth, seed=self.seed)
        for row in range(self.depth):
            for col in range(self.width):
                merged._table[row][col] = self._table[row][col] + other._table[row][col]
        merged._n = self._n + other._n
        return merged

    def size(self) -> int:
        """Number of counters stored (width * depth)."""
        return self.width * self.depth

    def heavy_hitters(
        self, items: list[str | bytes | int | float], threshold_fraction: float
    ) -> list[tuple[str | bytes | int | float, int]]:
        """Return items whose estimated frequency >= threshold_fraction * N.

        Args:
            items:              Candidate items to check.
            threshold_fraction: Fraction of total count N to use as threshold.

        Returns:
            Sorted list of (item, estimated_count) for heavy hitters.
        """
        threshold = int(threshold_fraction * self._n)
        result = []
        seen: set[int] = set()
        for item in items:
            h = _hash_item(item)
            if h in seen:
                continue
            seen.add(h)
            est = self.query(item)
            if est >= threshold:
                result.append((item, est))
        result.sort(key=lambda x: x[1], reverse=True)
        return result
