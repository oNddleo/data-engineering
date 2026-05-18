"""Two classic ride-share fraud patterns.

**Cancellation abuse** — a driver "accepts" a dispatch to claim
position in the queue, then cancels seconds later when a better
offer arrives. The tell: a driver with high cancel-rate (cancels /
accepts) AND short median accept-to-cancel lag.

**Phantom trips** — a driver completes a "trip" with zero distance
or in implausibly short time (e.g. 100m in 5 seconds). Used to
inflate trip-count incentives. The tell: an unusually short
distance-or-duration on a completed DROPOFF.

Both are pure functions over (stitched trips). No clock dependencies,
no I/O — deterministic and easy to test.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from vntrip.schema import CancelBy

if TYPE_CHECKING:
    from vntrip.schema import Trip


class FraudKind(str, Enum):
    """The two fraud signal types we surface."""

    CANCEL_ABUSE = "CANCEL_ABUSE"
    PHANTOM_TRIP = "PHANTOM_TRIP"


@dataclass(frozen=True, slots=True)
class FraudFinding:
    """One ops-actionable fraud signal — same shape across both kinds."""

    kind: FraudKind
    subject_id: str  # driver_id for both kinds
    detail: str
    metric: int  # context-dependent (rate%×100 for CANCEL_ABUSE, count for PHANTOM_TRIP)
    trips_affected: int


def find_cancel_abuse(
    trips: list[Trip],
    *,
    min_accepts: int = 10,
    max_cancel_rate_pct: int = 30,
    max_accept_to_cancel_seconds: int = 30,
) -> list[FraudFinding]:
    """Surface drivers with high accept-then-cancel rate at short lag.

    A driver is flagged when, of trips they accepted:

    1. They cancelled ≥ ``max_cancel_rate_pct`` per cent of them, and
    2. Of those cancellations, the median accept → cancel lag is
       ≤ ``max_accept_to_cancel_seconds`` (a real "I want to cancel"
       takes longer to think about).

    Drivers with fewer than ``min_accepts`` are skipped (too small).
    """
    if min_accepts < 1:
        raise ValueError("min_accepts must be >= 1")
    if not 0 <= max_cancel_rate_pct <= 100:
        raise ValueError("max_cancel_rate_pct must be in [0, 100]")
    if max_accept_to_cancel_seconds <= 0:
        raise ValueError("max_accept_to_cancel_seconds must be > 0")

    accepts_by_driver: dict[str, list[Trip]] = defaultdict(list)
    for t in trips:
        if t.accepted_at is None or not t.driver_id:
            continue
        accepts_by_driver[t.driver_id].append(t)

    out: list[FraudFinding] = []
    for driver_id, driver_trips in accepts_by_driver.items():
        if len(driver_trips) < min_accepts:
            continue
        driver_cancels = [
            t for t in driver_trips if t.cancel_by is CancelBy.DRIVER and t.cancelled_at is not None
        ]
        cancel_rate = len(driver_cancels) / len(driver_trips) * 100
        if cancel_rate < max_cancel_rate_pct:
            continue
        if not driver_cancels:
            continue
        lags = [
            int((t.cancelled_at - t.accepted_at).total_seconds())
            for t in driver_cancels
            if t.accepted_at is not None and t.cancelled_at is not None
        ]
        median_lag = sorted(lags)[len(lags) // 2]
        if median_lag > max_accept_to_cancel_seconds:
            continue
        out.append(
            FraudFinding(
                kind=FraudKind.CANCEL_ABUSE,
                subject_id=driver_id,
                detail=(
                    f"cancelled {len(driver_cancels)}/{len(driver_trips)} accepts "
                    f"({cancel_rate:.1f}%), median lag {median_lag}s"
                ),
                metric=int(cancel_rate * 100),
                trips_affected=len(driver_cancels),
            )
        )
    out.sort(key=lambda f: (-f.metric, f.subject_id))
    return out


def find_phantom_trips(
    trips: list[Trip],
    *,
    min_distance_m: int = 200,
    min_ride_seconds: int = 30,
) -> list[FraudFinding]:
    """Surface drivers with completed trips of suspicious distance
    or duration.

    A "phantom" completion is a DROPOFF where:

    * ``distance_m < min_distance_m`` (default 200m — shorter than
      walking distance), OR
    * ``ride_seconds < min_ride_seconds`` (default 30s — driver
      didn't go anywhere).

    Per driver, if there's at least one phantom trip we surface them
    with the affected count and the offending driver_id.
    """
    if min_distance_m < 1:
        raise ValueError("min_distance_m must be >= 1")
    if min_ride_seconds < 1:
        raise ValueError("min_ride_seconds must be >= 1")

    by_driver: dict[str, list[Trip]] = defaultdict(list)
    for t in trips:
        if not t.is_completed:
            continue
        if not t.driver_id:
            continue
        if t.distance_m < min_distance_m or t.ride_seconds < min_ride_seconds:
            by_driver[t.driver_id].append(t)
    out: list[FraudFinding] = []
    for driver_id, phantoms in by_driver.items():
        out.append(
            FraudFinding(
                kind=FraudKind.PHANTOM_TRIP,
                subject_id=driver_id,
                detail=(
                    f"{len(phantoms)} completions with distance<{min_distance_m}m "
                    f"or duration<{min_ride_seconds}s"
                ),
                metric=len(phantoms),
                trips_affected=len(phantoms),
            )
        )
    out.sort(key=lambda f: (-f.trips_affected, f.subject_id))
    return out


__all__ = [
    "FraudFinding",
    "FraudKind",
    "find_cancel_abuse",
    "find_phantom_trips",
]
