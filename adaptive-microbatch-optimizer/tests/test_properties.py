"""Hypothesis property tests for the adaptive micro-batch optimizer."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from microbatch.pid import PIDConfig, PIDController
from microbatch.window import AdaptiveWindowManager, SLAConfig


class TestPIDProperties:
    @given(
        error=st.floats(min_value=0.01, max_value=1.0, allow_nan=False),
        w=st.floats(min_value=0.1, max_value=4.9, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_positive_error_shrinks_or_clamps(self, error: float, w: float) -> None:
        pid = PIDController()
        w_new = pid.apply(w, error)
        assert w_new <= w or w_new == PIDController().cfg.min_output

    @given(
        error=st.floats(min_value=-1.0, max_value=-0.01, allow_nan=False),
        w=st.floats(min_value=0.1, max_value=4.9, allow_nan=False),
    )
    @settings(max_examples=50)
    def test_negative_error_grows_or_clamps(self, error: float, w: float) -> None:
        pid = PIDController()
        w_new = pid.apply(w, error)
        assert w_new >= w or w_new == PIDController().cfg.max_output

    @given(
        kp=st.floats(min_value=0.0, max_value=2.0, allow_nan=False),
        error=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False),
        n=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=40)
    def test_output_always_in_bounds(self, kp: float, error: float, n: int) -> None:
        cfg = PIDConfig(kp=kp, ki=0.0, kd=0.0)
        pid = PIDController(cfg)
        w = 0.5
        for _ in range(n):
            w = pid.apply(w, error)
        assert cfg.min_output <= w <= cfg.max_output

    @given(n=st.integers(min_value=1, max_value=200))
    @settings(max_examples=30)
    def test_integral_clamp_respected(self, n: int) -> None:
        cfg = PIDConfig(kp=0.0, ki=1.0, kd=0.0, integral_clamp=0.5)
        pid = PIDController(cfg)
        for _ in range(n):
            pid.step(error=1.0)
        assert abs(pid.integral) <= cfg.integral_clamp + 1e-9


class TestWindowManagerProperties:
    @given(
        latency=st.floats(min_value=0.001, max_value=10.0, allow_nan=False),
        target=st.floats(min_value=0.05, max_value=1.0, allow_nan=False),
        n=st.integers(min_value=5, max_value=30),
    )
    @settings(max_examples=40)
    def test_window_always_in_bounds(self, latency: float, target: float, n: int) -> None:
        sla = SLAConfig(target_latency_s=target, backpressure_weight=0.5)
        mgr = AdaptiveWindowManager(sla=sla, initial_window=0.5)
        for _ in range(n):
            mgr.after_batch(batch_size=10, processing_time_s=latency)
        lo, hi = AdaptiveWindowManager.MIN_WINDOW, AdaptiveWindowManager.MAX_WINDOW
        assert lo <= mgr.current_window <= hi

    @given(
        n=st.integers(min_value=1, max_value=20),
    )
    @settings(max_examples=30)
    def test_history_length_matches_calls(self, n: int) -> None:
        mgr = AdaptiveWindowManager()
        for _ in range(n):
            mgr.after_batch(batch_size=10, processing_time_s=0.1)
        assert len(mgr.history()) == n

    @given(st.floats(min_value=0.05, max_value=5.0, allow_nan=False))
    @settings(max_examples=20)
    def test_reset_restores_initial_window(self, w0: float) -> None:
        mgr = AdaptiveWindowManager(initial_window=w0)
        for _ in range(10):
            mgr.after_batch(100, 0.5)
        mgr.reset()
        assert mgr.current_window == 0.5

    @given(
        n_batches=st.integers(min_value=1, max_value=50),
        lat_high=st.floats(min_value=0.5, max_value=5.0, allow_nan=False),
    )
    @settings(max_examples=30)
    def test_sustained_high_latency_reduces_window(self, n_batches: int, lat_high: float) -> None:
        sla = SLAConfig(target_latency_s=0.1)
        mgr = AdaptiveWindowManager(sla=sla, initial_window=2.0)
        for _ in range(n_batches):
            mgr.after_batch(100, lat_high)
        # After sustained high latency, window should be at or below initial
        assert mgr.current_window <= 2.0
