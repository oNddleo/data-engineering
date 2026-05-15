"""SLA breach detection (OVERDUE + STUCK)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from logietr.schema import ShipmentState
from logietr.sla import BreachKind, find_overdue, find_stuck
from logietr.tracker import ShipmentStatus, apply_events

from ._fixtures import DEFAULT_TS, make_event, make_shipment


def test_overdue_finds_past_promised_at():
    s = make_shipment(promised_at=DEFAULT_TS + timedelta(hours=24))
    statuses = apply_events([s], [])  # still in CREATED
    now = DEFAULT_TS + timedelta(hours=48)
    breaches = find_overdue(statuses, now)
    assert len(breaches) == 1
    assert breaches[0].kind is BreachKind.OVERDUE
    assert breaches[0].overdue_seconds == 24 * 3600


def test_overdue_excludes_terminal_states():
    s = make_shipment(promised_at=DEFAULT_TS + timedelta(hours=24))
    evs = [
        make_event(state=ShipmentState.PICKED_UP, occurred_at=DEFAULT_TS + timedelta(hours=1)),
        make_event(
            event_id="E2",
            state=ShipmentState.IN_TRANSIT,
            occurred_at=DEFAULT_TS + timedelta(hours=5),
        ),
        make_event(
            event_id="E3",
            state=ShipmentState.OUT_FOR_DELIVERY,
            occurred_at=DEFAULT_TS + timedelta(hours=10),
        ),
        make_event(
            event_id="E4",
            state=ShipmentState.DELIVERED,
            occurred_at=DEFAULT_TS + timedelta(hours=20),
        ),
    ]
    statuses = apply_events([s], evs)
    now = DEFAULT_TS + timedelta(hours=48)
    assert find_overdue(statuses, now) == []


def test_overdue_excludes_on_time_shipments():
    s = make_shipment(promised_at=DEFAULT_TS + timedelta(hours=48))
    statuses = apply_events([s], [])
    now = DEFAULT_TS + timedelta(hours=24)
    assert find_overdue(statuses, now) == []


def test_overdue_sorted_by_most_overdue_first():
    s1 = make_shipment(
        shipment_id="S-1", order_id="O-1", promised_at=DEFAULT_TS + timedelta(hours=10)
    )
    s2 = make_shipment(
        shipment_id="S-2", order_id="O-2", promised_at=DEFAULT_TS + timedelta(hours=20)
    )
    statuses = apply_events([s1, s2], [])
    now = DEFAULT_TS + timedelta(hours=48)
    breaches = find_overdue(statuses, now)
    assert breaches[0].shipment_id == "S-1"  # more overdue
    assert breaches[1].shipment_id == "S-2"


def test_stuck_finds_shipments_without_recent_events():
    s = make_shipment()
    # One event 1 hour after creation; ``now`` is 48h later.
    evs = [make_event(state=ShipmentState.PICKED_UP, occurred_at=DEFAULT_TS + timedelta(hours=1))]
    statuses = apply_events([s], evs)
    now = DEFAULT_TS + timedelta(hours=48)
    breaches = find_stuck(statuses, now, stuck_after=timedelta(hours=24))
    assert len(breaches) == 1
    assert breaches[0].kind is BreachKind.STUCK
    # Gap was 47h, threshold was 24h, overdue beyond = 23h.
    assert breaches[0].overdue_seconds == 23 * 3600


def test_stuck_skips_just_created_shipments_with_no_events():
    """CREATED with no event yet — that's the seller's problem, not the carrier's."""
    s = make_shipment()
    statuses = apply_events([s], [])
    now = DEFAULT_TS + timedelta(hours=72)
    assert find_stuck(statuses, now) == []


def test_stuck_skips_terminal_shipments():
    s = make_shipment()
    evs = [
        make_event(state=ShipmentState.PICKED_UP, occurred_at=DEFAULT_TS + timedelta(hours=1)),
        make_event(
            event_id="E2",
            state=ShipmentState.IN_TRANSIT,
            occurred_at=DEFAULT_TS + timedelta(hours=5),
        ),
        make_event(
            event_id="E3",
            state=ShipmentState.OUT_FOR_DELIVERY,
            occurred_at=DEFAULT_TS + timedelta(hours=10),
        ),
        make_event(
            event_id="E4",
            state=ShipmentState.DELIVERED,
            occurred_at=DEFAULT_TS + timedelta(hours=20),
        ),
    ]
    statuses = apply_events([s], evs)
    now = DEFAULT_TS + timedelta(hours=240)
    assert find_stuck(statuses, now) == []


def test_stuck_threshold_validated():
    with pytest.raises(ValueError):
        find_stuck({}, DEFAULT_TS, stuck_after=timedelta(hours=0))
    with pytest.raises(ValueError):
        find_stuck({}, DEFAULT_TS, stuck_after=timedelta(hours=-1))


def test_breach_overdue_hours_property():
    s = make_shipment(promised_at=DEFAULT_TS + timedelta(hours=10))
    statuses = apply_events([s], [])
    now = DEFAULT_TS + timedelta(hours=25)
    [b] = find_overdue(statuses, now)
    assert b.overdue_hours == 15.0


def test_overdue_and_stuck_can_overlap():
    """A shipment can be both overdue AND stuck simultaneously."""
    s = make_shipment(promised_at=DEFAULT_TS + timedelta(hours=10))
    statuses: dict[str, ShipmentStatus] = apply_events(
        [s],
        [make_event(state=ShipmentState.PICKED_UP, occurred_at=DEFAULT_TS + timedelta(hours=1))],
    )
    now = DEFAULT_TS + timedelta(hours=48)
    assert len(find_overdue(statuses, now)) == 1
    assert len(find_stuck(statuses, now, stuck_after=timedelta(hours=12))) == 1
