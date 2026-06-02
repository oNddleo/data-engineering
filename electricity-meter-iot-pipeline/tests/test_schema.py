"""Schema invariants."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from evnmeter.schema import METER_MAX_X100, VN_TZ, ConsumptionInterval, MeterKind

from ._fixtures import DEFAULT_TS, make_interval, make_meter, make_reading


def test_vn_tz_is_utc_plus_7():
    offset = VN_TZ.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == 7 * 3600


def test_meter_kind_enum_has_three_values():
    assert {k.value for k in MeterKind} == {"RESI_1P", "RESI_3P", "COMM"}


def test_meter_rejects_empty_id():
    with pytest.raises(ValueError):
        make_meter(meter_id="")


def test_meter_rejects_naive_installed_at():
    with pytest.raises(ValueError):
        make_meter(installed_at=datetime(2024, 1, 1))


def test_meter_rejects_empty_region():
    with pytest.raises(ValueError):
        make_meter(region_code="")


def test_reading_rejects_negative_cumulative():
    with pytest.raises(ValueError):
        make_reading(cumulative_kwh_x100=-1)


def test_reading_rejects_above_max():
    with pytest.raises(ValueError):
        make_reading(cumulative_kwh_x100=METER_MAX_X100 + 1)


def test_reading_rejects_naive_observed_at():
    with pytest.raises(ValueError):
        make_reading(observed_at=datetime(2026, 5, 1))


def test_reading_rejects_unknown_quality():
    with pytest.raises(ValueError):
        make_reading(quality="MAYBE")


def test_reading_max_value_accepted():
    r = make_reading(cumulative_kwh_x100=METER_MAX_X100)
    assert r.cumulative_kwh_x100 == METER_MAX_X100


def test_interval_rejects_zero_duration():
    with pytest.raises(ValueError, match="start_at"):
        ConsumptionInterval(
            meter_id="M",
            start_at=DEFAULT_TS,
            end_at=DEFAULT_TS,  # zero-length
            kwh_x100=10,
            is_estimated=False,
        )


def test_interval_rejects_negative_kwh():
    with pytest.raises(ValueError):
        make_interval(kwh_x100=-1)


def test_interval_rejects_backward():
    with pytest.raises(ValueError):
        ConsumptionInterval(
            meter_id="M",
            start_at=DEFAULT_TS + timedelta(hours=1),
            end_at=DEFAULT_TS,
            kwh_x100=0,
            is_estimated=False,
        )


def test_interval_zero_kwh_legal():
    """A zero-consumption interval is legal (e.g. customer away)."""
    c = make_interval(kwh_x100=0)
    assert c.kwh_x100 == 0
