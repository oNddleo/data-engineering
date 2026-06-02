"""Schema validation: FareBreakdown, Trip, DriverSettlement."""

from __future__ import annotations

from datetime import datetime

import pytest

from vnride.schema import (
    VN_TZ,
    DriverSettlement,
    PaymentMethod,
    ServiceType,
    Trip,
    TripState,
)

from ._fixtures import make_cancelled, make_completed, make_fare

# ---------- FareBreakdown ---------------------------------------------------


def test_fare_total_sums_components() -> None:
    f = make_fare()
    assert f.total_vnd == 15_000 + 60_000 + 6_000 + 3_000


def test_fare_surge_multiplier_float() -> None:
    f = make_fare(surge_multiplier_bps=15_000)
    assert f.surge_multiplier == 1.5


def test_fare_rejects_negative_base() -> None:
    with pytest.raises(ValueError, match="base_vnd"):
        make_fare(base_vnd=-1)


def test_fare_rejects_negative_distance_vnd() -> None:
    with pytest.raises(ValueError, match="distance_vnd"):
        make_fare(distance_vnd=-100)


def test_fare_rejects_surge_below_one() -> None:
    """surge_multiplier_bps < 10_000 (sub-1.0×) is not allowed."""
    with pytest.raises(ValueError, match="surge_multiplier_bps"):
        make_fare(surge_multiplier_bps=8_000)


# ---------- Trip ------------------------------------------------------------


def test_trip_completed_basic() -> None:
    t = make_completed()
    assert t.state is TripState.COMPLETED
    assert t.distance_km == 5.0
    assert t.duration_minutes == 15.0


def test_trip_rejects_empty_id() -> None:
    with pytest.raises(ValueError, match="trip_id"):
        make_completed(trip_id="")


def test_trip_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        make_completed(requested_at=datetime(2026, 5, 18, 9, 0))


def test_trip_rejects_negative_distance() -> None:
    with pytest.raises(ValueError, match="distance_cm"):
        make_completed(distance_cm=-1)


def test_trip_completed_requires_fare() -> None:
    with pytest.raises(ValueError, match="COMPLETED trip must have a fare"):
        make_completed(fare=None)


def test_trip_completed_requires_driver_id() -> None:
    with pytest.raises(ValueError, match="COMPLETED trip must have a driver_id"):
        make_completed(driver_id="")


def test_trip_cancelled_must_not_have_fare() -> None:
    with pytest.raises(ValueError, match="must not have a fare"):
        make_cancelled(fare=make_fare())


def test_trip_cancelled_requires_cancelled_by() -> None:
    with pytest.raises(ValueError, match="cancelled_by"):
        make_cancelled(cancelled_by=None)


def test_trip_kinds_complete() -> None:
    assert {s.value for s in ServiceType} == {"CAR", "BIKE", "DELIVERY"}


def test_trip_states_complete() -> None:
    assert {s.value for s in TripState} == {
        "REQUESTED",
        "ASSIGNED",
        "ARRIVING",
        "PICKED_UP",
        "COMPLETED",
        "CANCELLED",
        "NO_DRIVER",
    }


def test_payment_methods_complete() -> None:
    assert {p.value for p in PaymentMethod} == {
        "CASH",
        "EWALLET",
        "BANK_CARD",
        "CORPORATE",
        "VOUCHER",
    }


def test_trip_non_terminal_must_not_have_fare() -> None:
    """A REQUESTED / ASSIGNED trip must not carry a fare yet."""
    with pytest.raises(ValueError, match="non-terminal trip"):
        Trip(
            trip_id="T-1",
            operator="GRAB",
            city="SGN",
            service=ServiceType.CAR,
            rider_id="R-1",
            driver_id="D-1",
            state=TripState.ASSIGNED,
            requested_at=datetime(2026, 5, 18, 10, 0, tzinfo=VN_TZ),
            fare=make_fare(),
        )


# ---------- DriverSettlement ------------------------------------------------


def _make_settlement(**overrides: object) -> DriverSettlement:
    defaults = {
        "driver_id": "D-1",
        "operator": "GRAB",
        "date": "2026-05-18",
        "n_completed_trips": 10,
        "n_cancelled_trips": 2,
        "gross_revenue_vnd": 1_000_000,
        "commission_vnd": 200_000,
        "cash_collected_vnd": 400_000,
        "net_payable_vnd": 400_000,
    }
    defaults.update(overrides)
    return DriverSettlement(**defaults)  # type: ignore[arg-type]


def test_settlement_cancellation_rate() -> None:
    s = _make_settlement(n_completed_trips=8, n_cancelled_trips=2)
    assert s.cancellation_rate == 0.2


def test_settlement_zero_trips_rate_is_zero() -> None:
    s = _make_settlement(n_completed_trips=0, n_cancelled_trips=0)
    assert s.cancellation_rate == 0.0


def test_settlement_negative_payable_allowed() -> None:
    """When driver collected more cash than they earned, payable is negative."""
    s = _make_settlement(
        cash_collected_vnd=900_000,
        net_payable_vnd=-100_000,
    )
    assert s.net_payable_vnd == -100_000


def test_settlement_rejects_negative_count() -> None:
    with pytest.raises(ValueError, match="n_completed_trips"):
        _make_settlement(n_completed_trips=-1)


def test_settlement_rejects_negative_gross() -> None:
    with pytest.raises(ValueError, match="gross_revenue_vnd"):
        _make_settlement(gross_revenue_vnd=-1)
