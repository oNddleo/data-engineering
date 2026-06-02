"""Generic check behaviour."""

from __future__ import annotations

import pytest

from dqkit.checks_generic import (
    dtype_int,
    dtype_str,
    in_set,
    not_null,
    range_int,
    regex,
    unique,
)
from dqkit.schema import Severity


def _run(check, rows, column):  # type: ignore[no-untyped-def]
    return check(rows, column)


# ---------- not_null ------------------------------------------------------


def test_not_null_flags_none_and_empty():
    rows = [{"x": "ok"}, {"x": None}, {"x": ""}, {"x": "ok2"}]
    r = _run(not_null(), rows, "x")
    assert r.n_failed == 2
    indices = sorted(f.row_index for f in r.failures)
    assert indices == [1, 2]


def test_not_null_severity_is_caller_choice():
    r = _run(not_null(severity=Severity.WARNING), [{"x": None}], "x")
    assert r.severity is Severity.WARNING


def test_not_null_zero_is_not_a_failure():
    """``0`` (int) is a valid value — only None / empty string flag."""
    r = _run(not_null(), [{"x": 0}], "x")
    assert r.passed is True


# ---------- unique --------------------------------------------------------


def test_unique_flags_duplicates_after_first():
    rows = [{"x": "a"}, {"x": "b"}, {"x": "a"}, {"x": "a"}]
    r = _run(unique(), rows, "x")
    assert r.n_failed == 2  # rows 2 and 3 flagged; row 0 is the first occurrence
    indices = sorted(f.row_index for f in r.failures)
    assert indices == [2, 3]


def test_unique_ignores_nulls():
    rows = [{"x": None}, {"x": None}, {"x": "a"}]
    r = _run(unique(), rows, "x")
    assert r.passed is True


def test_unique_passes_distinct_values():
    rows = [{"x": "a"}, {"x": "b"}, {"x": "c"}]
    r = _run(unique(), rows, "x")
    assert r.passed is True


# ---------- in_set --------------------------------------------------------


def test_in_set_flags_outsiders():
    rows = [{"tier": "BASIC"}, {"tier": "WEIRD"}, {"tier": "MALL"}]
    r = _run(in_set({"BASIC", "STANDARD", "PREFERRED", "MALL"}), rows, "tier")
    assert r.n_failed == 1
    assert r.failures[0].row_index == 1


def test_in_set_passes_none_silently():
    """``None`` is not flagged — pair with ``not_null`` if presence is required."""
    rows = [{"tier": None}]
    r = _run(in_set({"BASIC"}), rows, "tier")
    assert r.passed is True


# ---------- regex --------------------------------------------------------


def test_regex_fullmatch_required():
    rows = [{"x": "abc"}, {"x": "abcd"}, {"x": ""}]
    r = _run(regex(r"abc"), rows, "x")
    # "abc" matches; "abcd" doesn't fullmatch.
    assert r.n_failed >= 1
    failed_values = {f.value for f in r.failures}
    assert "abcd" in failed_values


def test_regex_skips_non_strings():
    rows = [{"x": 42}, {"x": None}, {"x": "ok"}]
    r = _run(regex(r"ok"), rows, "x")
    assert r.passed is True


# ---------- range_int ----------------------------------------------------


def test_range_int_flags_below():
    rows = [{"x": -1}, {"x": 5}, {"x": 100}]
    r = _run(range_int(0, 50), rows, "x")
    assert r.n_failed == 2
    indices = sorted(f.row_index for f in r.failures)
    assert indices == [0, 2]


def test_range_int_rejects_bad_bounds():
    with pytest.raises(ValueError):
        range_int(10, 5)


def test_range_int_skips_non_ints():
    rows = [{"x": None}, {"x": "string"}, {"x": True}]
    r = _run(range_int(0, 100), rows, "x")
    # All three skipped because none is a non-bool int.
    assert r.passed is True


# ---------- dtype --------------------------------------------------------


def test_dtype_int_flags_strings():
    rows = [{"x": 1}, {"x": "two"}, {"x": 3}]
    r = _run(dtype_int(), rows, "x")
    assert r.n_failed == 1


def test_dtype_int_flags_bool():
    """``True`` is technically an ``int`` subclass — we still reject it."""
    rows = [{"x": True}, {"x": 1}]
    r = _run(dtype_int(), rows, "x")
    assert r.n_failed == 1


def test_dtype_str_flags_ints():
    rows = [{"x": "ok"}, {"x": 42}]
    r = _run(dtype_str(), rows, "x")
    assert r.n_failed == 1


def test_dtype_passes_none_silently():
    r = _run(dtype_int(), [{"x": None}], "x")
    assert r.passed is True
