"""Apply tracking events to shipments to derive ``ShipmentStatus``.

The tracker is the **state-folding** layer: take a manifest +
chronological event stream and produce one ``ShipmentStatus`` per
shipment with its current state, last-update time, and the full
sorted history.

Out-of-order delivery is the norm for VN 3PL webhooks — events
arrive late, duplicated, or in the wrong sequence. The tracker:

1. Sorts events by ``occurred_at`` per shipment before applying.
2. Skips idempotent re-emits (same state as current).
3. Skips events that would cause an **illegal backwards** transition
   (e.g. ``DELIVERED → IN_TRANSIT``) — these are carrier bugs we
   tolerate rather than blow up on.
4. Refuses events from terminal states unless they're explicit
   FAILED → RETURNED / FAILED → OUT_FOR_DELIVERY recoveries that the
   state machine allows.

Events for unknown shipments are dropped (the manifest is
authoritative; orphans are likely a different fulfilment partner).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from logietr.schema import TERMINAL_STATES, ShipmentState, is_legal_transition

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime

    from logietr.schema import Shipment, TrackingEvent


@dataclass(slots=True)
class ShipmentStatus:
    """Materialised view: where one shipment is *right now*."""

    shipment: Shipment
    state: ShipmentState
    last_event_at: datetime
    history: list[TrackingEvent] = field(default_factory=list)
    n_dropped_events: int = 0  # illegal transitions silently dropped

    @property
    def is_terminal(self) -> bool:
        return self.state in TERMINAL_STATES

    @property
    def is_delivered(self) -> bool:
        return self.state is ShipmentState.DELIVERED


def apply_events(
    shipments: Iterable[Shipment], events: Iterable[TrackingEvent]
) -> dict[str, ShipmentStatus]:
    """Fold ``events`` onto ``shipments`` → ``{shipment_id: ShipmentStatus}``.

    Each shipment starts in ``CREATED`` at ``shipment.created_at`` —
    even if no event has fired yet.
    """
    by_id: dict[str, ShipmentStatus] = {}
    for s in shipments:
        by_id[s.shipment_id] = ShipmentStatus(
            shipment=s,
            state=ShipmentState.CREATED,
            last_event_at=s.created_at,
        )

    grouped: dict[str, list[TrackingEvent]] = defaultdict(list)
    for ev in events:
        if ev.shipment_id in by_id:
            grouped[ev.shipment_id].append(ev)

    for shipment_id, evs in grouped.items():
        evs.sort(key=lambda e: e.occurred_at)
        status = by_id[shipment_id]
        for ev in evs:
            if not is_legal_transition(status.state, ev.state):
                status.n_dropped_events += 1
                continue
            if ev.state == status.state:
                # Idempotent re-emit — record in history but don't bump state.
                status.history.append(ev)
                if ev.occurred_at > status.last_event_at:
                    status.last_event_at = ev.occurred_at
                continue
            status.state = ev.state
            status.last_event_at = ev.occurred_at
            status.history.append(ev)

    return by_id


def state_distribution(statuses: dict[str, ShipmentStatus]) -> dict[ShipmentState, int]:
    """Count of shipments per state — for dashboards."""
    counts: dict[ShipmentState, int] = {s: 0 for s in ShipmentState}
    for st in statuses.values():
        counts[st.state] += 1
    return counts


__all__ = ["ShipmentStatus", "apply_events", "state_distribution"]
