"""Column-profile schema.

A ``ColumnProfile`` is the canonical output of a profiling pass —
it captures everything the query optimizer / DQ monitor needs to
make decisions about a column:

* **null fraction** and total row count,
* **distinct cardinality** (capped),
* **numeric stats** (min / max / mean / std + percentiles), or
* **categorical stats** (top-K most-frequent values),
* a **histogram** (one of three flavours: equi-width / equi-depth /
  MaxDiff) for cardinality estimation.

The schema is column-kind-tagged so consumers can dispatch on
``kind`` without inspecting which fields are populated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ColumnKind(str, Enum):
    """Four detected column kinds covering canonical DE inputs."""

    NUMERIC = "NUMERIC"  # int / float column
    STRING = "STRING"  # high-cardinality strings (e.g. names, URLs)
    CATEGORICAL = "CATEGORICAL"  # low-cardinality strings (enum-like)
    DATE = "DATE"  # ISO date / datetime strings; ranked numerically


class HistogramKind(str, Enum):
    """Three histogram-construction strategies."""

    EQUI_WIDTH = "EQUI_WIDTH"  # n equal-width bins between min and max
    EQUI_DEPTH = "EQUI_DEPTH"  # n bins, each holding ~equal count
    MAXDIFF = "MAXDIFF"  # bin boundaries at the biggest gaps


@dataclass(frozen=True, slots=True)
class Bin:
    """One histogram bin — half-open ``[lower, upper)`` with a count."""

    lower: float
    upper: float
    count: int

    def __post_init__(self) -> None:
        if self.count < 0:
            raise ValueError(f"count must be >= 0, got {self.count}")
        if self.upper < self.lower:
            raise ValueError(f"upper {self.upper} < lower {self.lower}")

    @property
    def width(self) -> float:
        return self.upper - self.lower


@dataclass(frozen=True, slots=True)
class Histogram:
    """A histogram of a numeric column's value distribution."""

    kind: HistogramKind
    bins: tuple[Bin, ...]
    total_count: int

    def __post_init__(self) -> None:
        if self.total_count < 0:
            raise ValueError(f"total_count must be >= 0, got {self.total_count}")
        if self.bins and sum(b.count for b in self.bins) != self.total_count:
            raise ValueError(
                f"bin counts {sum(b.count for b in self.bins)} "
                f"!= total_count {self.total_count}",
            )

    @property
    def n_bins(self) -> int:
        return len(self.bins)


@dataclass(frozen=True, slots=True)
class TopKEntry:
    """One entry in a top-K most-frequent list."""

    value: str
    count: int
    # Space-Saving algorithm reports `count` as an upper bound on the
    # true frequency, and `epsilon` as the over-count error margin.
    epsilon: int = 0

    def __post_init__(self) -> None:
        if self.count < 0:
            raise ValueError(f"count must be >= 0, got {self.count}")
        if self.epsilon < 0:
            raise ValueError(f"epsilon must be >= 0, got {self.epsilon}")


@dataclass(frozen=True, slots=True)
class NumericStats:
    """min / max / mean / std + 5 canonical percentiles."""

    min: float
    max: float
    mean: float
    std: float
    p25: float
    p50: float
    p75: float
    p95: float
    p99: float

    def __post_init__(self) -> None:
        if self.std < 0:
            raise ValueError(f"std must be >= 0, got {self.std}")


@dataclass(frozen=True, slots=True)
class StringStats:
    """String column length distribution."""

    min_length: int
    max_length: int
    mean_length: float

    def __post_init__(self) -> None:
        if self.min_length < 0 or self.max_length < 0:
            raise ValueError("lengths must be >= 0")
        if self.max_length < self.min_length:
            raise ValueError("max_length < min_length")


@dataclass(frozen=True, slots=True)
class ColumnProfile:
    """The canonical profile of one column."""

    name: str
    kind: ColumnKind
    n_rows: int
    n_non_null: int
    cardinality: int  # distinct non-null values, capped
    cardinality_capped: bool  # True when cardinality hit the cap

    # Optional sub-profiles (None for inapplicable column kinds)
    numeric: NumericStats | None = None
    strings: StringStats | None = None
    top_k: tuple[TopKEntry, ...] = field(default_factory=tuple)
    histogram: Histogram | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must be non-empty")
        if self.n_rows < 0 or self.n_non_null < 0:
            raise ValueError("counts must be >= 0")
        if self.n_non_null > self.n_rows:
            raise ValueError("n_non_null > n_rows")
        if self.cardinality < 0:
            raise ValueError("cardinality must be >= 0")

    @property
    def null_fraction(self) -> float:
        if self.n_rows == 0:
            return 0.0
        return (self.n_rows - self.n_non_null) / self.n_rows


__all__ = [
    "Bin",
    "ColumnKind",
    "ColumnProfile",
    "Histogram",
    "HistogramKind",
    "NumericStats",
    "StringStats",
    "TopKEntry",
]
