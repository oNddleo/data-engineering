"""HyperLogLog++ cardinality estimator.

References:
  - Flajolet et al. (2007) "HyperLogLog: the analysis of a near-optimal
    cardinality estimation algorithm"
  - Heule et al. (2013) "HyperLogLog in Practice: Algorithmic Engineering
    of a State of The Art Cardinality Estimation Algorithm" (HLL++)

Algorithm:
  1. Hash each element to a 64-bit value h.
  2. Use the first `precision` bits of h to select a register index j.
  3. Count the number of leading zeros in the remaining bits + 1 → rho.
  4. Maintain M[j] = max(M[j], rho) across all elements.
  5. Estimate cardinality via the harmonic mean of 2^-M[j].

Error rate: σ ≈ 1.04 / sqrt(m) where m = 2^precision.
  precision=10 → m=1024,  σ ≈ 3.25%
  precision=12 → m=4096,  σ ≈ 1.63%
  precision=14 → m=16384, σ ≈ 0.81%
"""

from __future__ import annotations

import hashlib
import math
import struct
from dataclasses import dataclass, field


def _hash64(item: str | bytes | int | float) -> int:
    """Deterministic 64-bit hash for any supported type."""
    if isinstance(item, int):
        raw = struct.pack(">Q", item & 0xFFFFFFFFFFFFFFFF)
    elif isinstance(item, float):
        raw = struct.pack(">d", item)
    elif isinstance(item, str):
        raw = item.encode()
    else:
        raw = item
    digest = hashlib.sha256(raw).digest()
    return int.from_bytes(digest[:8], "big")


def _rho(bits: int, max_bits: int) -> int:
    """Position of leftmost 1-bit (1-indexed) in a max_bits-wide value.

    Equivalent to: number of leading zeros + 1 in the max_bits suffix.
    Returns max_bits + 1 if all bits are zero.
    """
    if bits == 0:
        return max_bits + 1
    # Count leading zeros in a max_bits-wide value
    leading = max_bits - bits.bit_length()
    return leading + 1


def _alpha(m: int) -> float:
    """Bias correction constant for HyperLogLog."""
    if m == 16:
        return 0.673
    if m == 32:
        return 0.697
    if m == 64:
        return 0.709
    return 0.7213 / (1.0 + 1.079 / m)


@dataclass
class HyperLogLog:
    """HyperLogLog++ cardinality estimator.

    Args:
        precision: Number of bits used for register indexing.
                   m = 2^precision registers. Range: [4, 18].
                   Higher → more accuracy but more memory.
    """

    precision: int = 12

    _registers: list[int] = field(default_factory=list, init=False)
    _m: int = field(default=0, init=False)
    _alpha_m: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        if not 4 <= self.precision <= 18:
            raise ValueError("precision must be in [4, 18]")
        self._m = 1 << self.precision  # 2^precision
        self._registers = [0] * self._m
        self._alpha_m = _alpha(self._m)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, item: str | bytes | int | float) -> None:
        """Add an element to the sketch."""
        h = _hash64(item)
        # j = first `precision` bits (register index)
        j = h >> (64 - self.precision)
        # w = remaining 64 - precision bits
        w = h & ((1 << (64 - self.precision)) - 1)
        # rho = position of leftmost 1-bit in w
        r = _rho(w, 64 - self.precision)
        if r > self._registers[j]:
            self._registers[j] = r

    def count(self) -> int:
        """Estimate the number of distinct elements added."""
        m = self._m
        # Raw HLL estimate via harmonic mean
        z = sum(2.0 ** (-reg) for reg in self._registers)
        estimate = self._alpha_m * m * m / z

        # Small-range correction (linear counting)
        if estimate <= 2.5 * m:
            zeros = self._registers.count(0)
            if zeros > 0:
                estimate = m * math.log(m / zeros)

        # Large-range correction (2^32 boundary)
        elif estimate > (1 << 32) / 30.0:
            estimate = -(1 << 32) * math.log(1.0 - estimate / (1 << 32))

        return int(round(estimate))

    def merge(self, other: HyperLogLog) -> HyperLogLog:
        """Return a new sketch representing the union of two HLL sketches.

        Both must have the same precision.
        """
        if self.precision != other.precision:
            raise ValueError("Cannot merge HyperLogLog sketches with different precision")
        merged = HyperLogLog(precision=self.precision)
        merged._registers = [
            max(a, b) for a, b in zip(self._registers, other._registers, strict=True)
        ]
        return merged

    def size_bytes(self) -> int:
        """Approximate memory footprint: one byte per register."""
        return self._m

    @property
    def num_registers(self) -> int:
        """Number of registers (2^precision)."""
        return self._m
