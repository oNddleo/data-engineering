"""Per-courier on-time SLA computation — Tết-aware.

A parcel is considered **on time** when:

```
delivered_at - picked_up_at <= sla_hours
```

where ``sla_hours`` comes from the courier's published target,
choosing same-city vs inter-city based on the first two characters
of the origin and destination hub codes.

**Tết adjustment**: during the 5-day Tết block + the surrounding
weekend, hub throughput drops to near-zero. Including those hours
in the SLA window would unfairly penalize couriers for closures
they don't control. ``tet_aware=True`` subtracts the Tết block from
the elapsed transit time before comparing to the SLA. The block
dates are hard-coded from the published TCTK calendar (2024-2027).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

from vnpost.couriers import sla_hours
from vnpost.schema import CourierCode, CourierSLA, ParcelStatus

if TYPE_CHECKING:
    from vnpost.schema import Parcel


# Tết blocks (Mùng 1 + the surrounding 5 days = giao thừa through
# Mùng 4). Hard-coded from the TCTK Gregorian calendar. Extend as needed.
_TET_BLOCKS: tuple[tuple[date, date], ...] = (
    (date(2024, 2, 9), date(2024, 2, 14)),  # Tết 2024
    (date(2025, 1, 28), date(2025, 2, 2)),  # Tết 2025
    (date(2026, 2, 16), date(2026, 2, 21)),  # Tết 2026
    (date(2027, 2, 5), date(2027, 2, 10)),  # Tết 2027
)


def hours_in_tet_block(start: datetime, end: datetime) -> int:
    """Hours in the interval ``[start, end]`` that fall in a Tết block."""
    if end <= start:
        return 0
    total_h = 0
    for block_start, block_end in _TET_BLOCKS:
        # Convert block_start/end dates to datetimes in start's TZ.
        bs = datetime(block_start.year, block_start.month, block_start.day, tzinfo=start.tzinfo)
        be = datetime(
            block_end.year, block_end.month, block_end.day, tzinfo=start.tzinfo
        ) + timedelta(days=1)
        overlap_start = max(start, bs)
        overlap_end = min(end, be)
        if overlap_end > overlap_start:
            total_h += int((overlap_end - overlap_start).total_seconds() // 3600)
    return total_h


def compute_sla(
    parcels: list[Parcel],
    *,
    tet_aware: bool = True,
) -> list[CourierSLA]:
    """Group parcels by courier, compute on-time rate + transit percentiles."""
    by_courier: dict[CourierCode, list[Parcel]] = defaultdict(list)
    for p in parcels:
        by_courier[p.courier].append(p)

    out: list[CourierSLA] = []
    for courier, group in by_courier.items():
        delivered = [p for p in group if p.status is ParcelStatus.DELIVERED]
        n_on_time = 0
        transit_hours_list: list[int] = []
        for p in delivered:
            if p.picked_up_at is None or p.delivered_at is None:
                continue
            elapsed = int(
                (p.delivered_at - p.picked_up_at).total_seconds() // 3600,
            )
            if tet_aware:
                elapsed -= hours_in_tet_block(p.picked_up_at, p.delivered_at)
                elapsed = max(0, elapsed)
            transit_hours_list.append(elapsed)
            origin_city = p.origin_hub.split("-")[0] if p.origin_hub else ""
            dest_city = p.dest_hub.split("-")[0] if p.dest_hub else origin_city
            target = sla_hours(
                courier,
                origin_city=origin_city,
                dest_city=dest_city,
            )
            if elapsed <= target:
                n_on_time += 1
        on_time_rate = n_on_time / len(delivered) * 100 if delivered else 0.0
        sorted_transit = sorted(transit_hours_list)
        median_t = sorted_transit[len(sorted_transit) // 2] if sorted_transit else 0
        p95_t = (
            sorted_transit[int(round(0.95 * (len(sorted_transit) - 1)))] if sorted_transit else 0
        )
        out.append(
            CourierSLA(
                courier=courier,
                n_parcels=len(group),
                n_delivered=len(delivered),
                n_on_time=n_on_time,
                median_transit_hours=median_t,
                p95_transit_hours=p95_t,
                on_time_rate_pct=round(on_time_rate, 1),
            )
        )
    out.sort(key=lambda s: s.courier.value)
    return out


__all__ = ["compute_sla", "hours_in_tet_block"]
