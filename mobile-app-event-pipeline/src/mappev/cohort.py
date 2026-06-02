"""Install-cohort retention + LTV.

**Retention**: for each install-day cohort, what fraction of installs
were still active on D1, D7, D30? "Active" = at least one ``OPEN`` /
``IN_APP`` / ``PURCHASE`` event in the 24-hour window centred on that
day.

**LTV**: per cohort, cumulative revenue (from ``PURCHASE`` events)
divided by cohort size, computed at three horizons (D1, D7, D30
post-install).

The functions cohort users by their **install date in VN_TZ**, not
UTC — VN marketplaces report install metrics in local time, and a
UTC-23:30 install attributed to "yesterday" in UTC is "today" in
VN. This matches `seller-performance-data-mart` and other repos in
the catalogue.

D-N horizon definition: an install at 2026-05-01 09:00 VN has a
D7 window of 2026-05-07 09:00 VN — 2026-05-08 09:00 VN. Equivalent
to ``[install_at + 6d, install_at + 7d)`` for D7.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from mappev.schema import VN_TZ, CohortLTV, CohortRetention, EventKind

if TYPE_CHECKING:
    from mappev.schema import Event


_ACTIVE_KINDS = (EventKind.OPEN, EventKind.IN_APP, EventKind.PURCHASE)


def _install_date_key(install_at: datetime) -> str:
    """ISO date of the install in VN_TZ — the cohort key."""
    return install_at.astimezone(VN_TZ).date().isoformat()


def _was_active_on_day(
    install_at: datetime,
    day_offset: int,
    sorted_active_events: list[Event],
) -> bool:
    """``True`` if any active event falls in ``[install + offset_days,
    install + (offset+1)_days)``."""
    start = install_at + timedelta(days=day_offset)
    end = install_at + timedelta(days=day_offset + 1)
    return any(start <= e.occurred_at < end for e in sorted_active_events)


def retention(events: list[Event]) -> list[CohortRetention]:
    """Build a list of CohortRetention per (VN_TZ) install date.

    Output sorted by ``cohort_date`` ascending.
    """
    # Pass 1: identify installs per device.
    install_by_device: dict[str, datetime] = {}
    for e in events:
        if e.kind is EventKind.INSTALL and e.device_id not in install_by_device:
            install_by_device[e.device_id] = e.occurred_at

    # Pass 2: index active events per device (sorted, for sliding-window lookup).
    active_by_device: dict[str, list[Event]] = defaultdict(list)
    for e in events:
        if e.kind in _ACTIVE_KINDS:
            active_by_device[e.device_id].append(e)
    for events_list in active_by_device.values():
        events_list.sort(key=lambda e: e.occurred_at)

    # Bucket devices by install cohort date.
    cohort_devices: dict[str, list[tuple[str, datetime]]] = defaultdict(list)
    for device_id, install_at in install_by_device.items():
        key = _install_date_key(install_at)
        cohort_devices[key].append((device_id, install_at))

    out: list[CohortRetention] = []
    for cohort_date in sorted(cohort_devices):
        devices = cohort_devices[cohort_date]
        d1 = 0
        d7 = 0
        d30 = 0
        for device_id, install_at in devices:
            actives = active_by_device.get(device_id, [])
            if _was_active_on_day(install_at, 1, actives):
                d1 += 1
            if _was_active_on_day(install_at, 7, actives):
                d7 += 1
            if _was_active_on_day(install_at, 30, actives):
                d30 += 1
        out.append(
            CohortRetention(
                cohort_date=cohort_date,
                cohort_size=len(devices),
                d1_active=d1,
                d7_active=d7,
                d30_active=d30,
            )
        )
    return out


def _revenue_in_window(
    install_at: datetime,
    horizon_days: int,
    sorted_purchases: list[Event],
) -> int:
    """Sum revenue in ``[install_at, install_at + horizon_days)``."""
    end = install_at + timedelta(days=horizon_days)
    total = 0
    for e in sorted_purchases:
        if e.occurred_at < install_at:
            continue
        if e.occurred_at >= end:
            break
        total += e.revenue_vnd
    return total


def ltv(events: list[Event]) -> list[CohortLTV]:
    """Cumulative LTV per install cohort at D1 / D7 / D30 horizons."""
    install_by_device: dict[str, datetime] = {}
    for e in events:
        if e.kind is EventKind.INSTALL and e.device_id not in install_by_device:
            install_by_device[e.device_id] = e.occurred_at

    purchases_by_device: dict[str, list[Event]] = defaultdict(list)
    for e in events:
        if e.kind is EventKind.PURCHASE:
            purchases_by_device[e.device_id].append(e)
    for pl in purchases_by_device.values():
        pl.sort(key=lambda e: e.occurred_at)

    cohort_devices: dict[str, list[tuple[str, datetime]]] = defaultdict(list)
    for device_id, install_at in install_by_device.items():
        key = _install_date_key(install_at)
        cohort_devices[key].append((device_id, install_at))

    out: list[CohortLTV] = []
    for cohort_date in sorted(cohort_devices):
        devices = cohort_devices[cohort_date]
        rev_1 = rev_7 = rev_30 = 0
        for device_id, install_at in devices:
            purchases = purchases_by_device.get(device_id, [])
            rev_1 += _revenue_in_window(install_at, 1, purchases)
            rev_7 += _revenue_in_window(install_at, 7, purchases)
            rev_30 += _revenue_in_window(install_at, 30, purchases)
        out.append(
            CohortLTV(
                cohort_date=cohort_date,
                cohort_size=len(devices),
                revenue_d1_vnd=rev_1,
                revenue_d7_vnd=rev_7,
                revenue_d30_vnd=rev_30,
            )
        )
    return out


__all__ = ["ltv", "retention"]
