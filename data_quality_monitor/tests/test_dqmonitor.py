"""Comprehensive test suite for dqmonitor (40+ tests including Hypothesis)."""

from __future__ import annotations

import json
import threading
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from dqmonitor.audit import AuditLog, ValidationRun
from dqmonitor.expectations import ExpectationSuite
from dqmonitor.gate import QualityGate
from dqmonitor.monitor import QualityMonitor
from dqmonitor.rules import (
    CustomPredicateRule,
    NotNullRule,
    RangeCheckRule,
    ReferentialIntegrityRule,
    RegexMatchRule,
    UniqueRule,
)
from dqmonitor.validator import ValidationResult, Validator

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def make_batch(*records: dict[str, Any]) -> list[dict[str, object]]:
    return list(records)


# ---------------------------------------------------------------------------
# TestNotNullRule
# ---------------------------------------------------------------------------


class TestNotNullRule:
    def test_null_field_fails(self) -> None:
        rule = NotNullRule("x")
        assert rule.check({"x": None}) is False

    def test_present_field_passes(self) -> None:
        rule = NotNullRule("x")
        assert rule.check({"x": 42}) is True

    def test_missing_key_fails(self) -> None:
        rule = NotNullRule("x")
        assert rule.check({"y": 1}) is False

    def test_empty_string_passes(self) -> None:
        rule = NotNullRule("x")
        assert rule.check({"x": ""}) is True

    def test_zero_passes(self) -> None:
        rule = NotNullRule("x")
        assert rule.check({"x": 0}) is True

    def test_name(self) -> None:
        rule = NotNullRule("col")
        assert "col" in rule.name

    def test_description(self) -> None:
        rule = NotNullRule("col")
        assert "col" in rule.description


# ---------------------------------------------------------------------------
# TestUniqueRule
# ---------------------------------------------------------------------------


class TestUniqueRule:
    def test_duplicates_fail(self) -> None:
        rule = UniqueRule("id")
        assert rule.check({"id": 1}) is True
        assert rule.check({"id": 1}) is False

    def test_unique_values_pass(self) -> None:
        rule = UniqueRule("id")
        for i in range(5):
            assert rule.check({"id": i}) is True

    def test_resets_between_batches(self) -> None:
        rule = UniqueRule("id")
        validator = Validator([rule])
        batch1 = make_batch({"id": 1}, {"id": 2})
        r1 = validator.validate(batch1)
        assert r1.failed == 0
        # Same batch again — rule state should be reset
        r2 = validator.validate(batch1)
        assert r2.failed == 0

    def test_name(self) -> None:
        rule = UniqueRule("col")
        assert "col" in rule.name

    def test_reset_clears_seen(self) -> None:
        rule = UniqueRule("id")
        rule.check({"id": 99})
        rule.reset()
        assert rule.check({"id": 99}) is True


# ---------------------------------------------------------------------------
# TestRangeCheckRule
# ---------------------------------------------------------------------------


class TestRangeCheckRule:
    def test_in_range_passes(self) -> None:
        rule = RangeCheckRule("score", 0, 100)
        assert rule.check({"score": 50}) is True

    def test_lower_boundary_passes(self) -> None:
        rule = RangeCheckRule("score", 0, 100)
        assert rule.check({"score": 0}) is True

    def test_upper_boundary_passes(self) -> None:
        rule = RangeCheckRule("score", 0, 100)
        assert rule.check({"score": 100}) is True

    def test_below_range_fails(self) -> None:
        rule = RangeCheckRule("score", 0, 100)
        assert rule.check({"score": -1}) is False

    def test_above_range_fails(self) -> None:
        rule = RangeCheckRule("score", 0, 100)
        assert rule.check({"score": 101}) is False

    def test_non_numeric_fails(self) -> None:
        rule = RangeCheckRule("score", 0, 100)
        assert rule.check({"score": "abc"}) is False

    def test_none_fails(self) -> None:
        rule = RangeCheckRule("score", 0, 100)
        assert rule.check({"score": None}) is False

    def test_missing_key_fails(self) -> None:
        rule = RangeCheckRule("score", 0, 100)
        assert rule.check({}) is False

    def test_float_value_passes(self) -> None:
        rule = RangeCheckRule("price", 1.0, 9.99)
        assert rule.check({"price": 5.5}) is True


