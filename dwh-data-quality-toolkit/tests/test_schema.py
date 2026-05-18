"""Schema invariants."""

from __future__ import annotations

import pytest

from dqkit.schema import CheckResult, CheckSpec, FailedRow, Severity, Suite


def test_severity_two_values():
    assert {s.value for s in Severity} == {"ERROR", "WARNING"}


def test_check_result_passed_property():
    r = CheckResult(check_name="x", column="c", severity=Severity.ERROR, n_rows=10, n_passed=10)
    assert r.passed is True
    assert r.n_failed == 0


def test_check_result_n_failed_computed():
    r = CheckResult(check_name="x", column="c", severity=Severity.ERROR, n_rows=10, n_passed=7)
    assert r.n_failed == 3
    assert r.passed is False


def test_check_result_rejects_negative_n_rows():
    with pytest.raises(ValueError):
        CheckResult(check_name="x", column="c", severity=Severity.ERROR, n_rows=-1, n_passed=0)


def test_check_result_rejects_passed_above_rows():
    with pytest.raises(ValueError):
        CheckResult(check_name="x", column="c", severity=Severity.ERROR, n_rows=5, n_passed=10)


def test_check_result_rejects_empty_check_name():
    with pytest.raises(ValueError):
        CheckResult(check_name="", column="c", severity=Severity.ERROR, n_rows=0, n_passed=0)


def test_check_spec_rejects_empty_check():
    with pytest.raises(ValueError):
        CheckSpec(check="", column="c", severity=Severity.ERROR)


def test_check_spec_default_args_empty():
    s = CheckSpec(check="not_null", column="cccd", severity=Severity.ERROR)
    assert s.args == {}


def test_suite_rejects_empty_specs():
    with pytest.raises(ValueError):
        Suite(name="x", specs=())


def test_suite_rejects_empty_name():
    with pytest.raises(ValueError):
        Suite(name="", specs=(CheckSpec(check="not_null", column="c", severity=Severity.ERROR),))


def test_failed_row_record_carries_value():
    f = FailedRow(row_index=3, column="cccd", value="bad", reason="too short")
    assert f.row_index == 3
    assert f.value == "bad"
