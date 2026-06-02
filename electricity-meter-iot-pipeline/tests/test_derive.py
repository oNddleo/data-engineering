"""Cumulative → delta derive pass: rollover, gaps, out-of-order, faults."""

from __future__ import annotations

from datetime import timedelta

import pytest

from evnmeter.derive import derive
from evnmeter.schema import METER_MAX_X100

from ._fixtures import DEFAULT_TS, make_reading


def _r(t_min: int, value: int, meter_id: str = "M-1"):  # type: ignore[no-untyped-def]
    return make_reading(
        meter_id=meter_id,
        cumulative_kwh_x100=value,
        observed_at=DEFAULT_TS + timedelta(minutes=t_min),
    )


def test_single_reading_produces_no_intervals():
    """One reading alone has nothing to delta — output is empty."""
    assert derive([_r(0, 100)]) == []


def test_two_readings_produce_one_interval():
    intervals = derive([_r(0, 1000), _r(30, 1200)])
    assert len(intervals) == 1
    assert intervals[0].kwh_x100 == 200
    assert intervals[0].is_estimated is False


def test_consecutive_readings_produce_consecutive_intervals():
    intervals = derive([_r(0, 1000), _r(30, 1200), _r(60, 1500)])
    assert len(intervals) == 2
    assert intervals[0].kwh_x100 == 200
    assert intervals[1].kwh_x100 == 300


def test_out_of_order_arrival_resorted():
    """Reverse-order input must still produce correct deltas."""
    intervals = derive([_r(60, 1500), _r(0, 1000), _r(30, 1200)])
    assert [c.kwh_x100 for c in intervals] == [200, 300]


def test_duplicate_keeps_larger_value():
    """Same timestamp with different values → keep the higher cumulative."""
    intervals = derive(
        [
            _r(0, 1000),
            _r(30, 1200),
            _r(30, 1250),  # duplicate timestamp with higher value
        ]
    )
    # Delta is 1250 - 1000 = 250 (the larger duplicate won).
    assert intervals[0].kwh_x100 == 250


def test_gap_within_max_produces_single_interval():
    """Gap below threshold → one interval, not estimated."""
    intervals = derive(
        [_r(0, 1000), _r(80, 1400)],  # 80-min gap, threshold 90 → not split
        max_gap_minutes=90,
    )
    assert len(intervals) == 1
    assert intervals[0].is_estimated is False


def test_gap_above_max_splits_into_chunks():
    """Gap above threshold → multiple estimated 30-min chunks."""
    intervals = derive(
        [_r(0, 1000), _r(180, 3000)],  # 3-hour gap → 6 × 30min chunks
        max_gap_minutes=90,
    )
    assert len(intervals) == 6
    assert all(c.is_estimated for c in intervals)
    # Total kWh preserved: 3000 - 1000 = 2000.
    assert sum(c.kwh_x100 for c in intervals) == 2000


def test_rollover_detected():
    """Cumulative wraps from near-max back to small value → delta via wrap."""
    near_max = METER_MAX_X100 - 100
    intervals = derive([_r(0, near_max), _r(30, 200)])
    # Wrap distance = 100 + 200 + 1 = 301.
    assert intervals[0].kwh_x100 == 301


def test_faulty_backward_step_dropped():
    """A small backward step (not consistent with rollover) is dropped."""
    intervals = derive([_r(0, 5000), _r(30, 4900), _r(60, 5100)])
    # Middle step is faulty; only the 5000 → 5100 interval survives (200).
    assert len(intervals) == 1
    assert intervals[0].kwh_x100 == 200


def test_per_meter_independence():
    """Two meters fold independently — readings don't cross-contaminate."""
    intervals = derive(
        [
            _r(0, 1000, "M-A"),
            _r(30, 1200, "M-A"),
            _r(0, 5000, "M-B"),
            _r(30, 5100, "M-B"),
        ]
    )
    by_meter = {c.meter_id: c for c in intervals}
    assert by_meter["M-A"].kwh_x100 == 200
    assert by_meter["M-B"].kwh_x100 == 100


def test_output_sorted_by_meter_then_start():
    """Output is sorted ``(meter_id, start_at)`` for stable diffs."""
    intervals = derive(
        [
            _r(60, 1300, "M-B"),
            _r(30, 1200, "M-A"),
            _r(0, 1000, "M-A"),
            _r(30, 1200, "M-B"),
            _r(0, 1100, "M-B"),
        ]
    )
    keys = [(c.meter_id, c.start_at) for c in intervals]
    assert keys == sorted(keys)


def test_validate_max_gap_minutes():
    with pytest.raises(ValueError):
        derive([], max_gap_minutes=0)
    with pytest.raises(ValueError):
        derive([], max_gap_minutes=-1)


def test_chunk_total_preserves_cumulative_delta():
    """Even after splitting, sum of estimated chunks equals the original delta."""
    intervals = derive(
        [_r(0, 100_000), _r(240, 101_300)],  # 4-hour gap, 1300 kWh×100 delta
        max_gap_minutes=30,
    )
    assert sum(c.kwh_x100 for c in intervals) == 1300