# ---------------------------------------------------------------------------
# TestRegexMatchRule
# ---------------------------------------------------------------------------


class TestRegexMatchRule:
    def test_matching_pattern_passes(self) -> None:
        rule = RegexMatchRule("email", r".+@.+\..+")
        assert rule.check({"email": "a@b.com"}) is True

    def test_non_matching_fails(self) -> None:
        rule = RegexMatchRule("email", r".+@.+\..+")
        assert rule.check({"email": "not-an-email"}) is False

    def test_none_value_fails(self) -> None:
        rule = RegexMatchRule("code", r"[A-Z]{3}")
        assert rule.check({"code": None}) is False

    def test_missing_key_fails(self) -> None:
        rule = RegexMatchRule("code", r"[A-Z]{3}")
        assert rule.check({}) is False

    def test_partial_match_treated_as_pass(self) -> None:
        # re.match matches from the start but not necessarily the full string
        rule = RegexMatchRule("code", r"ABC")
        assert rule.check({"code": "ABCDEF"}) is True

    def test_name_contains_column_and_pattern(self) -> None:
        rule = RegexMatchRule("col", r"\d+")
        assert "col" in rule.name
        assert r"\d+" in rule.name


# ---------------------------------------------------------------------------
# TestReferentialIntegrityRule
# ---------------------------------------------------------------------------


class TestReferentialIntegrityRule:
    def test_valid_value_passes(self) -> None:
        rule = ReferentialIntegrityRule("status", {"active", "inactive"})
        assert rule.check({"status": "active"}) is True

    def test_invalid_value_fails(self) -> None:
        rule = ReferentialIntegrityRule("status", {"active", "inactive"})
        assert rule.check({"status": "deleted"}) is False

    def test_none_not_in_set_fails(self) -> None:
        rule = ReferentialIntegrityRule("status", {"active"})
        assert rule.check({"status": None}) is False

    def test_none_in_set_passes(self) -> None:
        rule = ReferentialIntegrityRule("status", {None, "active"})
        assert rule.check({"status": None}) is True

    def test_missing_key_fails(self) -> None:
        rule = ReferentialIntegrityRule("status", {"active"})
        assert rule.check({}) is False

    def test_name(self) -> None:
        rule = ReferentialIntegrityRule("col", {"a"})
        assert "col" in rule.name


# ---------------------------------------------------------------------------
# TestCustomPredicateRule
# ---------------------------------------------------------------------------


class TestCustomPredicateRule:
    def test_callable_predicate_true(self) -> None:
        rule = CustomPredicateRule("positive_age", lambda r: int(r.get("age", 0)) > 0)
        assert rule.check({"age": 5}) is True

    def test_callable_predicate_false(self) -> None:
        rule = CustomPredicateRule("positive_age", lambda r: int(r.get("age", 0)) > 0)
        assert rule.check({"age": -1}) is False

    def test_name_property(self) -> None:
        rule = CustomPredicateRule("my_rule", lambda _r: True, "desc")
        assert rule.name == "my_rule"

    def test_description_property(self) -> None:
        rule = CustomPredicateRule("my_rule", lambda _r: True, "my desc")
        assert rule.description == "my desc"

    def test_default_description(self) -> None:
        rule = CustomPredicateRule("my_rule", lambda _r: True)
        assert "my_rule" in rule.description


# ---------------------------------------------------------------------------
# TestValidator
# ---------------------------------------------------------------------------


