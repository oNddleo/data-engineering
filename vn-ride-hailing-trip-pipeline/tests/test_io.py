"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from vnride.fraud import find_ghost_rides
from vnride.io_jsonl import (
    dump_frauds,
    dump_settlements,
    dump_trips,
    fare_from_dict,
    fare_to_dict,
    load_frauds,
    load_settlements,
    load_trips,
    settlement_from_dict,
    trip_from_dict,
    trip_to_dict,
)
from vnride.schema import PaymentMethod
from vnride.settlement import aggregate_daily

from ._fixtures import make_cancelled, make_completed, make_fare


def test_fare_roundtrip() -> None:
    f = make_fare(surge_multiplier_bps=14_000)
    assert fare_from_dict(fare_to_dict(f)) == f


def test_trip_completed_roundtrip() -> None:
    t = make_completed()
    assert trip_from_dict(trip_to_dict(t)) == t


def test_trip_cancelled_roundtrip() -> None:
    t = make_cancelled()
    assert trip_from_dict(trip_to_dict(t)) == t


def test_trip_with_corporate_payment_roundtrip() -> None:
    t = make_completed(payment_method=PaymentMethod.CORPORATE)
    assert trip_from_dict(trip_to_dict(t)) == t


def test_dump_load_many() -> None:
    trips = [make_completed(trip_id=f"T-{i}") for i in range(5)]
    assert load_trips(dump_trips(trips)) == trips


def test_dump_skips_blank_lines() -> None:
    trips = [make_completed()]
    text = "\n\n" + dump_trips(trips) + "\n\n"
    assert load_trips(text) == trips


def test_settlement_roundtrip() -> None:
    trips = [make_completed(trip_id=f"T-{i}") for i in range(3)]
    settlements = aggregate_daily(trips)
    out = load_settlements(dump_settlements(settlements))
    assert out == settlements


def test_settlement_negative_payable_roundtrip() -> None:
    from vnride.schema import DriverSettlement

    s = DriverSettlement(
        driver_id="D-1",
        operator="GRAB",
        date="2026-05-18",
        n_completed_trips=5,
        n_cancelled_trips=1,
        gross_revenue_vnd=500_000,
        commission_vnd=125_000,
        cash_collected_vnd=500_000,
        net_payable_vnd=-125_000,
    )
    assert settlement_from_dict(dump_settlement_dict(s)) == s


def dump_settlement_dict(s: object) -> dict[str, object]:
    """Helper to extract the codec-dict shape — bridges roundtrip test."""
    from vnride.io_jsonl import settlement_to_dict
    from vnride.schema import DriverSettlement

    assert isinstance(s, DriverSettlement)
    return settlement_to_dict(s)


def test_fraud_roundtrip() -> None:
    t = make_completed(distance_cm=100, duration_seconds=5)
    findings = find_ghost_rides([t])
    out = load_frauds(dump_frauds(findings))
    assert out == findings


def test_load_rejects_non_object() -> None:
    with pytest.raises(TypeError, match="object"):
        load_trips("[1, 2, 3]\n")


def test_load_rejects_wrong_type() -> None:
    bad = '{"trip_id": 1, "operator": "GRAB"}\n'
    with pytest.raises(TypeError):
        load_trips(bad)
