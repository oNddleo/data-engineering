"""Daily per-driver settlement — what the operator pays the driver.

For each ``(driver_id, operator, date)`` group, aggregate the day's
completed and cancelled trips into a single ``DriverSettlement``:

* ``gross_revenue_vnd`` = sum of completed-trip fares (rider-side)
* ``commission_vnd`` = operator's cut (via ``pricing.commission_split``)
* ``cash_collected_vnd`` = sum of fares paid in CASH (driver already
  holds these funds)
* ``net_payable_vnd`` = what the operator owes the driver at day-end
  = driver_net_earnings − cash_collected_vnd

When the net is negative the driver **owes** the operator (typical
on days dominated by cash trips — the operator still has commission
to claim against cash already in the driver's pocket).
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from vnride.operators import commission_bps
from vnride.pricing import commission_split
from vnride.schema import DriverSettlement, PaymentMethod, TripState

if TYPE_CHECKING:
    from vnride.schema import Trip


def aggregate_daily(trips: list[Trip]) -> list[DriverSettlement]:
    """Aggregate trips into per-(driver, operator, date) settlements.

    Output sorted by ``(date, operator, driver_id)``.
    """
    groups: dict[tuple[str, str, str], list[Trip]] = defaultdict(list)
    for t in trips:
        if not t.driver_id:
            continue  # NO_DRIVER trips have no driver to settle
        date = t.requested_at.date().isoformat()
        groups[(t.driver_id, t.operator, date)].append(t)

    out: list[DriverSettlement] = []
    for (driver_id, operator, date), group in groups.items():
        completed = [t for t in group if t.state is TripState.COMPLETED]
        cancelled = [t for t in group if t.state is TripState.CANCELLED]

        gross = 0
        commission_total = 0
        cash_collected = 0
        driver_net_total = 0

        for trip in completed:
            assert trip.fare is not None  # invariant from schema
            gross += trip.fare.total_vnd
            comm_bps = commission_bps(trip.operator, trip.service.value)
            op_take, driver_net = commission_split(trip.fare, comm_bps)
            commission_total += op_take
            driver_net_total += driver_net
            if trip.payment_method is PaymentMethod.CASH:
                cash_collected += trip.fare.total_vnd

        # What the operator owes (or claws back from) the driver.
        net_payable = driver_net_total - cash_collected

        out.append(
            DriverSettlement(
                driver_id=driver_id,
                operator=operator,
                date=date,
                n_completed_trips=len(completed),
                n_cancelled_trips=len(cancelled),
                gross_revenue_vnd=gross,
                commission_vnd=commission_total,
                cash_collected_vnd=cash_collected,
                net_payable_vnd=net_payable,
            )
        )
    out.sort(key=lambda s: (s.date, s.operator, s.driver_id))
    return out


__all__ = ["aggregate_daily"]
