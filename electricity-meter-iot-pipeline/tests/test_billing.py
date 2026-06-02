"""Billing engine — pro-rata, multi-meter, month-boundary handling."""

from __future__ import annotations

from datetime import timedelta

import pytest

from evnmeter.billing import bill_meters

from ._fixtures import DEFAULT_TS, make_interval


def test_single_meter_basic_bill():
    # 30 kWh = 3000 in kWh×100 units; lands entirely in tier 1.
    intervals = [
        make_interval(kwh_x100=3000, start_at=DEFAULT_TS, end_at=DEFAULT_TS + timedelta(hours=24))
    ]
    bills = bill_meters(
        intervals,
        period_start=DEFAULT_TS,
        period_end=DEFAULT_TS + timedelta(days=30),
    )
    assert len(bills) == 1
    b = bills[0]
    assert b.billed_kwh == 30
    assert b.subtotal_vnd == 30 * 1_806
    assert b.grand_total_vnd == b.subtotal_vnd + b.vat_vnd


def test_multiple_meters_independent_bills():
    """Two meters → two independent bills."""
    intervals = [
        make_interval(meter_id="M-A", kwh_x100=2000),
        make_interval(
            meter_id="M-B",
            kwh_x100=4000,
            start_at=DEFAULT_TS + timedelta(hours=1),
            end_at=DEFAULT_TS + timedelta(hours=2),
        ),
    ]
    bills = bill_meters(
        intervals,
        period_start=DEFAULT_TS,
        period_end=DEFAULT_TS + timedelta(days=30),
    )
    by_meter = {b.meter_id: b for b in bills}
    assert by_meter["M-A"].billed_kwh == 20
    assert by_meter["M-B"].billed_kwh == 40


def test_zero_consumption_meter_skipped():
    """A meter with no usage in the window doesn't produce a bill row."""
    intervals = [
        make_interval(kwh_x100=0, start_at=DEFAULT_TS, end_at=DEFAULT_TS + timedelta(hours=1))
    ]
    bills = bill_meters(
        intervals,
        period_start=DEFAULT_TS,
        period_end=DEFAULT_TS + timedelta(days=30),
    )
    assert bills == []


def test_partial_overlap_prorated():
    """Interval straddling month boundary is split proportionally."""
    # 6-hour interval: 3h in month A, 3h in month B.
    intervals = [
        make_interval(
            kwh_x100=600,  # 6 kWh total
            start_at=DEFAULT_TS - timedelta(hours=3),
            end_at=DEFAULT_TS + timedelta(hours=3),
        )
    ]
    bills = bill_meters(
        intervals,
        period_start=DEFAULT_TS,
        period_end=DEFAULT_TS + timedelta(days=30),
    )
    # Only half the interval falls in window → 300 kWh×100 → 3 billable kWh.
    assert bills[0].billed_kwh == 3


def test_outside_window_excluded():
    """An interval entirely before the period is ignored."""
    intervals = [
        make_interval(
            kwh_x100=5000,
            start_at=DEFAULT_TS - timedelta(days=10),
            end_at=DEFAULT_TS - timedelta(days=9),
        )
    ]
    bills = bill_meters(
        intervals,
        period_start=DEFAULT_TS,
        period_end=DEFAULT_TS + timedelta(days=30),
    )
    assert bills == []


def test_estimated_intervals_counted_separately():
    """``n_estimated_intervals`` is recorded for ops audit visibility."""
    intervals = [
        make_interval(kwh_x100=2000, start_at=DEFAULT_TS, end_at=DEFAULT_TS + timedelta(hours=1)),
        make_interval(
            kwh_x100=1000,
            is_estimated=True,
            start_at=DEFAULT_TS + timedelta(hours=1),
            end_at=DEFAULT_TS + timedelta(hours=2),
        ),
        make_interval(
            kwh_x100=1000,
            is_estimated=True,
            start_at=DEFAULT_TS + timedelta(hours=2),
            end_at=DEFAULT_TS + timedelta(hours=3),
        ),
    ]
    bills = bill_meters(
        intervals,
        period_start=DEFAULT_TS,
        period_end=DEFAULT_TS + timedelta(days=30),
    )
    assert bills[0].n_estimated_intervals == 2


def test_validates_naive_period():
    with pytest.raises(ValueError):
        from datetime import datetime

        bill_meters([], period_start=datetime(2026, 5, 1), period_end=DEFAULT_TS)


def test_validates_inverted_period():
    with pytest.raises(ValueError, match="period_start"):
        bill_meters([], period_start=DEFAULT_TS + timedelta(days=30), period_end=DEFAULT_TS)


def test_high_consumption_triggers_top_tier():
    """500 kWh hits all 6 tiers — bill reflects the progressive structure."""
    intervals = [
        make_interval(kwh_x100=50_000, start_at=DEFAULT_TS, end_at=DEFAULT_TS + timedelta(days=10))
    ]
    bills = bill_meters(
        intervals,
        period_start=DEFAULT_TS,
        period_end=DEFAULT_TS + timedelta(days=30),
    )
    assert bills[0].billed_kwh == 500
    # 6 tiers in breakdown.
    assert len(bills[0].breakdown) == 6
    assert bills[0].breakdown[-1].tier == 6