class TestValidator:
    def test_mixed_rules(self) -> None:
        rules = [NotNullRule("a"), RangeCheckRule("b", 0, 10)]
        v = Validator(rules)
        batch = make_batch({"a": "x", "b": 5}, {"a": None, "b": 5}, {"a": "x", "b": 99})
        result = v.validate(batch)
        assert result.total == 3
        assert result.failed == 2  # record 1 (a=None) and record 2 (b=99)

    def test_pass_rate_calculation(self) -> None:
        rule = NotNullRule("x")
        v = Validator([rule])
        batch = make_batch({"x": 1}, {"x": 2}, {"x": None}, {"x": None})
        result = v.validate(batch)
        assert result.pass_rate == pytest.approx(0.5)

    def test_violations_list_populated(self) -> None:
        rule = NotNullRule("x")
        v = Validator([rule])
        batch = make_batch({"x": None})
        result = v.validate(batch)
        assert len(result.violations) == 1
        assert result.violations[0].rule_name == rule.name
        assert result.violations[0].record_index == 0

    def test_empty_batch_returns_pass_rate_one(self) -> None:
        v = Validator([NotNullRule("x")])
        result = v.validate([])
        assert result.pass_rate == 1.0
        assert result.total == 0

    def test_all_pass(self) -> None:
        v = Validator([NotNullRule("x")])
        result = v.validate(make_batch({"x": 1}, {"x": 2}))
        assert result.failed == 0
        assert result.pass_rate == 1.0

    def test_violation_holds_value(self) -> None:
        rule = RangeCheckRule("score", 0, 10)
        v = Validator([rule])
        batch = make_batch({"score": 999})
        result = v.validate(batch)
        assert result.violations[0].value == 999

    def test_multiple_rules_same_record(self) -> None:
        # One bad record with two failing rules → still counts as 1 failed record
        rules = [NotNullRule("a"), NotNullRule("b")]
        v = Validator(rules)
        result = v.validate(make_batch({"a": None, "b": None}))
        assert result.failed == 1
        assert len(result.violations) == 2


# ---------------------------------------------------------------------------
# TestExpectationSuite
# ---------------------------------------------------------------------------


class TestExpectationSuite:
    def test_add_rules(self) -> None:
        suite = ExpectationSuite("test_suite")
        suite.add_rule(NotNullRule("x"))
        suite.add_rule(RangeCheckRule("y", 0, 100))
        assert len(suite.rules) == 2

    def test_json_round_trip_not_null(self) -> None:
        suite = ExpectationSuite("s")
        suite.add_rule(NotNullRule("col"))
        restored = ExpectationSuite.from_json(suite.to_json())
        assert len(restored.rules) == 1
        assert isinstance(restored.rules[0], NotNullRule)

    def test_json_round_trip_range(self) -> None:
        suite = ExpectationSuite("s")
        suite.add_rule(RangeCheckRule("val", 1.0, 9.0))
        restored = ExpectationSuite.from_json(suite.to_json())
        rule = restored.rules[0]
        assert isinstance(rule, RangeCheckRule)
        assert rule.min_val == pytest.approx(1.0)
        assert rule.max_val == pytest.approx(9.0)

    def test_json_round_trip_regex(self) -> None:
        suite = ExpectationSuite("s")
        suite.add_rule(RegexMatchRule("code", r"\d{3}"))
        restored = ExpectationSuite.from_json(suite.to_json())
        assert isinstance(restored.rules[0], RegexMatchRule)
        assert restored.rules[0].pattern == r"\d{3}"

    def test_json_round_trip_referential(self) -> None:
        suite = ExpectationSuite("s")
        suite.add_rule(ReferentialIntegrityRule("status", {"a", "b"}))
        restored = ExpectationSuite.from_json(suite.to_json())
        assert isinstance(restored.rules[0], ReferentialIntegrityRule)

    def test_json_round_trip_unique(self) -> None:
        suite = ExpectationSuite("s")
        suite.add_rule(UniqueRule("id"))
        restored = ExpectationSuite.from_json(suite.to_json())
        assert isinstance(restored.rules[0], UniqueRule)

    def test_reconstruct_from_json_preserves_name(self) -> None:
        suite = ExpectationSuite("my_suite")
        restored = ExpectationSuite.from_json(suite.to_json())
        assert restored.name == "my_suite"

    def test_json_is_valid_json(self) -> None:
        suite = ExpectationSuite("s")
        suite.add_rule(NotNullRule("x"))
        data = json.loads(suite.to_json())
        assert "rules" in data


