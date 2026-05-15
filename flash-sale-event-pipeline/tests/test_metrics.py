"""Metrics tests."""

from __future__ import annotations

import time

from flashpipe.metrics import MetricsCollector

from ._fixtures import t_at


def test_empty_snapshot_has_zero_throughput():
    m = MetricsCollector()
    s = m.snapshot()
    assert s.n_events == 0
    assert s.throughput_events_per_sec == 0.0


def test_record_event_increments_counters():
    m = MetricsCollector()
    m.record(
        event_time=t_at(0),
        wall_clock_before=time.perf_counter(),
        wall_clock_after=time.perf_counter(),
        processed_at_wall=t_at(0),
    )
    s = m.snapshot()
    assert s.n_events == 1
    assert s.throughput_events_per_sec > 0


def test_mark_late_increments_late_counter():
    m = MetricsCollector()
    m.mark_late()
    m.mark_late()
    s = m.snapshot()
    assert s.n_late_events == 2


def test_lag_is_computed():
    m = MetricsCollector()
    m.record(
        event_time=t_at(0),
        wall_clock_before=0.0,
        wall_clock_after=0.001,
        processed_at_wall=t_at(0.5),
    )
    s = m.snapshot()
    # lag = 500 ms
    assert 499 <= s.lag_ms_max <= 501


def test_latency_p95_basic():
    m = MetricsCollector()
    for _ in range(100):
        m.record(
            event_time=t_at(0),
            wall_clock_before=0.0,
            wall_clock_after=0.001,
            processed_at_wall=t_at(0),
        )
    s = m.snapshot()
    # All samples are 1 ms — p50, p95, max should all be ~1.
    assert 0.5 < s.latency_ms_p50 < 1.5
    assert 0.5 < s.latency_ms_p95 < 1.5


def test_percentile_interpolates_at_extremes():
    """p100 should equal max."""
    m = MetricsCollector()
    for ms in (1, 2, 3, 4, 5):
        m.record(
            event_time=t_at(0),
            wall_clock_before=0.0,
            wall_clock_after=ms / 1000,
            processed_at_wall=t_at(0),
        )
    s = m.snapshot()
    assert s.latency_ms_max == 5.0
