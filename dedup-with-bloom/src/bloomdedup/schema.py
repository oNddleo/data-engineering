"""Bloom-filter parameter calculator and state container.

A Bloom filter is a fixed-size bit array + k independent hash
functions. Given:

* ``n`` — expected number of unique items
* ``p`` — desired false-positive rate (e.g. 0.01 = 1 %)

the optimal parameters are:

* ``m = -n · ln(p) / (ln 2)²``    (bit-array size)
* ``k = (m/n) · ln 2``             (number of hashes)

We round ``m`` up to the next byte boundary and ``k`` to the nearest
positive integer. The actual achieved FPR is then:

* ``p_actual ≈ (1 - exp(-k·n/m))^k``

False **negatives** are impossible — a Bloom filter that says "no"
is always right. False **positives** are bounded by ``p``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BloomParams:
    """Calculated parameters for an optimal Bloom filter."""

    capacity: int  # expected unique items (n)
    fpr: float  # target false-positive rate (p)
    m_bits: int  # bit-array size (rounded up to byte boundary)
    k_hashes: int  # number of hash functions

    @classmethod
    def for_capacity(cls, capacity: int, fpr: float = 0.01) -> BloomParams:
        if capacity <= 0:
            raise ValueError("capacity must be > 0")
        if not 0.0 < fpr < 1.0:
            raise ValueError("fpr must be in (0, 1)")
        ln2 = math.log(2)
        m_raw = -capacity * math.log(fpr) / (ln2 * ln2)
        # Round up to next byte boundary so storage is whole-byte aligned.
        m_bits = ((int(math.ceil(m_raw)) + 7) // 8) * 8
        k_raw = (m_bits / capacity) * ln2
        k_hashes = max(1, int(round(k_raw)))
        return cls(capacity=capacity, fpr=fpr, m_bits=m_bits, k_hashes=k_hashes)

    @property
    def m_bytes(self) -> int:
        return self.m_bits // 8


__all__ = ["BloomParams"]
