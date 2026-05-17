"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from evnmeter.billing import MonthlyBill
from evnmeter.io_jsonl import (
    bill_from_dict,
    dump_bills,
    dump_intervals,
    dump_meters,
    dump_readings,
    interval_from_dict,
    load_bills,
    load_intervals,
    load_meters,
    load_readings,
    meter_from_dict,
    reading_from_dict,
)

from ._fixtures import DEFAULT_TS, make_interval, make_meter, make_reading


def test_meter_roundtrip():
    m = make_meter()
    [back] = list(load_meters(dump_meters([m])))
    assert back == m


def test_reading_roundtrip():
    r = make_reading()
    [back] = list(load_readings(dump_readings([r])))
    assert back == r


def test_interval_roundtrip():
    c = make_interval()
    [back] = list(load_intervals(dump_intervals([c])))
    assert back == c


def test_bill_roundtrip():
    b = MonthlyBill(
        meter_id="M-1",
        period_start=DEFAULT_TS,
        period_end=DEFAULT_TS,
        billed_kwh=100,
        breakdown=(),
        subtotal_vnd=180_600,
        vat_vnd=14_448,
        grand_total_vnd=195_048,
        n_estimated_intervals=0,
    )
    [back] = list(load_bills(dump_bills([b])))
    assert back == b


def test_meter_decoder_rejects_unknown_kind():
    bad = {
        "meter_id": "M",
        "customer_id": "C",
        "kind": "QUANTUM",
        "region_code": "HN",
        "installed_at": "2026-05-01T00:00:00+07:00",
    }
    with pytest.raises(ValueError):
        meter_from_dict(bad)


def test_reading_decoder_rejects_bool_for_int():
    bad = {
        "meter_id": "M",
        "cumulative_kwh_x100": True,
        "observed_at": "2026-05-01T00:00:00+07:00",
        "quality": "GOOD",
    }
    with pytest.raises(TypeError, match="cumulative_kwh_x100"):
        reading_from_dict(bad)


def test_interval_decoder_rejects_string_for_bool():
    bad = {
        "meter_id": "M",
        "start_at": "2026-05-01T00:00:00+07:00",
        "end_at": "2026-05-01T00:30:00+07:00",
        "kwh_x100": 50,
        "is_estimated": "true",
    }
    with pytest.raises(TypeError, match="is_estimated"):
        interval_from_dict(bad)


def test_bill_decoder_missing_breakdown():
    bad = {
        "meter_id": "M",
        "period_start": "2026-05-01T00:00:00+07:00",
        "period_end": "2026-06-01T00:00:00+07:00",
        "billed_kwh": 100,
        "subtotal_vnd": 0,
        "vat_vnd": 0,
        "grand_total_vnd": 0,
        "n_estimated_intervals": 0,
    }
    with pytest.raises(KeyError):
        bill_from_dict(bad)


def test_blank_lines_skipped():
    text = dump_readings([make_reading()])
    padded = "\n\n" + text + "\n\n"
    assert len(list(load_readings(padded))) == 1


def test_multi_record_roundtrip():
    readings = [make_reading(cumulative_kwh_x100=100 * i + 100) for i in range(5)]
    assert list(load_readings(dump_readings(readings))) == readings
