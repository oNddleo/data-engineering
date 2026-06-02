"""Suite runner + quarantine."""

from __future__ import annotations

import pytest

from dqkit.runner import list_checks, quarantine_rows, run_suite, summarise
from dqkit.schema import CheckSpec, Severity, Suite


def test_list_checks_includes_vn():
    names = list_checks()
    for expected in ("cccd", "mst", "vn_phone", "vn_bank_account", "vn_postal_code"):
        assert expected in names


def test_list_checks_includes_generic():
    names = list_checks()
    for expected in ("not_null", "unique", "in_set", "regex", "range_int"):
        assert expected in names


def test_run_suite_executes_each_spec():
    rows = [{"x": "a"}, {"x": None}, {"x": "b"}]
    suite = Suite(
        name="t", specs=(CheckSpec(check="not_null", column="x", severity=Severity.ERROR),)
    )
    results = run_suite(rows, suite)
    assert len(results) == 1
    assert results[0].n_failed == 1


def test_run_suite_unknown_check_raises():
    suite = Suite(
        name="t", specs=(CheckSpec(check="NOT_REAL", column="x", severity=Severity.ERROR),)
    )
    with pytest.raises(KeyError, match="NOT_REAL"):
        run_suite([], suite)


def test_run_suite_in_set_with_args():
    rows = [{"t": "MALL"}, {"t": "PLATINUM"}]
    suite = Suite(
        name="t",
        specs=(
            CheckSpec(
                check="in_set",
                column="t",
                severity=Severity.ERROR,
                args={"allowed": "BASIC,STANDARD,PREFERRED,MALL"},
            ),
        ),
    )
    results = run_suite(rows, suite)
    assert results[0].n_failed == 1


def test_run_suite_in_set_missing_arg_raises():
    suite = Suite(
        name="t",
        specs=(
            CheckSpec(check="in_set", column="t", severity=Severity.ERROR),  # no allowed
        ),
    )
    with pytest.raises(ValueError, match="allowed"):
        run_suite([{"t": "a"}], suite)


def test_run_suite_regex_with_args():
    rows = [{"x": "abc"}, {"x": "xyz"}]
    suite = Suite(
        name="t",
        specs=(
            CheckSpec(check="regex", column="x", severity=Severity.ERROR, args={"pattern": "abc"}),
        ),
    )
    results = run_suite(rows, suite)
    assert results[0].n_failed == 1


def test_run_suite_range_int_with_args():
    rows = [{"x": 5}, {"x": -1}]
    suite = Suite(
        name="t",
        specs=(
            CheckSpec(
                check="range_int", column="x", severity=Severity.ERROR, args={"lo": "0", "hi": "10"}
            ),
        ),
    )
    results = run_suite(rows, suite)
    assert results[0].n_failed == 1


def test_quarantine_splits_on_error_failures():
    rows = [
        {"x": "a"},  # good
        {"x": None},  # ERROR — not_null
        {"x": "b"},  # good
    ]
    suite = Suite(
        name="t", specs=(CheckSpec(check="not_null", column="x", severity=Severity.ERROR),)
    )
    results = run_suite(rows, suite)
    good, bad = quarantine_rows(rows, results)
    assert len(good) == 2
    assert len(bad) == 1


def test_quarantine_ignores_warnings():
    """WARNING-severity failures do not quarantine rows."""
    rows = [{"x": None}, {"x": "a"}]
    suite = Suite(
        name="t", specs=(CheckSpec(check="not_null", column="x", severity=Severity.WARNING),)
    )
    results = run_suite(rows, suite)
    good, bad = quarantine_rows(rows, results)
    assert len(good) == 2
    assert len(bad) == 0


def test_summarise_counts_failures():
    rows = [{"x": None}, {"x": "ok"}]
    suite = Suite(
        name="t",
        specs=(
            CheckSpec(check="not_null", column="x", severity=Severity.ERROR),
            CheckSpec(check="dtype_str", column="x", severity=Severity.WARNING),
        ),
    )
    results = run_suite(rows, suite)
    summary = summarise(results)
    assert summary["n_checks"] == 2
    assert summary["n_failed"] == 1  # not_null fails; dtype_str passes (None skipped)
    by_sev = summary["by_severity"]
    assert isinstance(by_sev, dict)
    assert by_sev["ERROR"] == 1
    assert by_sev["WARNING"] == 0


def test_summarise_all_pass_no_failures():
    rows = [{"x": "a"}]
    suite = Suite(
        name="t", specs=(CheckSpec(check="not_null", column="x", severity=Severity.ERROR),)
    )
    summary = summarise(run_suite(rows, suite))
    assert summary["n_failed"] == 0