# ---------------------------------------------------------------------------
# TestQualityGate
# ---------------------------------------------------------------------------


class TestQualityGate:
    def test_open_when_above_threshold(self) -> None:
        gate = QualityGate(threshold=0.9)
        assert gate.update(1.0) is True
        assert gate.is_blocked() is False

    def test_blocked_when_below_threshold(self) -> None:
        gate = QualityGate(threshold=0.9)
        assert gate.update(0.8) is False
        assert gate.is_blocked() is True

    def test_exact_threshold_is_open(self) -> None:
        gate = QualityGate(threshold=0.9)
        assert gate.update(0.9) is True

    def test_transition_blocked_to_open(self) -> None:
        gate = QualityGate(threshold=0.8)
        gate.update(0.5)
        assert gate.is_blocked() is True
        gate.update(1.0)
        assert gate.is_blocked() is False

    def test_manual_reset(self) -> None:
        gate = QualityGate(threshold=0.99)
        gate.update(0.0)
        assert gate.is_blocked() is True
        gate.reset()
        assert gate.is_blocked() is False

    def test_invalid_threshold_raises(self) -> None:
        with pytest.raises(ValueError):
            QualityGate(threshold=1.5)

    def test_thread_safety(self) -> None:
        gate = QualityGate(threshold=0.5)
        results: list[bool] = []
        lock = threading.Lock()

        def worker(rate: float) -> None:
            res = gate.update(rate)
            with lock:
                results.append(res)

        threads = [threading.Thread(target=worker, args=(i / 20,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(results) == 20


# ---------------------------------------------------------------------------
# TestQualityMonitor
# ---------------------------------------------------------------------------


class TestQualityMonitor:
    def test_end_to_end_batch_processing(self) -> None:
        suite = ExpectationSuite("e2e")
        suite.add_rule(NotNullRule("id"))
        gate = QualityGate(threshold=0.8)
        monitor = QualityMonitor(suite=suite, gate=gate)
        batch = make_batch({"id": 1}, {"id": 2}, {"id": None})
        result = monitor.process_batch(batch)
        assert result.total == 3
        assert result.failed == 1
        assert result.pass_rate == pytest.approx(2 / 3)

    def test_gate_updates_after_batch(self) -> None:
        suite = ExpectationSuite("gate_test")
        suite.add_rule(NotNullRule("x"))
        gate = QualityGate(threshold=0.9)
        monitor = QualityMonitor(suite=suite, gate=gate)
        # Only 1 out of 10 passes → below threshold
        batch = make_batch(*[{"x": None}] * 9 + [{"x": 1}])
        monitor.process_batch(batch)
        assert gate.is_blocked() is True

    def test_audit_log_written(self, tmp_path: Path) -> None:
        suite = ExpectationSuite("audit_test")
        suite.add_rule(NotNullRule("v"))
        audit = AuditLog(tmp_path / "audit.jsonl")
        monitor = QualityMonitor(suite=suite, audit_log=audit)
        monitor.process_batch(make_batch({"v": 1}))
        runs = audit.query()
        assert len(runs) == 1
        assert runs[0].suite_name == "audit_test"

    def test_returns_validation_result_type(self) -> None:
        suite = ExpectationSuite("t")
        monitor = QualityMonitor(suite=suite)
        result = monitor.process_batch([])
        assert isinstance(result, ValidationResult)


# ---------------------------------------------------------------------------
# TestAuditLog
# ---------------------------------------------------------------------------


class TestAuditLog:
    def _make_run(self, suite: str = "s", pass_rate: float = 1.0) -> ValidationRun:
        return ValidationRun(
            run_id="test-id",
            suite_name=suite,
            timestamp=ValidationRun.now_iso(),
            pass_rate=pass_rate,
            total=10,
            failed=0,
            gate_status="open",
        )

    def test_append_and_query(self, tmp_path: Path) -> None:
        log = AuditLog(tmp_path / "audit.jsonl")
        run = self._make_run()
        log.append(run)
        runs = log.query(last_n=5)
        assert len(runs) == 1
        assert runs[0].suite_name == "s"

    def test_jsonl_format(self, tmp_path: Path) -> None:
        path = tmp_path / "audit.jsonl"
        log = AuditLog(path)
        log.append(self._make_run())
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 1
        obj = json.loads(lines[0])
        assert "run_id" in obj
        assert "pass_rate" in obj

    def test_persistence_across_instances(self, tmp_path: Path) -> None:
        path = tmp_path / "audit.jsonl"
        log1 = AuditLog(path)
        log1.append(self._make_run("suite_a"))
        log2 = AuditLog(path)
        log2.append(self._make_run("suite_b"))
        runs = log2.query(last_n=10)
        assert len(runs) == 2
        assert {r.suite_name for r in runs} == {"suite_a", "suite_b"}

    def test_query_last_n(self, tmp_path: Path) -> None:
        log = AuditLog(tmp_path / "audit.jsonl")
        for i in range(20):
            log.append(self._make_run(f"s{i}"))
        runs = log.query(last_n=5)
        assert len(runs) == 5
        assert runs[-1].suite_name == "s19"

    def test_clear(self, tmp_path: Path) -> None:
        log = AuditLog(tmp_path / "audit.jsonl")
        log.append(self._make_run())
        log.clear()
        assert log.query() == []

    def test_query_empty_log(self, tmp_path: Path) -> None:
        log = AuditLog(tmp_path / "audit.jsonl")
        assert log.query() == []

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        path = tmp_path / "deep" / "nested" / "audit.jsonl"
        log = AuditLog(path)
        log.append(self._make_run())
        assert path.exists()


# ---------------------------------------------------------------------------
# TestProperties (Hypothesis)
# ---------------------------------------------------------------------------

_record_strategy = st.fixed_dictionaries(
    {
        "id": st.one_of(st.integers(min_value=1, max_value=1000), st.none()),
        "score": st.one_of(st.floats(min_value=-200, max_value=200), st.none()),
        "label": st.one_of(st.text(max_size=5), st.none()),
    }
)


@settings(max_examples=60, deadline=2000)
@given(batch=st.lists(_record_strategy, min_size=0, max_size=50))
def test_pass_rate_always_in_0_1(batch: list[dict[str, object]]) -> None:
    """pass_rate is always in [0.0, 1.0]."""
    rules = [NotNullRule("id"), RangeCheckRule("score", 0, 100)]
    v = Validator(rules)
    result = v.validate(batch)
    assert 0.0 <= result.pass_rate <= 1.0


@settings(max_examples=60, deadline=2000)
@given(batch=st.lists(_record_strategy, min_size=1, max_size=50))
def test_passed_plus_failed_equals_total(batch: list[dict[str, object]]) -> None:
    """passed + failed == total for any non-empty batch."""
    rules = [NotNullRule("id"), RangeCheckRule("score", -10, 10)]
    v = Validator(rules)
    result = v.validate(batch)
    assert result.passed + result.failed == result.total


@settings(max_examples=60, deadline=2000)
@given(batch=st.lists(_record_strategy, min_size=1, max_size=50))
def test_violated_records_le_total(batch: list[dict[str, object]]) -> None:
    """Number of distinct violated record indices is at most total."""
    rules = [
        NotNullRule("id"),
        NotNullRule("score"),
        RangeCheckRule("score", 0, 50),
    ]
    v = Validator(rules)
    result = v.validate(batch)
    violated_indices = {viol.record_index for viol in result.violations}
    assert len(violated_indices) <= result.total


@settings(max_examples=40, deadline=2000)
@given(
    pass_rate=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    threshold=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
)
def test_gate_pass_rate_threshold_consistency(pass_rate: float, threshold: float) -> None:
    """Gate.is_blocked() is always consistent with threshold vs pass_rate."""
    assume(not (pass_rate != pass_rate))  # exclude NaN
    gate = QualityGate(threshold=threshold)
    open_ = gate.update(pass_rate)
    if pass_rate >= threshold:
        assert open_ is True
        assert gate.is_blocked() is False
    else:
        assert open_ is False
        assert gate.is_blocked() is True
