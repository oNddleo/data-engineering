"""Count-Min sketch schema.

The sketch (Cormode & Muthukrishnan 2003) is parameterised by:

* **width** ``w = ⌈e / ε⌉`` — controls per-bucket collision rate;
  ``ε`` is the relative error bound.
* **depth** ``d = ⌈ln(1/δ)⌉`` — number of independent hash rows;
  ``δ`` is the failure probability (the chance the estimate exceeds
  the bound).

Estimate guarantee: with probability ≥ 1 − δ,

```
true_count ≤ estimate ≤ true_count + ε · total_count
```

The sketch is **one-sided** — over-estimates only, never under.

Standard precisions:

| ε      | δ      | width w  | depth d | memory     |
| ------ | ------ | -------- | ------- | ---------- |
| 0.01   | 0.01   | 272      | 5       | 5.3 KB     |
| 0.001  | 0.01   | 2 719    | 5       | 53 KB      |
| 0.001  | 0.001  | 2 719    | 7       | 74 KB      |
| 0.0001 | 0.001  | 27 183   | 7       | 740 KB     |

(Each cell is a 32-bit unsigned counter.)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

MAX_COUNT = (1 << 32) - 1  # 32-bit unsigned counter ceiling


@dataclass(frozen=True, slots=True)
class SketchConfig:
    """Configuration for a ``CountMinSketch``."""

    epsilon: float = 0.001  # relative error bound
    delta: float = 0.001  # failure probability

    def __post_init__(self) -> None:
        if not 0 < self.epsilon < 1:
            raise ValueError(f"epsilon must be in (0, 1), got {self.epsilon}")
        if not 0 < self.delta < 1:
            raise ValueError(f"delta must be in (0, 1), got {self.delta}")

    @property
    def width(self) -> int:
        """``w = ⌈e / ε⌉`` — number of buckets per row."""
        return max(1, math.ceil(math.e / self.epsilon))

    @property
    def depth(self) -> int:
        """``d = ⌈ln(1/δ)⌉`` — number of independent rows."""
        return max(1, math.ceil(math.log(1.0 / self.delta)))


@dataclass(frozen=True, slots=True)
class CountMinSketch:
    """The sketch — a 2D ``d × w`` table of 32-bit counters."""

    config: SketchConfig
    rows: list[list[int]] = field(default_factory=list)
    total_count: int = 0

    def __post_init__(self) -> None:
        if not self.rows:
            # Auto-fill on construction via dataclass-safe __setattr__.
            d = self.config.depth
            w = self.config.width
            object.__setattr__(self, "rows", [[0] * w for _ in range(d)])
        else:
            d = self.config.depth
            w = self.config.width
            if len(self.rows) != d:
                raise ValueError(
                    f"rows count {len(self.rows)} != depth {d}",
                )
            for r in self.rows:
                if len(r) != w:
                    raise ValueError(
                        f"row length {len(r)} != width {w}",
                    )
                if any(c < 0 for c in r):
                    raise ValueError("counters must be >= 0")
        if self.total_count < 0:
            raise ValueError("total_count must be >= 0")

    @property
    def width(self) -> int:
        return self.config.width

    @property
    def depth(self) -> int:
        return self.config.depth

    @property
    def n_cells(self) -> int:
        """Total number of counters = ``depth × width``."""
        return self.depth * self.width


@dataclass(frozen=True, slots=True)
class HeavyHitter:
    """One heavy-hitter result row."""

    value: str
    estimated_count: int
    fraction_of_total: float  # estimated_count / total_count

    def __post_init__(self) -> None:
        if self.estimated_count < 0:
            raise ValueError("estimated_count must be >= 0")
        if not 0 <= self.fraction_of_total <= 1.0:
            raise ValueError("fraction_of_total must be in [0, 1]")


@dataclass(frozen=True, slots=True)
class SketchStats:
    """Roll-up of one sketch — for diagnostics + capacity planning."""

    width: int
    depth: int
    n_cells: int
    total_count: int
    max_counter: int
    epsilon: float
    delta: float
    standard_error_bound: int  # ε × total_count


__all__ = [
    "MAX_COUNT",
    "CountMinSketch",
    "HeavyHitter",
    "SketchConfig",
    "SketchStats",
]
