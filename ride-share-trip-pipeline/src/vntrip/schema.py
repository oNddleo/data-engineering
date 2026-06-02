"""Ride-share trip event schema.

Models a Grab/Gojek/Be-style ride-hailing pipeline. The event stream
is the canonical input; trip stitching, fare calculation, ETA accuracy,
surge-window detection, driver utilization, and cancellation-abuse
detection all derive from it.

The trip-event state machine has six terminal/intermediate states:

```
                       (driver cancels)
                       ┌──────────────────────┐
                       │                      ↓
REQUEST ── ACCEPT ── PICKUP ── DROPOFF       CANCELLED
   │          │                              ↑
   │          └──────────────────────────────┤  (rider/driver cancels after accept)
   │                                         │
   └──────── EXPIRED  (no driver in 5min) ───┘
```

Money is integer VND throughout. Timestamps are tz-aware in VN_TZ.
Districts are encoded as ``"HCM:Q1"`` (Quận 1, HCMC), ``"HN:HK"``
(Hoàn Kiếm, Hà Nội), etc — see ``vntrip.districts``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))


class TripEventKind(str, Enum):
    """Seven event kinds covering the full trip state machine."""

    REQUEST = "REQUEST"  # rider opens app, requests a ride
    ACCEPT = "ACCEPT"  # driver accepts the dispatch
    PICKUP = "PICKUP"  # driver arrives + rider boards
    DROPOFF = "DROPOFF"  # rider reaches destination
    CANCEL = "CANCEL"  # cancellation by rider or driver
    EXPIRE = "EXPIRE"  # no driver accepted in dispatch-window
    SURGE_UPDATE = "SURGE_UPDATE"  # platform-side surge multiplier change


class CancelBy(str, Enum):
    """Which party cancelled."""

    RIDER = "RIDER"
    DRIVER = "DRIVER"
    SYSTEM = "SYSTEM"  # auto-cancel after timeout


class VehicleClass(str, Enum):
    """Vehicle class — affects base fare + per-km rate."""

    MOTORBIKE = "MOTORBIKE"  # GrabBike / GojekBike — most common in VN
    CAR_4 = "CAR_4"  # GrabCar / GojekCar 4-seat
    CAR_7 = "CAR_7"  # 7-seat MPV
    DELIVERY = "DELIVERY"  # GrabExpress / GojekSend


@dataclass(frozen=True, slots=True)
class TripEvent:
    """One event line in the input stream.

    ``trip_id`` is the cross-event join key. ``driver_id`` is empty
    for ``REQUEST``/``EXPIRE`` (no driver assigned yet) and for
    ``SURGE_UPDATE`` (platform-wide event). For all post-ACCEPT events
    the driver is set.

    Position fields (``district``, ``lat_x10000``, ``lon_x10000``)
    are present on ``REQUEST``/``PICKUP``/``DROPOFF`` to track origin
    and destination; integer-scaled by 1e4 to avoid float drift
    (HCM Q1 ≈ ``106.7°E`` → ``1067000``).
    """

    event_id: str
    trip_id: str
    rider_id: str
    driver_id: str  # "" for REQUEST/EXPIRE/SURGE_UPDATE
    kind: TripEventKind
    occurred_at: datetime
    district: str  # e.g. "HCM:Q1", "HN:HK", "" for SURGE_UPDATE
    lat_x10000: int = 0  # latitude × 10000 (truncated)
    lon_x10000: int = 0  # longitude × 10000
    vehicle_class: VehicleClass = VehicleClass.MOTORBIKE
    distance_m: int = 0  # planned route distance, set on REQUEST + DROPOFF
    fare_vnd: int = 0  # only set on DROPOFF (final fare)
    surge_bps: int = (
        10_000  # 10_000 bps = 1.00× (no surge); only meaningful on SURGE_UPDATE / DROPOFF
    )
    cancel_by: CancelBy | None = None  # only set on CANCEL

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id must be non-empty")
        if not self.trip_id:
            raise ValueError("trip_id must be non-empty")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        if self.fare_vnd < 0:
            raise ValueError(f"fare_vnd must be >= 0, got {self.fare_vnd}")
        if self.distance_m < 0:
            raise ValueError(f"distance_m must be >= 0, got {self.distance_m}")
        if self.surge_bps < 10_000:
            raise ValueError(
                f"surge_bps must be >= 10000 (no negative surge), got {self.surge_bps}"
            )
        # State-specific invariants.
        if self.kind is TripEventKind.CANCEL and self.cancel_by is None:
            raise ValueError("CANCEL events must set cancel_by")
        if self.kind is not TripEventKind.CANCEL and self.cancel_by is not None:
            raise ValueError(f"cancel_by must be None for {self.kind.value} events")
        if self.kind is TripEventKind.DROPOFF and self.fare_vnd == 0:
            raise ValueError("DROPOFF must have fare_vnd > 0")
        if self.kind is not TripEventKind.DROPOFF and self.fare_vnd > 0:
            raise ValueError(
                f"fare_vnd must be 0 for {self.kind.value} events, got {self.fare_vnd}"
            )
        # Driver presence rules.
        driver_required = self.kind in (
            TripEventKind.ACCEPT,
            TripEventKind.PICKUP,
            TripEventKind.DROPOFF,
        )
        if driver_required and not self.driver_id:
            raise ValueError(f"driver_id must be set on {self.kind.value} events")
        # SURGE_UPDATE doesn't have a trip_id in real systems but we
        # still attach one for stream-keying; rider_id may be empty.


@dataclass(frozen=True, slots=True)
class FareBreakdown:
    """Fare decomposition: base + distance + time + surge."""

    trip_id: str
    base_fare_vnd: int
    distance_fare_vnd: int
    time_fare_vnd: int
    surge_multiplier_bps: int  # 10_000 = 1.0x
    pre_surge_subtotal_vnd: int
    total_fare_vnd: int

    def __post_init__(self) -> None:
        if self.base_fare_vnd < 0:
            raise ValueError("base_fare_vnd must be >= 0")
        if self.distance_fare_vnd < 0:
            raise ValueError("distance_fare_vnd must be >= 0")
        if self.time_fare_vnd < 0:
            raise ValueError("time_fare_vnd must be >= 0")
        if self.surge_multiplier_bps < 10_000:
            raise ValueError("surge_multiplier_bps must be >= 10000")
        if self.total_fare_vnd < 0:
            raise ValueError("total_fare_vnd must be >= 0")


@dataclass(frozen=True, slots=True)
class Trip:
    """The stitched view of one trip — all events joined by trip_id."""

    trip_id: str
    rider_id: str
    driver_id: str  # "" if cancelled before ACCEPT
    vehicle_class: VehicleClass
    origin_district: str
    dest_district: str  # "" if trip didn't reach DROPOFF
    requested_at: datetime
    accepted_at: datetime | None
    picked_up_at: datetime | None
    dropped_off_at: datetime | None
    cancelled_at: datetime | None
    cancel_by: CancelBy | None
    distance_m: int  # 0 if no DROPOFF
    fare_vnd: int  # 0 if no DROPOFF
    surge_bps: int  # 10_000 if no surge

    @property
    def is_completed(self) -> bool:
        return self.dropped_off_at is not None

    @property
    def is_cancelled(self) -> bool:
        return self.cancelled_at is not None

    @property
    def wait_seconds(self) -> int:
        """Seconds from REQUEST → PICKUP. -1 if trip didn't reach PICKUP."""
        if self.picked_up_at is None:
            return -1
        return int((self.picked_up_at - self.requested_at).total_seconds())

    @property
    def dispatch_seconds(self) -> int:
        """Seconds from REQUEST → ACCEPT. -1 if no ACCEPT."""
        if self.accepted_at is None:
            return -1
        return int((self.accepted_at - self.requested_at).total_seconds())

    @property
    def ride_seconds(self) -> int:
        """Seconds from PICKUP → DROPOFF. -1 if trip didn't reach DROPOFF."""
        if self.picked_up_at is None or self.dropped_off_at is None:
            return -1
        return int((self.dropped_off_at - self.picked_up_at).total_seconds())


