"""Data-quality framework — Check Protocol + result records.

Every check is a callable conforming to the :class:`Check` Protocol:
takes ``(rows, column)`` and returns a :class:`CheckResult` listing
any rows that failed. Severity is per-check, not global: a missing
``shop_name`` might be ERROR but a missing ``preferred_language`` is
WARNING.

The toolkit ships with **generic** checks (not_null, unique, in_set,
regex, range, dtype) and **VN-specific** checks (CCCD format / MST
checksum / VN phone / VN bank account / VN postal code). Production
callers compose them into a :class:`Suite` and run the suite against
a rowset.

A "row" here is just a ``dict[str, str | int | None]`` — strings for
text columns, ints for numeric, None for missing. Production callers
typically serialise their typed DW rows to this shape before passing
to ``run_suite``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

Row = dict[str, str | int | None]


class Severity(str, Enum):
    """Failures are graded so dashboards can split into blockers vs warnings."""

    ERROR = "ERROR"  # blocks the load
    WARNING = "WARNING"  # log + alert; load proceeds


class Check(Protocol):
    """Anything callable as ``check(rows, column) → CheckResult`` is a check."""

    name: str
    severity: Severity

    def __call__(self, rows: list[Row], column: str) -> CheckResult: ...


@dataclass(frozen=True, slots=True)
class FailedRow:
    """One row that failed one check — index into the input + the bad value."""

    row_index: int
    column: str
    value: str | int | None
    reason: str


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Outcome of running one check against one column over a rowset."""

    check_name: str
    column: str
    severity: Severity
    n_rows: int
    n_passed: int
    failures: tuple[FailedRow, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.check_name:
            raise ValueError("check_name must be non-empty")
        if not self.column:
            raise ValueError("column must be non-empty")
        if self.n_rows < 0:
            raise ValueError(f"n_rows must be >= 0, got {self.n_rows}")
        if self.n_passed < 0:
            raise ValueError(f"n_passed must be >= 0, got {self.n_passed}")
        if self.n_passed > self.n_rows:
            raise ValueError(f"n_passed ({self.n_passed}) must be <= n_rows ({self.n_rows})")

    @property
    def n_failed(self) -> int:
        return self.n_rows - self.n_passed

    @property
    def passed(self) -> bool:
        return self.n_failed == 0


@dataclass(frozen=True, slots=True)
class CheckSpec:
    """Recipe for a single check entry in a :class:`Suite`.

    The Suite is data — JSON-serialisable — so production callers can
    store it in source control alongside the schema and reload it
    without re-instantiating Check callables.
    """

    check: str  # name of the registered check (e.g. "not_null")
    column: str  # which column to run against
    severity: Severity
    args: dict[str, str] = field(default_factory=dict)  # extra params (e.g. {"regex": "..."})

    def __post_init__(self) -> None:
        if not self.check:
            raise ValueError("check must be non-empty")
        if not self.column:
            raise ValueError("column must be non-empty")


@dataclass(frozen=True, slots=True)
class Suite:
    """A reusable bundle of checks pinned to specific columns."""

    name: str
    specs: tuple[CheckSpec, ...]

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("name must be non-empty")
        if not self.specs:
            raise ValueError("suite must have at least one check spec")


__all__ = [
    "Check",
    "CheckResult",
    "CheckSpec",
    "FailedRow",
    "Row",
    "Severity",
    "Suite",
]
