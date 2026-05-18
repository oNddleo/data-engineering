"""Trip state machine — validates and stitches per-trip event streams.

The legal transitions:

```
                ACCEPT      PICKUP     DROPOFF
    REQUEST ──────────► ACCEPTED ────► PICKED ────► COMPLETED
       │                  │              │
       │ EXPIRE           │ CANCEL       │ CANCEL
       ↓                  ↓              ↓
    EXPIRED           CANCELLED      CANCELLED
```

``stitch()`` takes an unordered event list and produces one ``Trip``
per ``trip_id``. ``validate_trip_events()`` checks that the per-trip
event sequence respects the state machine — throws ``ValueError``
on illegal transitions (e.g. DROPOFF without PICKUP).
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from vntrip.schema import (
    CancelBy,
    Trip,
    TripEventKind,
    VehicleClass,
)

if TYPE_CHECKING:
    from vntrip.schema import TripEvent


# Legal next-states for each state. CANCEL/EXPIRE are accepted from any
# pre-terminal state and produce CANCELLED / EXPIRED respectively.
_LEGAL_NEXT: dict[TripEventKind, frozenset[TripEventKind]] = {
    TripEventKind.REQUEST: frozenset(
        {TripEventKind.ACCEPT, TripEventKind.EXPIRE, TripEventKind.CANCEL}
    ),
    TripEventKind.ACCEPT: frozenset({TripEventKind.PICKUP, TripEventKind.CANCEL}),
    TripEventKind.PICKUP: frozenset({TripEventKind.DROPOFF, TripEventKind.CANCEL}),
}


def validate_trip_events(events: list[TripEvent]) -> None:
    """Validate that ``events`` (sorted) respect the trip state machine.

    Raises ``ValueError`` on any illegal transition or missing
    initial REQUEST.
    """
    if not events:
        raise ValueError("empty event list")
    sorted_events = sorted(events, key=lambda e: (e.occurred_at, e.event_id))
    if sorted_events[0].kind is not TripEventKind.REQUEST:
        raise ValueError(
            f"trip {sorted_events[0].trip_id!r} does not start with REQUEST"
            f" (starts with {sorted_events[0].kind.value})"
        )
    prev = sorted_events[0]
    for e in sorted_events[1:]:
        if prev.kind in (TripEventKind.DROPOFF, TripEventKind.CANCEL, TripEventKind.EXPIRE):
            raise ValueError(
                f"trip {e.trip_id!r}: event {e.kind.value} after terminal " f"{prev.kind.value}"
            )
        legal = _LEGAL_NEXT.get(prev.kind, frozenset())
        if e.kind not in legal:
            raise ValueError(f"trip {e.trip_id!r}: illegal {prev.kind.value} → {e.kind.value}")
        prev = e


def stitch(events: list[TripEvent]) -> list[Trip]:
    """Stitch the raw event stream into one ``Trip`` per ``trip_id``.

    SURGE_UPDATE events (which are platform-wide and not tied to a
    specific trip flow) are filtered out before grouping. Per-trip
    event streams are validated, then a single ``Trip`` is produced
    per group. Output sorted by ``requested_at`` for stable diffs.
    """
    per_trip: dict[str, list[TripEvent]] = defaultdict(list)
    for e in events:
        if e.kind is TripEventKind.SURGE_UPDATE:
            continue
        per_trip[e.trip_id].append(e)

    out: list[Trip] = []
    for trip_id, trip_events in per_trip.items():
        validate_trip_events(trip_events)
        out.append(_build_trip(trip_id, trip_events))
    out.sort(key=lambda t: (t.requested_at, t.trip_id))
    return out


def _build_trip(trip_id: str, events: list[TripEvent]) -> Trip:
    """Collapse a per-trip event list into a ``Trip``."""
    sorted_events = sorted(events, key=lambda e: (e.occurred_at, e.event_id))
    request = sorted_events[0]  # validated as REQUEST
    accept = _first(sorted_events, TripEventKind.ACCEPT)
    pickup = _first(sorted_events, TripEventKind.PICKUP)
    dropoff = _first(sorted_events, TripEventKind.DROPOFF)
    cancel = _first(sorted_events, TripEventKind.CANCEL)
    expire = _first(sorted_events, TripEventKind.EXPIRE)
    cancelled_at = (
        cancel.occurred_at
        if cancel is not None
        else (expire.occurred_at if expire is not None else None)
    )
    cancel_by = (
        cancel.cancel_by
        if cancel is not None
        else (CancelBy.SYSTEM if expire is not None else None)
    )
    return Trip(
        trip_id=trip_id,
        rider_id=request.rider_id,
        driver_id=accept.driver_id if accept is not None else "",
        vehicle_class=request.vehicle_class,
        origin_district=request.district,
        dest_district=dropoff.district if dropoff is not None else "",
        requested_at=request.occurred_at,
        accepted_at=accept.occurred_at if accept is not None else None,
        picked_up_at=pickup.occurred_at if pickup is not None else None,
        dropped_off_at=dropoff.occurred_at if dropoff is not None else None,
        cancelled_at=cancelled_at,
        cancel_by=cancel_by,
        distance_m=dropoff.distance_m if dropoff is not None else 0,
        fare_vnd=dropoff.fare_vnd if dropoff is not None else 0,
        surge_bps=dropoff.surge_bps if dropoff is not None else 10_000,
    )


def _first(events: list[TripEvent], kind: TripEventKind) -> TripEvent | None:
    """First event matching ``kind`` in ``events``, or ``None``."""
    for e in events:
        if e.kind is kind:
            return e
    return None


__all__ = [
    "VehicleClass",  # re-export for convenience
    "stitch",
    "validate_trip_events",
]
