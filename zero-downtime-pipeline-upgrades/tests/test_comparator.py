"""Tests for the DivergenceTracker and dict_divergence helpers."""

from __future__ import annotations

import pytest

from pipeline_deployer.comparator import DivergenceTracker, dict_divergence

# ---------------------------------------------------------------------------
# dict_divergence
# ---------------------------------------------------------------------------


class TestDictDivergence:
    def test_identical_dicts_score_zero(self) -> None:
        out = {"a": 1, "b": "hello", "c": 3.14}
        assert dict_divergence(out, out) == 0.0

    def test_completely_different_keys(self) -> None:
        # One key missing entirely → that key scores 1.0
        score = dict_divergence({"a": 1}, {"b": 2})
        assert score == 1.0

    def test_one_key_differs(self) -> None:
        v1 = {"x": 10, "y": 20}
        v2 = {"x": 10, "y": 99}
        # One of two keys diverges → 0.5
        assert dict_divergence(v1, v2) == pytest.approx(0.5)

    def test_numeric_within_tolerance(self) -> None:
        v1 = {"val": 1.000000001}
        v2 = {"val": 1.000000002}
        assert dict_divergence(v1, v2, numeric_tolerance=1e-5) == 0.0

    def test_numeric_outside_tolerance(self) -> None:
        v1 = {"val": 1.0}
        v2 = {"val": 2.0}
        assert dict_divergence(v1, v2) == 1.0

    def test_nested_dict(self) -> None:
        v1 = {"meta": {"count": 5, "label": "a"}}
        v2 = {"meta": {"count": 5, "label": "b"}}
        # Inner dict: 1 of 2 fields differs → inner score 0.5 → outer 0.5
        assert dict_divergence(v1, v2) == pytest.approx(0.5)

    def test_list_fields_same_length_identical(self) -> None:
        v1 = {"scores": [1, 2, 3]}
        v2 = {"scores": [1, 2, 3]}
        assert dict_divergence(v1, v2) == 0.0

    def test_list_fields_different_length(self) -> None:
        v1 = {"scores": [1, 2, 3]}
        v2 = {"scores": [1, 2]}
        assert dict_divergence(v1, v2) == 1.0

    def test_ignore_keys(self) -> None:
        v1 = {"a": 1, "ts": 111111}
        v2 = {"a": 1, "ts": 999999}
        assert dict_divergence(v1, v2, ignore_keys={"ts"}) == 0.0

    def test_one_none_value(self) -> None:
        assert dict_divergence({"a": None}, {"a": 1}) == 1.0

    def test_both_none_value(self) -> None:
        assert dict_divergence({"a": None}, {"a": None}) == 0.0

    def test_empty_dicts(self) -> None:
        assert dict_divergence({}, {}) == 0.0

    def test_bool_fields(self) -> None:
        assert dict_divergence({"flag": True}, {"flag": True}) == 0.0
        assert dict_divergence({"flag": True}, {"flag": False}) == 1.0


# ---------------------------------------------------------------------------
# DivergenceTracker
# ---------------------------------------------------------------------------


class TestDivergenceTracker:
    def _tracker(self, window: int = 10) -> DivergenceTracker:
        return DivergenceTracker(window_size=window)

    def test_initial_state(self) -> None:
        t = self._tracker()
        assert t.sample_count == 0
        assert t.window_divergence_rate == 0.0
        assert t.mean_divergence_score == 0.0

    def test_identical_records_zero_divergence(self) -> None:
        t = self._tracker()
        for _ in range(20):
            score = t.record({"a": 1, "b": 2}, {"a": 1, "b": 2})
            assert score == 0.0
        assert t.window_divergence_rate == 0.0

    def test_all_divergent(self) -> None:
        t = self._tracker()
        for _ in range(20):
            t.record({"a": 1}, {"a": 2})
        assert t.window_divergence_rate == 1.0

    def test_rolling_window_evicts_old_scores(self) -> None:
        t = self._tracker(window=5)
        # 5 divergent records
        for _ in range(5):
            t.record({"a": 1}, {"a": 2})
        assert t.window_divergence_rate == 1.0
        # Now 5 identical records push out the old ones
        for _ in range(5):
            t.record({"a": 1}, {"a": 1})
        assert t.window_divergence_rate == 0.0

    def test_sample_count_unbounded(self) -> None:
        t = self._tracker(window=5)
        for i in range(20):
            t.record({"i": i}, {"i": i})
        assert t.sample_count == 20

    def test_summary_keys(self) -> None:
        t = self._tracker()
        t.record({"x": 1}, {"x": 2})
        s = t.summary()
        assert "total_compared" in s
        assert "window_divergence_rate" in s
        assert "mean_divergence_score" in s

    def test_reset_clears_state(self) -> None:
        t = self._tracker()
        for _ in range(10):
            t.record({"a": 1}, {"a": 2})
        t.reset()
        assert t.sample_count == 0
        assert t.window_divergence_rate == 0.0
