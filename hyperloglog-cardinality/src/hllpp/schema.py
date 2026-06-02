"""HyperLogLog sketch schema.

The HLL sketch is parameterised by **precision** ``p`` (4 ≤ p ≤ 16).
The number of registers is ``m = 2^p`` and the standard relative
error is ``≈ 1.04 / sqrt(m)``:

| p  | m       | std error  | sketch size (bytes) |
| -- | ------- | ---------- | ------------------- |
| 4  | 16      | ~26%       | 16                  |
| 8  | 256     | ~6.5%      | 256                 |
| 10 | 1024    | ~3.3%      | 1 024               |
| 12 | 4096    | ~1.6%      | 4 096               |
| 14 | 16 384  | ~0.81%     | 16 384              |
| 16 | 65 536  | ~0.41%     | 65 536              |

The default precision **p = 14** matches Google's HLL++ paper and
most production systems (Redshift, BigQuery, Snowflake) — gives
< 1% error with ~16 KB of memory regardless of the input cardinality.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MIN_PRECISION = 4
MAX_PRECISION = 16
DEFAULT_PRECISION = 14


@dataclass(frozen=True, slots=True)
class HLLSketch:
    """An HLL sketch — immutable container with mutable register array.

    The ``registers`` array has length ``2^precision``, each entry is
    a non-negative int storing the max-leading-zero count seen for
    that bucket. Stored as a ``list[int]`` to keep stdlib-only.
    """

    precision: int
    registers: list[int] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not MIN_PRECISION <= self.precision <= MAX_PRECISION:
            raise ValueError(
                f"precision must be in [{MIN_PRECISION}, {MAX_PRECISION}], "
                f"got {self.precision}",
            )
        expected_m = 1 << self.precision
        if not self.registers:
            # Auto-fill on construction (the frozen dataclass needs object.__setattr__).
            object.__setattr__(self, "registers", [0] * expected_m)
        elif len(self.registers) != expected_m:
            raise ValueError(
                f"registers length {len(self.registers)} != 2^precision " f"({expected_m})",
            )
        if any(r < 0 for r in self.registers):
            raise ValueError("registers must all be >= 0")

    @property
    def m(self) -> int:
        """Number of registers ``= 2^precision``."""
        return 1 << self.precision

    def n_zero_registers(self) -> int:
        """Count of registers still at 0 (used for linear counting)."""
        return sum(1 for r in self.registers if r == 0)


@dataclass(frozen=True, slots=True)
class SketchStats:
    """Summary of one sketch — for diagnostics + drift reports."""

    precision: int
    m: int
    n_zero_registers: int
    max_register: int
    estimated_cardinality: int
    standard_error_pct: float  # e.g. 0.81 for p=14

    def __post_init__(self) -> None:
        if self.m != 1 << self.precision:
            raise ValueError(f"m {self.m} != 2^precision ({1 << self.precision})")
        if self.standard_error_pct < 0:
            raise ValueError("standard_error_pct must be >= 0")


__all__ = [
    "DEFAULT_PRECISION",
    "HLLSketch",
    "MAX_PRECISION",
    "MIN_PRECISION",
    "SketchStats",
]
