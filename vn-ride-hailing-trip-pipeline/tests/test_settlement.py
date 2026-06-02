"""Daily driver settlement aggregation."""

from __future__ import annotations

from datetime import datetime

from vnride.schema import VN_TZ, PaymentMethod, ServiceType, TripState
from vnride.settlement import aggregate_daily

from ._fixtures import make_cancelled, make_completed, make_fare


def test_aggregate_groups_per_driver_per_day() -> None:
    trips = [make_completed(trip_id=f"T-{i}") for i in range(3)]
    settlements = aggregate_daily(trips)
    assert len(settlements) == 1
    s = settlements[0]
    assert s.n_completed_trips == 3
    assert s.n_cancelled_trips == 0


def test_aggregate_splits_by_day() -> None:
    t1 = make_completed(
        trip_id="T-1",
        requested_at=datetime(2026, 5, 18, 10, 0, tzinfo=VN_TZ),
    )
    t2 = make_completed(
        trip_id="T-2",
        requested_at=datetime(2026, 5, 19, 10, 0, tzinfo=VN_TZ),
    )
    settlements = aggregate_daily([t1, t2])
    assert len(settlements) == 2
    assert {s.date for s in settlements} == {"2026-05-18", "2026-05-19"}


def test_aggregate_splits_by_driver() -> None:
    t1 = make_completed(trip_id="T-1", driver_id="D-1")
    t2 = make_completed(trip_id="T-2", driver_id="D-2")
    settlements = aggregate_daily([t1, t2])
    assert len(settlements) == 2


def test_aggregate_counts_cancelled() -> None:
    trips = [
        make_completed(trip_id="T-A"),
        make_cancelled(trip_id="T-C", driver_id="D-0001"),
    ]
    s = aggregate_daily(trips)[0]
    assert s.n_completed_trips == 1
    assert s.n_cancelled_trips == 1


def test_aggregate_revenue_sums_fares() -> None:
    fare = make_fare()  # total 84_000
    trips = [make_completed(trip_id=f"T-{i}", fare=fare) for i in range(3)]
    s = aggregate_daily(trips)[0]
    assert s.gross_revenue_vnd == 3 * fare.total_vnd


def test_aggregate_cash_collected() -> None:
    """Cash trips contribute to cash_collected; e-wallet trips do not."""
    trips = [
        make_completed(
            trip_id="T-1",
            payment_method=PaymentMethod.CASH,
        ),
        make_completed(
            trip_id="T-2",
            payment_method=PaymentMethod.EWALLET,
        ),
    ]
    s = aggregate_daily(trips)[0]
    fare = make_fare()
    assert s.cash_collected_vnd == fare.total_vnd  # only the CASH trip


def test_aggregate_skips_no_driver() -> None:
    """NO_DRIVER trips never settle (no driver to pay)."""
    from vnride.schema import CancelledBy, Trip

    no_driver = Trip(
        trip_id="T-ND",
        operator="GRAB",
        city="SGN",
        service=ServiceType.CAR,
        rider_id="R-1",
        driver_id="",
        state=TripState.NO_DRIVER,
        requested_at=datetime(2026, 5, 18, 10, 0, tzinfo=VN_TZ),
        completed_at=datetime(2026, 5, 18, 10, 3, tzinfo=VN_TZ),
        cancelled_by=CancelledBy.SYSTEM,
    )
    settlements = aggregate_daily([no_driver])
    assert settlements == []


def test_aggregate_sorted_by_date_op_driver() -> None:
    trips = [
        make_completed(trip_id="T-1", driver_id="D-2", operator="GRAB"),
        make_completed(trip_id="T-2", driver_id="D-1", operator="GRAB"),
        make_completed(trip_id="T-3", driver_id="D-1", operator="BE"),
    ]
    settlements = aggregate_daily(trips)
    # date is the same → sort by (operator, driver_id)
    assert [(s.operator, s.driver_id) for s in settlements] == [
        ("BE", "D-1"),
        ("GRAB", "D-1"),
        ("GRAB", "D-2"),
    ]


def test_aggregate_commission_taken() -> None:
    """Grab CAR commission is 25% → driver keeps 75% of ride revenue."""
    trip = make_completed()
    s = aggregate_daily([trip])[0]
    # Ride revenue (fare - booking) = 81_000. Operator takes 25% + booking = 23250.
    expected_commission = ((81_000 * 2_500 + 9_999) // 10_000) + 3_000
    assert s.commission_vnd == expected_commission


def test_aggregate_empty() -> None:
    assert aggregate_daily([]) == []
