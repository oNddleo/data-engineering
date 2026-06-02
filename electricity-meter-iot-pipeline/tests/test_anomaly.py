"""Anomaly detectors."""

from __future__ import annotations

from datetime import timedelta

import pytest

from evnmeter.anomaly import AnomalyKind, find_gaps, find_spikes, find_stuck

from ._fixtures import DEFAULT_TS, make_interval


def _iv(
    start_min: int,
    end_min: int,
    kwh: int = 50,
    *,
    is_estimated: bool = False,
    meter_id: str = "M-1",
):  # type: ignore[no-untyped-def]
    return make_interval(
        meter_id=meter_id,
        start_at=DEFAULT_TS + timedelta(minutes=start_min),
        end_at=DEFAULT_TS + timedelta(minutes=end_min),
        kwh_x100=kwh,
        is_estimated=is_estimated,
    )


def test_find_gaps_flags_long_estimated_run():
    intervals = [
        _iv(0, 30),
        _iv(30, 60, is_estimated=True),
        _iv(60, 90, is_estimated=True),
        _iv(90, 120, is_estimated=True),
        _iv(120, 150, is_estimated=True),
        _iv(150, 180),
    ]
    gaps = find_gaps(intervals, min_minutes=60)
    assert len(gaps) == 1
    assert gaps[0].kind is AnomalyKind.GAP
    assert gaps[0].metric == 120


def test_find_gaps_below_threshold_ignored():
    intervals = [_iv(0, 30), _iv(30, 60, is_estimated=True), _iv(60, 90)]
    assert find_gaps(intervals, min_minutes=60) == []


def test_find_gaps_trailing_run_caught():
    """A gap that extends to the end of the stream is still flagged."""
    intervals = [
        _iv(0, 30),
        _iv(30, 60, is_estimated=True),
        _iv(60, 90, is_estimated=True),
        _iv(90, 120, is_estimated=True),
    ]
    gaps = find_gaps(intervals, min_minutes=60)
    assert len(gaps) == 1


def test_find_gaps_validates():
    with pytest.raises(ValueError):
        find_gaps([], min_minutes=0)


def test_find_spikes_threshold():
    # 12 baseline intervals at 50 kWh×100/30min = 100 kWh×100/hour.
    intervals = [_iv(i * 30, (i + 1) * 30, kwh=50) for i in range(12)]
    # One spike: 1000 kWh×100/30min = 2000 kWh×100/hour = 20× baseline.
    intervals.append(_iv(360, 390, kwh=1000))
    spikes = find_spikes(intervals, multiplier=5.0)
    assert len(spikes) == 1
    assert spikes[0].kind is AnomalyKind.SPIKE


def test_find_spikes_min_history():
    """A meter with too few historical intervals is skipped."""
    intervals = [
        _iv(0, 30, kwh=50),
        _iv(30, 60, kwh=10_000),  # huge but no history → skipped
    ]
    assert find_spikes(intervals, min_historical_intervals=10) == []


def test_find_spikes_excludes_estimated_intervals():
    """Estimated intervals don't count as history nor as candidates."""
    intervals = [_iv(i * 30, (i + 1) * 30, kwh=50) for i in range(12)]
    intervals.append(_iv(360, 390, kwh=10_000, is_estimated=True))
    spikes = find_spikes(intervals, multiplier=5.0)
    assert spikes == []


def test_find_spikes_validates_multiplier():
    with pytest.raises(ValueError):
        find_spikes([], multiplier=1.0)


def test_find_stuck_long_zero_run():
    intervals = [_iv(i * 30, (i + 1) * 30, kwh=0) for i in range(15)]
    stuck = find_stuck(intervals, min_zero_intervals=12)
    assert len(stuck) == 1
    assert stuck[0].kind is AnomalyKind.STUCK
    assert stuck[0].metric == 15


def test_find_stuck_below_threshold_run_ignored():
    intervals = [_iv(i * 30, (i + 1) * 30, kwh=0) for i in range(5)]
    intervals += [_iv(150 + i * 30, 180 + i * 30, kwh=100) for i in range(5)]
    assert find_stuck(intervals, min_zero_intervals=12) == []


def test_find_stuck_near_zero_counts():
    """Intervals at or below the near-zero threshold count as stuck."""
    intervals = [_iv(i * 30, (i + 1) * 30, kwh=5) for i in range(15)]
    stuck = find_stuck(intervals, near_zero_threshold_x100=10)
    assert len(stuck) == 1


def test_find_stuck_above_threshold_breaks_run():
    """A real-consumption interval in the middle of a zero run breaks it."""
    intervals = (
        [_iv(i * 30, (i + 1) * 30, kwh=0) for i in range(6)]
        + [_iv(180, 210, kwh=200)]
        + [_iv(210 + i * 30, 240 + i * 30, kwh=0) for i in range(6)]
    )
    stuck = find_stuck(intervals, min_zero_intervals=12)
    # Neither run is long enough (6 + 6 ≠ 12).
    assert stuck == []


def test_find_stuck_validates():
    with pytest.raises(ValueError):
        find_stuck([], min_zero_intervals=0)
    with pytest.raises(ValueError):
        find_stuck([], near_zero_threshold_x100=-1)
