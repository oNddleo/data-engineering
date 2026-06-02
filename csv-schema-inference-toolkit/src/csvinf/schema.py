"""Inferred-schema types.

We model the output of inference as an ``InferredSchema`` containing
one ``InferredColumn`` per CSV column, in column order. Each column
carries:

* the **detected type** (``INT``, ``FLOAT``, ``BOOL``, ``DATE``,
  ``DATETIME``, ``DECIMAL``, ``STRING``),
* **nullability** (whether any sample row was empty),
* **distinct-value cardinality** (capped at ``MAX_CARDINALITY`` for
  memory),
* a sample of representative values for review,
* min/max for numeric and temporal types.

These cover the canonical Avro / JSON Schema / Pydantic projections
needed for ingestion into a warehouse.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

MAX_CARDINALITY = 1_000
"""Maximum distinct-value count we track exactly. Beyond this we
return ``MAX_CARDINALITY + 1`` to indicate "many"."""


class ColumnType(str, Enum):
    """Seven detected types covering canonical CSV ingestion."""

    INT = "INT"  # all values parse as integer (incl. signed)
    FLOAT = "FLOAT"  # all values parse as float
    DECIMAL = "DECIMAL"  # numeric with fixed decimal places — VND-style "1.234.567"
    BOOL = "BOOL"  # true/false/yes/no/1/0/Có/Không
    DATE = "DATE"  # yyyy-mm-dd or dd/mm/yyyy etc, no time component
    DATETIME = "DATETIME"  # ISO-8601 or recognised datetime
    STRING = "STRING"  # fallback


@dataclass(frozen=True, slots=True)
class InferredColumn:
    """Inferred properties for one column."""

    name: str
    type: ColumnType
    nullable: bool
    n_rows: int  # rows considered for this column
    n_non_null: int  # rows with a non-empty value
    cardinality: int  # number of distinct non-null values; capped at MAX_CARDINALITY+1
    examples: tuple[str, ...]  # up to 5 representative non-null values
    min_value: str = ""  # min as raw string, for INT/FLOAT/DECIMAL/DATE/DATETIME
    max_value: str = ""  # max as raw string
    detected_format: str = ""  # e.g. "dd/MM/yyyy" or "yyyy-mm-dd" for DATE/DATETIME

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must be non-empty")
        if self.n_rows < 0:
            raise ValueError("n_rows must be >= 0")
        if self.n_non_null < 0:
            raise ValueError("n_non_null must be >= 0")
        if self.n_non_null > self.n_rows:
            raise ValueError("n_non_null cannot exceed n_rows")
        if self.cardinality < 0:
            raise ValueError("cardinality must be >= 0")

    @property
    def null_fraction(self) -> float:
        """Fraction of rows that were empty for this column."""
        if self.n_rows == 0:
            return 0.0
        return (self.n_rows - self.n_non_null) / self.n_rows

    @property
    def is_high_cardinality(self) -> bool:
        """``True`` if cardinality hit the cap (treat as not-an-enum)."""
        return self.cardinality > MAX_CARDINALITY


@dataclass(frozen=True, slots=True)
class InferredSchema:
    """Inferred schema for an entire CSV file."""

    source_name: str  # filename or stream-id
    delimiter: str  # e.g. ",", "\t", ";"
    has_header: bool
    n_rows_scanned: int
    columns: tuple[InferredColumn, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.source_name:
            raise ValueError("source_name must be non-empty")
        if not self.delimiter:
            raise ValueError("delimiter must be non-empty")
        if self.n_rows_scanned < 0:
            raise ValueError("n_rows_scanned must be >= 0")
        names = [c.name for c in self.columns]
        if len(names) != len(set(names)):
            raise ValueError(f"duplicate column names: {names}")

    def column(self, name: str) -> InferredColumn:
        """Look up a column by name; raises ``KeyError`` if absent."""
        for c in self.columns:
            if c.name == name:
                return c
        raise KeyError(name)


__all__ = [
    "MAX_CARDINALITY",
    "ColumnType",
    "InferredColumn",
    "InferredSchema",
]
