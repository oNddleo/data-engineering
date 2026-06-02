"""Tracker fold + illegal-transition handling."""

from __future__ import annotations

from datetime import timedelta

from logietr.schema import ShipmentState
from logietr.tracker import apply_events, state_distribution

from ._fixtures import DEFAULT_TS, make_event, make_shipment


def _ev(state: ShipmentState, hours: float, eid: str = "E") -> object:
    return make_event(
        event_id=eid,
        state=state,
        occurred_at=DEFAULT_TS + timedelta(hours=hours),
    )


def test_no_events_keeps_shipment_in_created():
    s = make_shipment()
    statuses = apply_events([s], [])
    assert statuses["S-0001"].state is ShipmentState.CREATED
    assert statuses["S-0001"].last_event_at == DEFAULT_TS


def test_happy_path_lands_in_delivered():
    s = make_shipment()
    evs = [
        _ev(ShipmentState.PICKED_UP, 1, "E1"),
        _ev(ShipmentState.IN_TRANSIT, 5, "E2"),
        _ev(ShipmentState.AT_HUB, 10, "E3"),
        _ev(ShipmentState.OUT_FOR_DELIVERY, 20, "E4"),
        _ev(ShipmentState.DELIVERED, 24, "E5"),
    ]
    statuses = apply_events([s], evs)
    st = statuses["S-0001"]
    assert st.state is ShipmentState.DELIVERED
    assert st.is_delivered
    assert st.is_terminal
    assert len(st.history) == 5


def test_out_of_order_events_resorted():
    """Events arrive in shuffled order — tracker must sort by occurred_at first."""
    s = make_shipment()
    evs = [
        _ev(ShipmentState.DELIVERED, 24, "E5"),
        _ev(ShipmentState.PICKED_UP, 1, "E1"),
        _ev(ShipmentState.OUT_FOR_DELIVERY, 20, "E4"),
        _ev(ShipmentState.AT_HUB, 10, "E3"),
        _ev(ShipmentState.IN_TRANSIT, 5, "E2"),
    ]
    statuses = apply_events([s], evs)
    assert statuses["S-0001"].state is ShipmentState.DELIVERED


def test_illegal_transition_silently_dropped():
    """A DELIVERED -> IN_TRANSIT event must not regress state."""
    s = make_shipment()
    evs = [
        _ev(ShipmentState.PICKED_UP, 1, "E1"),
        _ev(ShipmentState.IN_TRANSIT, 5, "E2"),
        _ev(ShipmentState.AT_HUB, 10, "E3"),
        _ev(ShipmentState.OUT_FOR_DELIVERY, 20, "E4"),
        _ev(ShipmentState.DELIVERED, 24, "E5"),
        _ev(ShipmentState.IN_TRANSIT, 30, "E_BUG"),  # carrier replay bug
    ]
    statuses = apply_events([s], evs)
    st = statuses["S-0001"]
    assert st.state is ShipmentState.DELIVERED
    assert st.n_dropped_events == 1


def test_idempotent_reemit_does_not_count_as_drop():
    s = make_shipment()
    evs = [
        _ev(ShipmentState.PICKED_UP, 1, "E1"),
        _ev(ShipmentState.PICKED_UP, 2, "E1B"),  # re-emit
    ]
    statuses = apply_events([s], evs)
    st = statuses["S-0001"]
    assert st.state is ShipmentState.PICKED_UP
    assert st.n_dropped_events == 0
    assert len(st.history) == 2


def test_orphan_events_ignored():
    """Events for unknown shipments are dropped without affecting anything."""
    s = make_shipment()
    orphan = make_event(
        event_id="E-orphan",
        shipment_id="S-DOES-NOT-EXIST",
        state=ShipmentState.DELIVERED,
        occurred_at=DEFAULT_TS + timedelta(hours=1),
    )
    statuses = apply_events([s], [orphan])
    assert statuses["S-0001"].state is ShipmentState.CREATED


def test_failure_recovery_path():
    s = make_shipment()
    evs = [
        _ev(ShipmentState.PICKED_UP, 1, "E1"),
        _ev(ShipmentState.IN_TRANSIT, 5, "E2"),
        _ev(ShipmentState.OUT_FOR_DELIVERY, 20, "E3"),
        _ev(ShipmentState.FAILED, 22, "E4"),
        _ev(ShipmentState.OUT_FOR_DELIVERY, 28, "E5"),  # one more try
        _ev(ShipmentState.DELIVERED, 30, "E6"),
    ]
    statuses = apply_events([s], evs)
    assert statuses["S-0001"].state is ShipmentState.DELIVERED


def test_state_distribution_zeroes_absent_states():
    s = make_shipment()
    statuses = apply_events([s], [_ev(ShipmentState.PICKED_UP, 1)])
    dist = state_distribution(statuses)
    assert dist[ShipmentState.PICKED_UP] == 1
    assert dist[ShipmentState.DELIVERED] == 0
    assert sum(dist.values()) == 1


def test_last_event_at_advances_with_state():
    s = make_shipment()
    evs = [
        _ev(ShipmentState.PICKED_UP, 1, "E1"),
        _ev(ShipmentState.IN_TRANSIT, 5, "E2"),
    ]
    statuses = apply_events([s], evs)
    assert statuses["S-0001"].last_event_at == DEFAULT_TS + timedelta(hours=5)
