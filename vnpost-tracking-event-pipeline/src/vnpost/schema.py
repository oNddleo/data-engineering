"""VN courier tracking event schema.

Models the parcel state machine as emitted by VN courier scan systems
(Viettel Post, GHN, GHTK, J&T Express, Shopee Express). Each
``ParcelEvent`` corresponds to one scanner read at a courier hub or
during a courier driver's collection / delivery attempt.

The canonical parcel state machine:

```
                ┌────── RETURNED   (failed delivery, sent back)
                │
                │      LOST        (no scan in N days)
                │       ▲
                │       │
CREATED → PICKED_UP → IN_TRANSIT → AT_HUB → OUT_FOR_DELIVERY ─→ DELIVERED
                                     ↑                 │
                                     └─── (re-attempt) ┘
```

Money + dimensions are integer VND / grams. Timestamps are tz-aware.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))


class ParcelEventKind(str, Enum):
    """Eight scan events covering the courier state machine."""

    CREATED = "CREATED"  # parcel registered in courier system
    PICKED_UP = "PICKED_UP"  # collected from shipper
    IN_TRANSIT = "IN_TRANSIT"  # in-flight between hubs
    AT_HUB = "AT_HUB"  # arrived at a hub for sorting
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"  # on courier vehicle for last-mile
    DELIVERED = "DELIVERED"  # signed for / dropped at recipient
    RETURN_TO_SENDER = "RETURN_TO_SENDER"  # back-leg started
    EXCEPTION = "EXCEPTION"  # damaged / address bad / customs hold


class ParcelStatus(str, Enum):
    """Six terminal-or-active status values for a stitched parcel."""

    PENDING = "PENDING"  # created, not yet picked up
    IN_FLIGHT = "IN_FLIGHT"  # picked up, not yet delivered/returned
    DELIVERED = "DELIVERED"  # successfully delivered
    RETURNED = "RETURNED"  # returned to sender
    LOST = "LOST"  # no scan in N days
    EXCEPTION = "EXCEPTION"  # operational exception, may be resolved


class CourierCode(str, Enum):
    """Five major VN couriers as of 2026 (covering ~85% of e-commerce volume)."""

    VTP = "VTP"  # Viettel Post — Bưu chính Viettel
    GHN = "GHN"  # GiaoHangNhanh
    GHTK = "GHTK"  # GiaoHangTietKiem (Frasers Property)
    JT = "JT"  # J&T Express VN
    SPX = "SPX"  # Shopee Express


@dataclass(frozen=True, slots=True)
class ParcelEvent:
    """One scan event in the tracking stream.

    ``hub_code`` is the canonical hub identifier (e.g. ``HCM-Q1``,
    ``HN-TM``, ``DN-HC``); ``"" `` for events that don't happen at
    a hub (CREATED, OUT_FOR_DELIVERY, DELIVERED).
    """

    event_id: str
    tracking_id: str  # courier's parcel ID
    courier: CourierCode
    kind: ParcelEventKind
    occurred_at: datetime
    hub_code: str = ""  # e.g. "HCM-TPN" (Tân Phú), "" for off-hub events
    note: str = ""  # courier's free-text annotation

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id must be non-empty")
        if not self.tracking_id:
            raise ValueError("tracking_id must be non-empty")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class Parcel:
    """The stitched view of one parcel — all events joined by ``tracking_id``."""

    tracking_id: str
    courier: CourierCode
    status: ParcelStatus
    created_at: datetime
    picked_up_at: datetime | None
    delivered_at: datetime | None
    returned_at: datetime | None
    last_event_at: datetime  # most recent scan
    n_events: int  # total scans recorded
    n_hubs_visited: int  # distinct hubs touched
    origin_hub: str  # first hub seen
    dest_hub: str  # last hub before delivery (or last seen)

    @property
    def is_delivered(self) -> bool:
        return self.status is ParcelStatus.DELIVERED

    @property
    def is_returned(self) -> bool:
        return self.status is ParcelStatus.RETURNED

    @property
    def is_lost(self) -> bool:
        return self.status is ParcelStatus.LOST

    @property
    def transit_hours(self) -> int:
        """Pickup → delivery in hours. ``-1`` if not delivered."""
        if self.delivered_at is None or self.picked_up_at is None:
            return -1
        return int((self.delivered_at - self.picked_up_at).total_seconds() // 3600)


@dataclass(frozen=True, slots=True)
class CourierSLA:
    """Per-courier on-time SLA roll-up over a parcel cohort."""

    courier: CourierCode
    n_parcels: int  # total parcels in scope
    n_delivered: int
    n_on_time: int  # delivered within SLA hours
    median_transit_hours: int
    p95_transit_hours: int
    on_time_rate_pct: float  # n_on_time / n_delivered × 100

    def __post_init__(self) -> None:
        if self.n_parcels < 0 or self.n_delivered < 0 or self.n_on_time < 0:
            raise ValueError("counts must be >= 0")
        if self.n_on_time > self.n_delivered:
            raise ValueError("n_on_time > n_delivered")
        if self.n_delivered > self.n_parcels:
            raise ValueError("n_delivered > n_parcels")

    @property
    def delivery_rate_pct(self) -> float:
        if self.n_parcels == 0:
            return 0.0
        return self.n_delivered / self.n_parcels * 100


__all__ = [
    "VN_TZ",
    "CourierCode",
    "CourierSLA",
    "Parcel",
    "ParcelEvent",
    "ParcelEventKind",
    "ParcelStatus",
]
