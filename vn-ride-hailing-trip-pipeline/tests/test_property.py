"""Hypothesis property tests."""

from __future__ import annotations

from datetime import datetime, timedelta

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from vnride.io_jsonl import fare_from_dict, fare_to_dict, trip_from_dict, trip_to_dict
from vnride.operators import all_operators, commission_bps
from vnride.pricing import (
    MAX_SURGE_BPS,
    MIN_SURGE_BPS,
    commission_split,
    quote,
)
from vnride.schema import (
    VN_TZ,
    FareBreakdown,
    PaymentMethod,
    ServiceType,
    Trip,
    TripState,
)
from vnride.settlement import aggregate_daily

_operator_abbrs = tuple(o.abbreviation for o in all_operators())


@st.composite
def fare_strategy(draw: st.DrawFn) -> FareBreakdown:
    return FareBreakdown(
        base_vnd=draw(st.integers(min_value=0, max_value=200_000)),
        distance_vnd=draw(st.integers(min_value=0, max_value=2_000_000)),
        duration_vnd=draw(st.integers(min_value=0, max_value=500_000)),
        booking_vnd=draw(st.integers(min_value=0, max_value=10_000)),
        surge_multiplier_bps=draw(
            st.integers(min_value=MIN_SURGE_BPS, max_value=MAX_SURGE_BPS),
        ),
    )


@st.composite
def completed_trip(draw: st.DrawFn) -> Trip:
    op = draw(st.sampled_from(_operator_abbrs))
    service = draw(st.sampled_from(list(ServiceType)))
    day_offset = draw(st.integers(min_value=0, max_value=29))
    hour = draw(st.integers(min_value=0, max_value=23))
    suffix = draw(st.text(min_size=1, max_size=6, alphabet="0123456789AB"))
    distance = draw(st.integers(min_value=10_000, max_value=10_000_000))
    duration = draw(st.integers(min_value=60, max_value=3600))
    return Trip(
        trip_id=f"T-{suffix}-{day_offset}-{hour}",
        operator=op,
        city="SGN",
        service=service,
        rider_id=f"R-{day_offset}",
        driver_id=f"D-{hour}",
        state=TripState.COMPLETED,
        requested_at=datetime(2026, 5, 1, hour, 0, tzinfo=VN_TZ) + timedelta(days=day_offset),
        completed_at=datetime(2026, 5, 1, hour, 0, tzinfo=VN_TZ)
        + timedelta(days=day_offset, seconds=duration + 180),
        distance_cm=distance,
        duration_seconds=duration,
        fare=draw(fare_strategy()),
        payment_method=draw(st.sampled_from(list(PaymentMethod))),
    )


# ---------- Fare invariants -------------------------------------------------


@given(fare_strategy())
def test_fare_total_consistent(f: FareBreakdown) -> None:
    """total_vnd is the sum of components."""
    assert f.total_vnd == f.base_vnd + f.distance_vnd + f.duration_vnd + f.booking_vnd


@given(fare_strategy())
def test_fare_total_non_negative(f: FareBreakdown) -> None:
    assert f.total_vnd >= 0


# ---------- Pricing properties ---------------------------------------------


@given(
    st.sampled_from(list(ServiceType)),
    st.integers(min_value=0, max_value=10_000_000),
    st.integers(min_value=0, max_value=7200),
)
@settings(max_examples=80)
def test_quote_total_at_least_min_fare(
    service: ServiceType,
    distance_cm: int,
    duration_seconds: int,
) -> None:
    from vnride.pricing import DEFAULT_TARIFFS

    fare = quote(service, distance_cm, duration_seconds)
    assert fare.total_vnd >= DEFAULT_TARIFFS[service].minimum_fare_vnd


@given(
    st.sampled_from(list(ServiceType)),
    st.integers(min_value=10_000, max_value=2_000_000),
    st.integers(min_value=60, max_value=3600),
    st.integers(min_value=MIN_SURGE_BPS, max_value=MAX_SURGE_BPS),
)
@settings(max_examples=80)
def test_quote_surge_monotonic(
    service: ServiceType,
    distance_cm: int,
    duration_seconds: int,
    surge_bps: int,
) -> None:
    """Higher surge → higher or equal total."""
    base = quote(service, distance_cm, duration_seconds, surge_bps=MIN_SURGE_BPS)
    surged = quote(service, distance_cm, duration_seconds, surge_bps=surge_bps)
    assert surged.total_vnd >= base.total_vnd


@given(
    fare_strategy(),
    st.integers(min_value=0, max_value=10_000),
)
@settings(max_examples=60)
def test_commission_split_conserves_total(
    fare: FareBreakdown,
    comm_bps: int,
) -> None:
    """Operator + driver share must always equal fare.total_vnd."""
    op, drv = commission_split(fare, comm_bps)
    assert op + drv == fare.total_vnd
    assert op >= 0 and drv >= 0


@given(st.sampled_from(_operator_abbrs))
def test_commission_bps_in_valid_range(operator: str) -> None:
    for service in ("CAR", "BIKE", "DELIVERY"):
        bps = commission_bps(operator, service)
        assert 0 <= bps <= 10_000


# ---------- Trip JSONL ------------------------------------------------------


@given(completed_trip())
@settings(max_examples=40, suppress_health_check=[HealthCheck.too_slow])
def test_trip_jsonl_roundtrip(t: Trip) -> None:
    assert trip_from_dict(trip_to_dict(t)) == t


@given(fare_strategy())
def test_fare_jsonl_roundtrip(f: FareBreakdown) -> None:
    assert fare_from_dict(fare_to_dict(f)) == f


# ---------- Settlement conservation ----------------------------------------


@given(st.lists(completed_trip(), min_size=1, max_size=15))
@settings(max_examples=20, suppress_health_check=[HealthCheck.too_slow])
def test_settlement_revenue_conservation(trips: list[Trip]) -> None:
    """Sum of per-driver gross revenue must equal sum of trip fares."""
    seen: set[str] = set()
    unique = []
    for t in trips:
        if t.trip_id not in seen:
            seen.add(t.trip_id)
            unique.append(t)
    settlements = aggregate_daily(unique)
    total_settlement = sum(s.gross_revenue_vnd for s in settlements)
    total_trips = sum(t.fare.total_vnd for t in unique if t.fare is not None)
    assert total_settlement == total_trips
