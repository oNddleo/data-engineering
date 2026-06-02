"""Bill computation — apply tariff to a meter reading.

For HOUSEHOLD readings, traverse the tier list and slice the
consumption into per-tier amounts (the "bậc thang" calculation that
appears on every VN household bill).

For flat-category readings (BUSINESS / ADMIN_PUBLIC / PRODUCTION /
AGRICULTURE), apply a single rate to the whole consumption.

In both paths we add 10% VAT per Decree 209/2013/NĐ-CP.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from evn.schema import (
    VAT_BPS,
    CustomerCategory,
    ElectricityBill,
    TierUsage,
)
from evn.tariff import DEFAULT_SCHEDULE, HouseholdTariff

if TYPE_CHECKING:
    from evn.schema import MeterReading
    from evn.tariff import TariffSchedule


def compute_bill(
    reading: MeterReading,
    *,
    schedule: TariffSchedule | None = None,
) -> ElectricityBill:
    """Apply ``schedule`` (default: current EVN schedule) to ``reading``."""
    sched = schedule if schedule is not None else DEFAULT_SCHEDULE

    if reading.category is CustomerCategory.HOUSEHOLD:
        tier_breakdown = _slice_household(reading.kwh_used, sched.household)
        pre_vat = sum(t.amount_vnd for t in tier_breakdown)
        # Defensive: collapse a zero-kwh household bill to an empty breakdown.
        if reading.kwh_used == 0:
            tier_breakdown = ()
    else:
        flat = sched.flat_for(reading.category)
        pre_vat = reading.kwh_used * flat.vnd_per_kwh
        tier_breakdown = ()

    vat = (pre_vat * VAT_BPS + 9_999) // 10_000  # ceil-style integer math

    return ElectricityBill(
        customer_code=reading.customer_code,
        category=reading.category,
        period_start=reading.period_start,
        period_end=reading.period_end,
        kwh_used=reading.kwh_used,
        pre_vat_amount_vnd=pre_vat,
        vat_amount_vnd=vat,
        tier_breakdown=tier_breakdown,
    )


def _slice_household(
    kwh: int,
    tariff: HouseholdTariff,
) -> tuple[TierUsage, ...]:
    """Slice ``kwh`` into per-tier usage rows."""
    if kwh == 0:
        return ()
    rows: list[TierUsage] = []
    consumed_so_far = 0
    for i, tier in enumerate(tariff.tiers):
        if consumed_so_far >= kwh:
            break
        # How much room is left in this tier?
        if tier.upper_bound_kwh is None:
            room = kwh - consumed_so_far
        else:
            room = tier.upper_bound_kwh - consumed_so_far
            if room <= 0:
                continue
        take = min(room, kwh - consumed_so_far)
        if take <= 0:
            continue
        rows.append(
            TierUsage(
                tier_index=i + 1,  # 1-based labelling
                kwh=take,
                rate_vnd_per_kwh=tier.vnd_per_kwh,
                amount_vnd=take * tier.vnd_per_kwh,
            )
        )
        consumed_so_far += take
    return tuple(rows)


__all__ = ["compute_bill"]
