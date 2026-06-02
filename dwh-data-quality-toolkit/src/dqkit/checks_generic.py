"""Generic checks — schema-agnostic validators.

Every check is a **factory** that takes its parameters and returns
a callable matching the :class:`Check` Protocol. Storing the
parameters in the factory means a registered Check carries its
own configuration; the runner just dispatches.

| Check       | Purpose                                            |
| ----------- | -------------------------------------------------- |
| ``not_null``| value is not ``None`` and not an empty string      |
| ``unique``  | every value in the column appears exactly once     |
| ``in_set``  | value is in a caller-supplied allowed set          |
| ``regex``   | value matches a regex (only applied to strings)    |
| ``range_int`` | int value is in ``[lo, hi]`` (inclusive)         |
| ``dtype_int`` | value is a non-bool ``int``                      |
| ``dtype_str`` | value is a ``str``                               |
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from dqkit.schema import CheckResult, FailedRow, Severity

if TYPE_CHECKING:
    from dqkit.schema import Row


# ---------- factories ------------------------------------------------------


def not_null(severity: Severity = Severity.ERROR) -> object:
    """Reject ``None`` and empty strings."""

    def _check(rows: list[Row], column: str) -> CheckResult:
        failures: list[FailedRow] = []
        for i, row in enumerate(rows):
            v = row.get(column)
            if v is None or (isinstance(v, str) and not v):
                failures.append(
                    FailedRow(
                        row_index=i,
                        column=column,
                        value=v,
                        reason="value is null or empty",
                    )
                )
        return CheckResult(
            check_name="not_null",
            column=column,
            severity=severity,
            n_rows=len(rows),
            n_passed=len(rows) - len(failures),
            failures=tuple(failures),
        )

    _check.name = "not_null"  # type: ignore[attr-defined]
    _check.severity = severity  # type: ignore[attr-defined]
    return _check


def unique(severity: Severity = Severity.ERROR) -> object:
    """Every non-null value appears exactly once.

    Null / empty values are **not** flagged here — that's
    ``not_null``'s job, and double-counting them inflates the
    failure count misleadingly.
    """

    def _check(rows: list[Row], column: str) -> CheckResult:
        seen: dict[object, int] = {}
        first_index: dict[object, int] = {}
        for i, row in enumerate(rows):
            v = row.get(column)
            if v is None or (isinstance(v, str) and not v):
                continue
            if v in seen:
                seen[v] += 1
            else:
                seen[v] = 1
                first_index[v] = i
        failures: list[FailedRow] = []
        for i, row in enumerate(rows):
            v = row.get(column)
            if v is None or (isinstance(v, str) and not v):
                continue
            if seen[v] > 1 and i != first_index[v]:
                # Flag duplicates after the first occurrence.
                failures.append(
                    FailedRow(
                        row_index=i,
                        column=column,
                        value=v,
                        reason=f"duplicate (first seen at row {first_index[v]})",
                    )
                )
        return CheckResult(
            check_name="unique",
            column=column,
            severity=severity,
            n_rows=len(rows),
            n_passed=len(rows) - len(failures),
            failures=tuple(failures),
        )

    _check.name = "unique"  # type: ignore[attr-defined]
    _check.severity = severity  # type: ignore[attr-defined]
    return _check


def in_set(allowed: set[str | int], severity: Severity = Severity.ERROR) -> object:
    """Reject values outside an explicit allowed set. ``None`` passes
    silently — pair with ``not_null`` if presence is also required."""
    allowed_copy = frozenset(allowed)

    def _check(rows: list[Row], column: str) -> CheckResult:
        failures: list[FailedRow] = []
        for i, row in enumerate(rows):
            v = row.get(column)
            if v is None:
                continue
            if v not in allowed_copy:
                failures.append(
                    FailedRow(
                        row_index=i,
                        column=column,
                        value=v,
                        reason=f"value {v!r} not in allowed set",
                    )
                )
        return CheckResult(
            check_name="in_set",
            column=column,
            severity=severity,
            n_rows=len(rows),
            n_passed=len(rows) - len(failures),
            failures=tuple(failures),
        )

    _check.name = "in_set"  # type: ignore[attr-defined]
    _check.severity = severity  # type: ignore[attr-defined]
    return _check


def regex(pattern: str, severity: Severity = Severity.ERROR) -> object:
    """Reject strings not matching ``pattern``. Non-strings (None, int)
    are skipped — pair with ``dtype_str`` if needed."""
    compiled = re.compile(pattern)

    def _check(rows: list[Row], column: str) -> CheckResult:
        failures: list[FailedRow] = []
        for i, row in enumerate(rows):
            v = row.get(column)
            if not isinstance(v, str):
                continue
            if not compiled.fullmatch(v):
                failures.append(
                    FailedRow(
                        row_index=i,
                        column=column,
                        value=v,
                        reason=f"value {v!r} does not match pattern {pattern!r}",
                    )
                )
        return CheckResult(
            check_name="regex",
            column=column,
            severity=severity,
            n_rows=len(rows),
            n_passed=len(rows) - len(failures),
            failures=tuple(failures),
        )

    _check.name = "regex"  # type: ignore[attr-defined]
    _check.severity = severity  # type: ignore[attr-defined]
    return _check


def range_int(lo: int, hi: int, severity: Severity = Severity.ERROR) -> object:
    """Reject ``int`` values outside ``[lo, hi]``. None / non-ints skipped."""
    if lo > hi:
        raise ValueError(f"lo {lo} must be <= hi {hi}")

    def _check(rows: list[Row], column: str) -> CheckResult:
        failures: list[FailedRow] = []
        for i, row in enumerate(rows):
            v = row.get(column)
            if not isinstance(v, int) or isinstance(v, bool):
                continue
            if not lo <= v <= hi:
                failures.append(
                    FailedRow(
                        row_index=i,
                        column=column,
                        value=v,
                        reason=f"value {v} not in [{lo}, {hi}]",
                    )
                )
        return CheckResult(
            check_name="range_int",
            column=column,
            severity=severity,
            n_rows=len(rows),
            n_passed=len(rows) - len(failures),
            failures=tuple(failures),
        )

    _check.name = "range_int"  # type: ignore[attr-defined]
    _check.severity = severity  # type: ignore[attr-defined]
    return _check


def dtype_int(severity: Severity = Severity.ERROR) -> object:
    """Reject values that aren't a non-bool ``int``. ``None`` passes."""

    def _check(rows: list[Row], column: str) -> CheckResult:
        failures: list[FailedRow] = []
        for i, row in enumerate(rows):
            v = row.get(column)
            if v is None:
                continue
            if not isinstance(v, int) or isinstance(v, bool):
                failures.append(
                    FailedRow(
                        row_index=i,
                        column=column,
                        value=v,
                        reason=f"value {v!r} is not int",
                    )
                )
        return CheckResult(
            check_name="dtype_int",
            column=column,
            severity=severity,
            n_rows=len(rows),
            n_passed=len(rows) - len(failures),
            failures=tuple(failures),
        )

    _check.name = "dtype_int"  # type: ignore[attr-defined]
    _check.severity = severity  # type: ignore[attr-defined]
    return _check


def dtype_str(severity: Severity = Severity.ERROR) -> object:
    """Reject values that aren't ``str``. ``None`` passes."""

    def _check(rows: list[Row], column: str) -> CheckResult:
        failures: list[FailedRow] = []
        for i, row in enumerate(rows):
            v = row.get(column)
            if v is None:
                continue
            if not isinstance(v, str):
                failures.append(
                    FailedRow(
                        row_index=i,
                        column=column,
                        value=v,
                        reason=f"value {v!r} is not str",
                    )
                )
        return CheckResult(
            check_name="dtype_str",
            column=column,
            severity=severity,
            n_rows=len(rows),
            n_passed=len(rows) - len(failures),
            failures=tuple(failures),
        )

    _check.name = "dtype_str"  # type: ignore[attr-defined]
    _check.severity = severity  # type: ignore[attr-defined]
    return _check


__all__ = [
    "dtype_int",
    "dtype_str",
    "in_set",
    "not_null",
    "range_int",
    "regex",
    "unique",
]
