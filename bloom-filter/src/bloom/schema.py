"""Bloom-filter schema — immutable + buildable + counting + scalable.

A **Bloom filter** (Bloom 1970) is a compact probabilistic data structure
that answers the question "have I seen this value before?" with:

* **No false negatives.** If ``contains(v)`` returns ``False``, ``v``
  was definitely never added.
* **Tunable false positives.** ``contains(v)`` may return ``True`` for
  a never-added ``v`` with a probability bounded by the configured
  ``false_positive_rate`` (assuming the filter holds ≤ ``capacity``
  distinct items).

Storage is a single bit array of ``size_bits`` bits — typically
8–12 bits per item to achieve a 1% FPR. We expose four data shapes:

| Class            | Mutable? | Purpose                                  |
| ---------------- | -------- | ---------------------------------------- |
| ``BloomFilter``  | no       | Frozen snapshot — safe to share / load   |
| ``BuildableBloom``| yes     | Streaming inserts during ingestion       |
| ``CountingBloom``| yes      | Supports deletion via bucket counters    |
| ``ScalableBloom``| yes      | Grows dynamically — chained sub-filters  |

All four share the same hash family (``bloom.hash``).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class BloomFilter:
    """Immutable, on-the-wire-friendly Bloom filter snapshot.

    ``bits`` is an ``int`` used as a bit array (Python's arbitrary-
    precision integer gives us a one-allocation, length-stable
    bit-vector with cheap bitwise ops for union / intersection).
    """

    size_bits: int
    n_hashes: int
    n_items: int
    bits: int

    def __post_init__(self) -> None:
        if self.size_bits < 1:
            raise ValueError(f"size_bits must be >= 1, got {self.size_bits}")
        if self.n_hashes < 1:
            raise ValueError(f"n_hashes must be >= 1, got {self.n_hashes}")
        if self.n_items < 0:
            raise ValueError(f"n_items must be >= 0, got {self.n_items}")
        if self.bits < 0:
            raise ValueError(f"bits must be >= 0, got {self.bits}")
        if self.bits.bit_length() > self.size_bits:
            raise ValueError(
                f"bits has {self.bits.bit_length()} significant bits, "
                f"exceeds size_bits={self.size_bits}",
            )

    @property
    def fill_ratio(self) -> float:
        """Fraction of bits set — proxy for saturation."""
        if self.size_bits == 0:
            return 0.0
        return bin(self.bits).count("1") / self.size_bits

    @property
    def is_saturated(self) -> bool:
        """``True`` if the filter is more than half full (FPR climbing)."""
        return self.fill_ratio > 0.5


@dataclass(slots=True)
class BuildableBloom:
    """Mutable Bloom filter for streaming inserts.

    Wraps a plain ``bytearray`` to keep insertions O(k) — a bit-array
    on top of an ``int`` would re-allocate on every set bit.
    """

    size_bits: int
    n_hashes: int
    capacity: int
    target_fpr: float
    _bits: bytearray = field(repr=False)
    n_items: int = 0

    def __post_init__(self) -> None:
        if self.size_bits < 1:
            raise ValueError(f"size_bits must be >= 1, got {self.size_bits}")
        if self.n_hashes < 1:
            raise ValueError(f"n_hashes must be >= 1, got {self.n_hashes}")
        if self.capacity < 1:
            raise ValueError(f"capacity must be >= 1, got {self.capacity}")
        if not 0 < self.target_fpr < 1:
            raise ValueError(
                f"target_fpr must be in (0, 1), got {self.target_fpr}",
            )
        n_bytes = (self.size_bits + 7) // 8
        if len(self._bits) != n_bytes:
            raise ValueError(
                f"_bits length {len(self._bits)} does not match " f"ceil(size_bits/8)={n_bytes}",
            )

    @property
    def fill_ratio(self) -> float:
        if self.size_bits == 0:
            return 0.0
        total = sum(bin(b).count("1") for b in self._bits)
        return total / self.size_bits


@dataclass(slots=True)
class CountingBloom:
    """Bloom variant where each bucket is a saturating counter.

    Supports ``remove(v)`` (decrement each of v's k buckets). Trade-off:
    8× the memory of a vanilla Bloom (one byte per cell vs one bit), and
    a small false-removal risk if counter overflows (saturated at 255).
    """

    size_buckets: int
    n_hashes: int
    capacity: int
    target_fpr: float
    _counters: bytearray = field(repr=False)
    n_items: int = 0

    def __post_init__(self) -> None:
        if self.size_buckets < 1:
            raise ValueError(f"size_buckets must be >= 1, got {self.size_buckets}")
        if self.n_hashes < 1:
            raise ValueError(f"n_hashes must be >= 1, got {self.n_hashes}")
        if self.capacity < 1:
            raise ValueError(f"capacity must be >= 1, got {self.capacity}")
        if not 0 < self.target_fpr < 1:
            raise ValueError(
                f"target_fpr must be in (0, 1), got {self.target_fpr}",
            )
        if len(self._counters) != self.size_buckets:
            raise ValueError(
                f"_counters length {len(self._counters)} does not match "
                f"size_buckets={self.size_buckets}",
            )


@dataclass(slots=True)
class ScalableBloom:
    """Scalable Bloom filter (Almeida et al. 2007).

    A chain of layered ``BuildableBloom`` slices. When the current
    slice approaches capacity, a new slice is appended with:

    * ``capacity_new = capacity_prev * growth_factor`` (default 2)
    * ``target_fpr_new = target_fpr_prev * tightening_ratio`` (default 0.5)

    Total FPR remains bounded because the per-slice rates form a
    geometric series whose sum < initial_fpr / (1 − tightening).
    """

    initial_capacity: int
    target_fpr: float
    growth_factor: int = 2
    tightening_ratio: float = 0.5
    slices: list[BuildableBloom] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.initial_capacity < 1:
            raise ValueError(
                f"initial_capacity must be >= 1, got {self.initial_capacity}",
            )
        if not 0 < self.target_fpr < 1:
            raise ValueError(
                f"target_fpr must be in (0, 1), got {self.target_fpr}",
            )
        if self.growth_factor < 2:
            raise ValueError(
                f"growth_factor must be >= 2, got {self.growth_factor}",
            )
        if not 0 < self.tightening_ratio < 1:
            raise ValueError(
                f"tightening_ratio must be in (0, 1), " f"got {self.tightening_ratio}",
            )

    @property
    def n_items(self) -> int:
        return sum(s.n_items for s in self.slices)

    @property
    def n_slices(self) -> int:
        return len(self.slices)


__all__ = [
    "BloomFilter",
    "BuildableBloom",
    "CountingBloom",
    "ScalableBloom",
]
