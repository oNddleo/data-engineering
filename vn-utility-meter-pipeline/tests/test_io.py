"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from evn.aggregator import aggregate_annual
from evn.anomaly import find_zero_usage
from evn.billing import compute_bill
from evn.io_jsonl import (
    anomaly_from_dict,
    anomaly_to_dict,
    bill_from_dict,
    bill_to_dict,
    dump_anomalies,
    dump_bills,
    dump_readings,
    dump_summaries,
    load_anomalies,
    load_bills,
    load_readings,
    load_summaries,
    reading_from_dict,
    reading_to_dict,
)
from evn.schema import AnomalyFinding, AnomalyKind, CustomerCategory

from ._fixtures import make_reading


def test_reading_roundtrip() -> None:
    r = make_reading()
    assert reading_from_dict(reading_to_dict(r)) == r


def test_reading_dump_load_many() -> None:
    readings = [make_reading(customer_code=f"PA{i:011d}") for i in range(5)]
    out = load_readings(dump_readings(readings))
    assert out == readings


def test_bill_household_roundtrip() -> None:
    bill = compute_bill(make_reading(kwh_used=150))
    out = bill_from_dict(bill_to_dict(bill))
    assert out == bill


def test_bill_flat_roundtrip() -> None:
    bill = compute_bill(
        make_reading(
            category=CustomerCategory.BUSINESS,
            kwh_used=1_000,
        )
    )
    out = bill_from_dict(bill_to_dict(bill))
    assert out == bill


def test_summary_roundtrip() -> None:
    bills = [compute_bill(make_reading(kwh_used=100 + 10 * i)) for i in range(3)]
    summaries = aggregate_annual(bills)
    out = load_summaries(dump_summaries(summaries))
    assert out == summaries


def test_anomaly_roundtrip() -> None:
    f = AnomalyFinding(
        kind=AnomalyKind.ZERO_USAGE,
        customer_code="PA00000000001",
        category=CustomerCategory.HOUSEHOLD,
        detail="test detail",
        metric=400,
    )
    assert anomaly_from_dict(anomaly_to_dict(f)) == f


def test_anomaly_dump_load_via_finder() -> None:
    """End-to-end: detect → dump → load."""
    from datetime import date

    readings = [
        make_reading(
            customer_code="PA00000000001",
            period_start=date(2025, m + 1, 1),
            period_end=date(2025, m + 1, 28),
            kwh_used=kwh,
        )
        for m, kwh in enumerate([100, 110, 120, 105, 0])
    ]
    findings = find_zero_usage(readings)
    assert len(findings) == 1
    out = load_anomalies(dump_anomalies(findings))
    assert out == findings


def test_dump_skips_blank_lines() -> None:
    readings = [make_reading()]
    text = "\n\n" + dump_readings(readings) + "\n\n"
    assert load_readings(text) == readings


def test_load_rejects_non_object() -> None:
    with pytest.raises(TypeError, match="object"):
        load_readings("[1, 2, 3]\n")


def test_load_rejects_wrong_type() -> None:
    bad = '{"customer_code": 123, "category": "HOUSEHOLD"}\n'
    with pytest.raises(TypeError):
        load_readings(bad)


def test_dump_bills_dump_anomalies_dump_summaries() -> None:
    """Bulk dump helpers should round-trip empty lists too."""
    assert load_bills(dump_bills([])) == []
    assert load_anomalies(dump_anomalies([])) == []
    assert load_summaries(dump_summaries([])) == []
