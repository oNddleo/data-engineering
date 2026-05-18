"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from dqkit.io_jsonl import (
    dump_results,
    dump_rows,
    load_results,
    load_rows,
    suite_from_json,
    suite_to_json,
)
from dqkit.schema import CheckResult, CheckSpec, FailedRow, Severity, Suite


def test_rows_roundtrip_simple():
    rows: list[dict[str, str | int | None]] = [
        {"x": "a", "n": 1},
        {"x": None, "n": 0},
    ]
    back = load_rows(dump_rows(rows))
    assert back == rows


def test_suite_roundtrip():
    suite = Suite(
        name="t",
        specs=(
            CheckSpec(check="not_null", column="x", severity=Severity.ERROR),
            CheckSpec(
                check="in_set", column="y", severity=Severity.WARNING, args={"allowed": "A,B"}
            ),
        ),
    )
    back = suite_from_json(suite_to_json(suite))
    assert back == suite


def test_suite_decoder_rejects_missing_name():
    bad = '{"specs": [{"check": "not_null", "column": "x", "severity": "ERROR"}]}'
    with pytest.raises(TypeError, match="name"):
        suite_from_json(bad)


def test_suite_decoder_rejects_empty_specs():
    bad = '{"name": "t", "specs": []}'
    with pytest.raises(TypeError, match="specs"):
        suite_from_json(bad)


def test_suite_decoder_rejects_bad_args_type():
    bad = (
        '{"name": "t", "specs": ['
        '{"check": "in_set", "column": "x", "severity": "ERROR",'
        ' "args": {"allowed": 42}}'
        "]}"
    )
    with pytest.raises(TypeError, match="args"):
        suite_from_json(bad)


def test_result_roundtrip_with_failures():
    r = CheckResult(
        check_name="not_null",
        column="x",
        severity=Severity.ERROR,
        n_rows=3,
        n_passed=1,
        failures=(
            FailedRow(row_index=1, column="x", value=None, reason="null"),
            FailedRow(row_index=2, column="x", value="", reason="empty"),
        ),
    )
    [back] = load_results(dump_results([r]))
    assert back == r


def test_result_roundtrip_with_int_failure_value():
    r = CheckResult(
        check_name="range_int",
        column="age",
        severity=Severity.ERROR,
        n_rows=1,
        n_passed=0,
        failures=(FailedRow(row_index=0, column="age", value=-5, reason="below"),),
    )
    [back] = load_results(dump_results([r]))
    assert back.failures[0].value == -5


def test_rows_coerce_floats_to_strings():
    """JSON floats land as JSON-encoded strings (defensive type-uniformity)."""
    import json

    raw = json.dumps({"x": 1.5})
    [row] = load_rows(raw)
    assert row["x"] == "1.5"


def test_rows_blank_lines_skipped():
    text = dump_rows([{"x": "1"}])
    padded = "\n\n" + text + "\n\n"
    assert load_rows(padded) == [{"x": "1"}]