@dataclass(frozen=True, slots=True)
class SurgeWindow:
    """Detected window of elevated demand on a district × hour bucket."""

    district: str
    hour_bucket: str  # ISO datetime truncated to hour, e.g. "2026-05-17T08:00:00+07:00"
    requests: int  # # of REQUEST events
    completed_trips: int
    completion_rate_pct: float  # completed / requests
    avg_surge_bps: int  # average surge across all REQUESTs in the window

    @property
    def is_surging(self) -> bool:
        """A window is "surging" if surge ≥ 1.2× AND completion < 50%."""
        return self.avg_surge_bps >= 12_000 and self.completion_rate_pct < 50.0


@dataclass(frozen=True, slots=True)
class DriverShift:
    """Per-driver utilization metrics for a (driver, day) bucket."""

    driver_id: str
    shift_date: str  # ISO date in VN_TZ
    trips_completed: int
    trips_cancelled_by_driver: int
    online_seconds: int  # time from first ACCEPT to last DROPOFF / CANCEL
    on_trip_seconds: int  # sum of ACCEPT → DROPOFF intervals
    revenue_vnd: int  # sum of completed fares

    @property
    def utilization_pct(self) -> float:
        """On-trip time as a percentage of online time."""
        if self.online_seconds <= 0:
            return 0.0
        return self.on_trip_seconds / self.online_seconds * 100


__all__ = [
    "VN_TZ",
    "CancelBy",
    "DriverShift",
    "FareBreakdown",
    "SurgeWindow",
    "Trip",
    "TripEvent",
    "TripEventKind",
    "VehicleClass",
]
