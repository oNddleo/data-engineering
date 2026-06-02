"""Tests for PipelineTopology, JobMetrics, and BackpressureSignal."""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from mesh.metrics import BackpressureLevel, BackpressureSignal, JobMetrics, ThrottleCommand
from mesh.topology import JobNode, PipelineTopology

# ─────────────────────────────────────────────────────────────────────────────
# PipelineTopology
# ─────────────────────────────────────────────────────────────────────────────


class TestPipelineTopology:
    def test_linear_creates_chain(self) -> None:
        topo = PipelineTopology.linear("A", "B", "C")
        assert "A" in topo
        assert "B" in topo
        assert "C" in topo

    def test_upstream_ancestors_of_last_node(self) -> None:
        topo = PipelineTopology.linear("A", "B", "C")
        ancestors = topo.upstream_ancestors("C")
        assert "B" in ancestors
        assert "A" in ancestors
        assert ancestors["B"] == 1
        assert ancestors["A"] == 2

    def test_upstream_ancestors_of_first_node_empty(self) -> None:
        topo = PipelineTopology.linear("A", "B", "C")
        ancestors = topo.upstream_ancestors("A")
        assert ancestors == {}

    def test_downstream_descendants_of_first_node(self) -> None:
        topo = PipelineTopology.linear("A", "B", "C")
        descendants = topo.downstream_descendants("A")
        assert "B" in descendants
        assert "C" in descendants

    def test_add_edge_unknown_job_raises(self) -> None:
        topo = PipelineTopology()
        topo.add_job("X")
        with pytest.raises(KeyError):
            topo.add_edge("X", "UNKNOWN")

    def test_get_node_returns_job_node(self) -> None:
        topo = PipelineTopology.linear("A", "B")
        node = topo.get_node("A")
        assert isinstance(node, JobNode)
        assert node.job_id == "A"

    def test_all_jobs_count(self) -> None:
        topo = PipelineTopology.linear("A", "B", "C", "D")
        assert sum(1 for _ in topo.all_jobs()) == 4

    def test_propagation_weight_default(self) -> None:
        topo = PipelineTopology()
        node = topo.add_job("job1")
        assert node.propagation_weight == 1.0

    def test_propagation_weight_custom(self) -> None:
        topo = PipelineTopology()
        node = topo.add_job("job1", propagation_weight=0.5)
        assert node.propagation_weight == 0.5

    def test_not_contains_unknown(self) -> None:
        topo = PipelineTopology.linear("A", "B")
        assert "Z" not in topo


# ─────────────────────────────────────────────────────────────────────────────
# JobMetrics
# ─────────────────────────────────────────────────────────────────────────────


class TestJobMetrics:
    def test_input_utilization_full(self) -> None:
        m = JobMetrics("j", input_queue_depth=1000, input_queue_capacity=1000)
        assert m.input_utilization == pytest.approx(1.0)

    def test_input_utilization_half(self) -> None:
        m = JobMetrics("j", input_queue_depth=500, input_queue_capacity=1000)
        assert m.input_utilization == pytest.approx(0.5)

    def test_utilization_zero_capacity(self) -> None:
        m = JobMetrics("j", input_queue_capacity=0)
        assert m.input_utilization == pytest.approx(0.0)

    def test_throughput_ratio_balanced(self) -> None:
        m = JobMetrics("j", records_in_per_sec=100.0, records_out_per_sec=100.0)
        assert m.throughput_ratio == pytest.approx(1.0)

    def test_throughput_ratio_falling_behind(self) -> None:
        m = JobMetrics("j", records_in_per_sec=100.0, records_out_per_sec=50.0)
        assert m.throughput_ratio == pytest.approx(0.5)

    def test_backpressure_score_empty_queue_no_lag(self) -> None:
        m = JobMetrics("j")
        score = m.backpressure_score()
        assert 0.0 <= score <= 1.0

    def test_backpressure_score_full_queue(self) -> None:
        m = JobMetrics("j", input_queue_depth=1000, input_queue_capacity=1000)
        assert m.backpressure_score() == pytest.approx(1.0)


# ─────────────────────────────────────────────────────────────────────────────
# BackpressureSignal serialisation round-trip
# ─────────────────────────────────────────────────────────────────────────────


class TestBackpressureSignal:
    def test_to_dict_contains_required_keys(self) -> None:
        sig = BackpressureSignal("job-1", BackpressureLevel.HIGH, score=0.8)
        d = sig.to_dict()
        assert "source_job_id" in d
        assert "level" in d
        assert "score" in d

    def test_from_dict_roundtrip(self) -> None:
        sig = BackpressureSignal("job-1", BackpressureLevel.MEDIUM, score=0.5)
        d = sig.to_dict()
        sig2 = BackpressureSignal.from_dict(d)
        assert sig2.source_job_id == sig.source_job_id
        assert sig2.level == sig.level
        assert sig2.score == pytest.approx(sig.score)

    def test_throttle_command_to_dict(self) -> None:
        cmd = ThrottleCommand("job-2", throttle_factor=0.6, reason="high lag")
        d = cmd.to_dict()
        assert d["target_job_id"] == "job-2"
        assert d["throttle_factor"] == pytest.approx(0.6)

    def test_throttle_command_from_dict(self) -> None:
        cmd = ThrottleCommand("job-3", throttle_factor=0.3)
        d = cmd.to_dict()
        cmd2 = ThrottleCommand.from_dict(d)
        assert cmd2.target_job_id == cmd.target_job_id
        assert cmd2.throttle_factor == pytest.approx(cmd.throttle_factor)


# ─────────────────────────────────────────────────────────────────────────────
# Hypothesis property tests
# ─────────────────────────────────────────────────────────────────────────────


class TestProperties:
    @given(
        depth=st.integers(min_value=0, max_value=1000),
        capacity=st.integers(min_value=1, max_value=2000),
    )
    def test_input_utilization_in_unit_interval(self, depth: int, capacity: int) -> None:
        m = JobMetrics("j", input_queue_depth=depth, input_queue_capacity=capacity)
        assert 0.0 <= m.input_utilization <= 1.0

    @given(
        score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    def test_backpressure_signal_score_preserved(self, score: float) -> None:
        sig = BackpressureSignal("j", BackpressureLevel.LOW, score=score)
        d = sig.to_dict()
        sig2 = BackpressureSignal.from_dict(d)
        assert sig2.score == pytest.approx(score, abs=1e-9)

    @given(
        factor=st.floats(min_value=-10.0, max_value=10.0, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_throttle_factor_clamps_to_unit(self, factor: float) -> None:
        from mesh.throttle import TokenBucketThrottle

        t = TokenBucketThrottle(rate=100.0)
        t.set_throttle_factor(factor)
        assert 0.0 <= t._factor <= 1.0

    @given(n=st.integers(min_value=2, max_value=8))
    def test_linear_topo_ancestor_count(self, n: int) -> None:
        jobs = [f"job{i}" for i in range(n)]
        topo = PipelineTopology.linear(*jobs)
        last = jobs[-1]
        ancestors = topo.upstream_ancestors(last)
        assert len(ancestors) == n - 1
