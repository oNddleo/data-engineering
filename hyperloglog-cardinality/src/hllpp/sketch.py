"""HyperLogLog++ core: add / estimate / merge.

The HyperLogLog algorithm (Flajolet et al. 2007) with the HLL++
improvements (Heule, Nunkesser, Hall 2013, Google):

* **Add(value)**: hash value into a 64-bit int; the top ``p`` bits
  pick a bucket index ``j``; the remaining ``q = 64 - p`` bits are
  scanned for the position of the leftmost 1. The bucket stores
  the max-seen leading-zeros-count + 1 (``rho``).

* **Estimate()**: harmonic mean of register values, bias-corrected:

  ```
  E = α_m · m² · (Σ 2^-M[i])^-1
  ```

  where ``α_m`` is a precision-dependent constant. For small
  cardinalities we use **linear counting**:
  ``E = m · ln(m / V)`` where V is the count of zero registers.

* **Merge(other)**: take element-wise max of the register arrays.
  Mathematically equivalent to adding both streams to one sketch —
  the basis of HLL's distributed-counting power.
"""

from __future__ import annotations

import math

from hllpp.hash import hash64, leading_zeros_64
from hllpp.schema import (
    DEFAULT_PRECISION,
    HLLSketch,
    SketchStats,
)


def new_sketch(precision: int = DEFAULT_PRECISION) -> HLLSketch:
    """Construct a fresh empty sketch at the given precision."""
    return HLLSketch(precision=precision)


def add(sketch: HLLSketch, value: str | bytes | int | float) -> None:
    """Add one observation to the sketch in place."""
    h = hash64(value)
    p = sketch.precision
    # Top p bits → register index.
    index = h >> (64 - p)
    # Remaining q = 64-p bits → ρ (leading zeros + 1).
    q = 64 - p
    w = h & ((1 << q) - 1)
    rho = leading_zeros_64(w, max_zeros=q + 1)
    if rho > sketch.registers[index]:
        sketch.registers[index] = rho


def estimate(sketch: HLLSketch) -> int:
    """Estimate the distinct cardinality represented by the sketch.

    Uses linear counting for very small streams + bias-corrected HLL
    elsewhere. Returns 0 for an empty sketch.
    """
    m = sketch.m
    zeros = sketch.n_zero_registers()
    if zeros == m:
        return 0
    raw = _raw_estimate(sketch)
    # Linear-counting threshold from Flajolet et al.: m * 2.5.
    if raw <= 2.5 * m and zeros > 0:
        return int(round(m * math.log(m / zeros)))
    return int(round(raw))


def merge(*sketches: HLLSketch) -> HLLSketch:
    """Return a new sketch = element-wise max of all inputs.

    All inputs must have the same precision. Raises ``ValueError``
    otherwise. An empty argument list returns a fresh empty sketch
    at DEFAULT_PRECISION.
    """
    if not sketches:
        return new_sketch()
    first = sketches[0]
    p = first.precision
    if any(s.precision != p for s in sketches[1:]):
        raise ValueError("all sketches must have the same precision")
    out_registers = list(first.registers)
    for other in sketches[1:]:
        for i, r in enumerate(other.registers):
            if r > out_registers[i]:
                out_registers[i] = r
    return HLLSketch(precision=p, registers=out_registers)


def stats(sketch: HLLSketch) -> SketchStats:
    """Build a ``SketchStats`` snapshot of the sketch."""
    m = sketch.m
    return SketchStats(
        precision=sketch.precision,
        m=m,
        n_zero_registers=sketch.n_zero_registers(),
        max_register=max(sketch.registers) if sketch.registers else 0,
        estimated_cardinality=estimate(sketch),
        standard_error_pct=round(1.04 / math.sqrt(m) * 100, 4),
    )


# ---- internal --------------------------------------------------------------


_ALPHA_M: dict[int, float] = {
    16: 0.673,
    32: 0.697,
    64: 0.709,
}


def _alpha(m: int) -> float:
    """Bias-correction constant α_m from Flajolet et al."""
    if m in _ALPHA_M:
        return _ALPHA_M[m]
    return 0.7213 / (1.0 + 1.079 / m)


def _raw_estimate(sketch: HLLSketch) -> float:
    """Raw harmonic-mean estimate, prior to small/large-range correction."""
    m = sketch.m
    inv_sum = 0.0
    for r in sketch.registers:
        inv_sum += 2 ** (-r)
    if inv_sum == 0:
        return 0.0
    return _alpha(m) * m * m / inv_sum


__all__ = ["add", "estimate", "merge", "new_sketch", "stats"]
