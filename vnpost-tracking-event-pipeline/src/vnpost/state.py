"""Parcel state machine + event-stream stitcher.

The state-machine validator enforces the canonical scan ordering:

```
CREATED → PICKED_UP → IN_TRANSIT ↔ AT_HUB → OUT_FOR_DELIVERY → DELIVERED
                                                          │
                                                          └→ RETURN_TO_SENDER
```

* ``IN_TRANSIT`` and ``AT_HUB`` may repeat as the parcel hops hubs.
* ``OUT_FOR_DELIVERY`` may repeat (re-attempts after failed delivery).
* ``EXCEPTION`` is legal from any pre-terminal state; the parcel
  remains in EXCEPTION until a normal-progress scan arrives or a
  terminal scan closes it.

``stitch(events)`` groups the event stream by ``tracking_id`` and
builds one ``Parcel`` per group. Per-tracking event lists are sorted
by ``occurred_at`` before processing.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from vnpost.schema import Parcel, ParcelEventKind, ParcelStatus

if TYPE_CHECKING:
    from datetime import datetime

    from vnpost.schema import ParcelEvent


# Legal next-event kinds from each kind. EXCEPTION and the two terminal
# kinds (DELIVERED, RETURN_TO_SENDER) are filled in via free transitions.
_LEGAL_NEXT: dict[ParcelEventKind, frozenset[ParcelEventKind]] = {
    ParcelEventKind.CREATED: frozenset(
        {
            ParcelEventKind.PICKED_UP,
            ParcelEventKind.EXCEPTION,
        }
    ),
    ParcelEventKind.PICKED_UP: frozenset(
        {
            ParcelEventKind.IN_TRANSIT,
            ParcelEventKind.AT_HUB,
            # Same-city same-driver pickup+delivery skips the hub leg entirely.
            # The fraud detector flags whether this was legitimate or scan-skipping.
            ParcelEventKind.OUT_FOR_DELIVERY,
            ParcelEventKind.EXCEPTION,
        }
    ),
    ParcelEventKind.IN_TRANSIT: frozenset(
        {
            ParcelEventKind.AT_HUB,
            ParcelEventKind.IN_TRANSIT,
            ParcelEventKind.OUT_FOR_DELIVERY,
            ParcelEventKind.EXCEPTION,
        }
    ),
    ParcelEventKind.AT_HUB: frozenset(
        {
            ParcelEventKind.IN_TRANSIT,
            ParcelEventKind.AT_HUB,
            ParcelEventKind.OUT_FOR_DELIVERY,
            ParcelEventKind.EXCEPTION,
        }
    ),
    ParcelEventKind.OUT_FOR_DELIVERY: frozenset(
        {
            ParcelEventKind.DELIVERED,
            ParcelEventKind.AT_HUB,
            ParcelEventKind.OUT_FOR_DELIVERY,
            ParcelEventKind.RETURN_TO_SENDER,
            ParcelEventKind.EXCEPTION,
        }
    ),
    ParcelEventKind.EXCEPTION: frozenset(
        {
            ParcelEventKind.IN_TRANSIT,
            ParcelEventKind.AT_HUB,
            ParcelEventKind.OUT_FOR_DELIVERY,
            ParcelEventKind.DELIVERED,
            ParcelEventKind.RETURN_TO_SENDER,
        }
    ),
}


def validate(events: list[ParcelEvent]) -> None:
    """Check that ``events`` (a single tracking_id) respect the state machine.

    Raises ``ValueError`` on:
      * empty list,
      * first event not ``CREATED`` (or ``PICKED_UP`` when CREATED missing —
        some couriers skip the registration scan),
      * any illegal kind transition,
      * any scan after a terminal (DELIVERED / RETURN_TO_SENDER).
    """
    if not events:
        raise ValueError("empty event list")
    sorted_events = sorted(events, key=lambda e: (e.occurred_at, e.event_id))
    first_kind = sorted_events[0].kind
    allowed_starts = (ParcelEventKind.CREATED, ParcelEventKind.PICKED_UP)
    if first_kind not in allowed_starts:
        raise ValueError(
            f"tracking {sorted_events[0].tracking_id!r}: must start with "
            f"CREATED or PICKED_UP, got {first_kind.value}",
        )
    terminals = (ParcelEventKind.DELIVERED, ParcelEventKind.RETURN_TO_SENDER)
    prev = sorted_events[0]
    for e in sorted_events[1:]:
        if prev.kind in terminals:
            raise ValueError(
                f"tracking {e.tracking_id!r}: {e.kind.value} after terminal " f"{prev.kind.value}",
            )
        if e.kind not in _LEGAL_NEXT.get(prev.kind, frozenset()):
            raise ValueError(
                f"tracking {e.tracking_id!r}: illegal " f"{prev.kind.value} → {e.kind.value}",
            )
        prev = e


def stitch(events: list[ParcelEvent]) -> list[Parcel]:
    """Group by ``tracking_id`` and build one ``Parcel`` per group.

    Validates each per-tracking sequence; bad sequences raise
    ``ValueError`` (callers catch + dead-letter as appropriate).
    Output sorted by ``created_at, tracking_id`` for stable diffs.
    """
    per_tracking: dict[str, list[ParcelEvent]] = defaultdict(list)
    for e in events:
        per_tracking[e.tracking_id].append(e)
    out: list[Parcel] = []
    for tracking_id, group in per_tracking.items():
        validate(group)
        out.append(_build_parcel(tracking_id, group))
    out.sort(key=lambda p: (p.created_at, p.tracking_id))
    return out


def _build_parcel(tracking_id: str, events: list[ParcelEvent]) -> Parcel:
    """Collapse a validated per-tracking event list into a ``Parcel``."""
    sorted_events = sorted(events, key=lambda e: (e.occurred_at, e.event_id))
    courier = sorted_events[0].courier
    created = _first_time(sorted_events, ParcelEventKind.CREATED)
    if created is None:
        # Couriers that skip CREATED — use the PICKED_UP time as parcel birth.
        created = _first_time(sorted_events, ParcelEventKind.PICKED_UP)
    assert created is not None  # validate() guarantees this
    picked_up = _first_time(sorted_events, ParcelEventKind.PICKED_UP)
    delivered = _first_time(sorted_events, ParcelEventKind.DELIVERED)
    returned = _first_time(sorted_events, ParcelEventKind.RETURN_TO_SENDER)

    hubs_visited: set[str] = set()
    origin_hub = ""
    dest_hub = ""
    for e in sorted_events:
        if e.hub_code:
            hubs_visited.add(e.hub_code)
            if not origin_hub:
                origin_hub = e.hub_code
            dest_hub = e.hub_code

    status = _classify(sorted_events)
    return Parcel(
        tracking_id=tracking_id,
        courier=courier,
        status=status,
        created_at=created,
        picked_up_at=picked_up,
        delivered_at=delivered,
        returned_at=returned,
        last_event_at=sorted_events[-1].occurred_at,
        n_events=len(sorted_events),
        n_hubs_visited=len(hubs_visited),
        origin_hub=origin_hub,
        dest_hub=dest_hub,
    )


def _first_time(
    events: list[ParcelEvent],
    kind: ParcelEventKind,
) -> datetime | None:
    """Earliest ``occurred_at`` of any event with the given ``kind``."""
    for e in events:
        if e.kind is kind:
            return e.occurred_at
    return None


def _classify(events: list[ParcelEvent]) -> ParcelStatus:
    """Derive ``ParcelStatus`` from the sorted event list."""
    kinds = {e.kind for e in events}
    if ParcelEventKind.DELIVERED in kinds:
        return ParcelStatus.DELIVERED
    if ParcelEventKind.RETURN_TO_SENDER in kinds:
        return ParcelStatus.RETURNED
    if events[-1].kind is ParcelEventKind.EXCEPTION:
        return ParcelStatus.EXCEPTION
    if ParcelEventKind.PICKED_UP in kinds:
        return ParcelStatus.IN_FLIGHT
    return ParcelStatus.PENDING


__all__ = ["stitch", "validate"]
