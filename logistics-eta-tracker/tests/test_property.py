"""Hypothesis properties — invariants the tracker must preserve."""

from __future__ import annotations

from datetime import datetime, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from logietr.schema import (
    TERMINAL_STATES,
    VN_TZ,
    Carrier,
    Shipment,
    ShipmentState,
    TrackingEvent,
    is_legal_transition,
)
from logietr.tracker import apply_events

_BASE = datetime(2026, 5, 1, 9, 0, 0, tzinfo=VN_TZ)


def _make_ship(idx: int) -> Shipment:
    return Shipment(
        shipment_id=f"S-{idx:04d}",
        order_id=f"O-{idx:04d}",
        carrier=Carrier.GHN,
        origin_district="A",
        dest_district="B",
        weight_g=500,
        declared_value_vnd=100_000,
        promised_at=_BASE + timedelta(hours=48),
        created_at=_BASE,
    )


@st.composite
def _events_for(draw: st.DrawFn, ship: Shipment) -> list[TrackingEvent]:
    n = draw(st.integers(min_value=0, max_value=8))
    out: list[TrackingEvent] = []
    for i in range(n):
        state = draw(st.sampled_from(list(ShipmentState)))
        hours = draw(st.integers(min_value=1, max_value=72))
        out.append(
            TrackingEvent(
                event_id=f"E-{ship.shipment_id}-{i:02d}",
                shipment_id=ship.shipment_id,
                state=state,
                occurred_at=ship.created_at + timedelta(hours=hours),
                hub_code=None,
            )
        )
    return out


@given(seed=st.integers(min_value=0, max_value=1000))
@settings(max_examples=50, deadline=None)
def test_terminal_state_is_sticky(seed: int) -> None:
    """Once a shipment hits a terminal state, no event can pull it out illegally."""
    import random

    rng = random.Random(seed)
    ship = _make_ship(0)
    # Force a delivered run.
    evs = [
        TrackingEvent(
            event_id=f"E-{i}",
            shipment_id=ship.shipment_id,
            state=s,
            occurred_at=ship.created_at + timedelta(hours=h),
            hub_code=None,
        )
        for i, (s, h) in enumerate(
            [
                (ShipmentState.PICKED_UP, 1),
                (ShipmentState.IN_TRANSIT, 5),
                (ShipmentState.OUT_FOR_DELIVERY, 20),
                (ShipmentState.DELIVERED, 24),
            ]
        )
    ]
    # Append a random burst of late events.
    for i in range(rng.randint(0, 5)):
        state = rng.choice(list(ShipmentState))
        evs.append(
            TrackingEvent(
                event_id=f"E-late-{i}",
                shipment_id=ship.shipment_id,
                state=state,
                occurred_at=ship.created_at + timedelta(hours=30 + i),
                hub_code=None,
            )
        )
    statuses = apply_events([ship], evs)
    # Tracker must not regress out of DELIVERED.
    assert statuses[ship.shipment_id].state in TERMINAL_STATES


@given(n_ships=st.integers(min_value=1, max_value=5), seed=st.integers(min_value=0, max_value=1000))
@settings(max_examples=30, deadline=None)
def test_orphan_events_dont_affect_known_shipments(n_ships: int, seed: int) -> None:
    """An event for an unknown ``shipment_id`` must not mutate any known status."""
    import random

    rng = random.Random(seed)
    ships = [_make_ship(i) for i in range(n_ships)]
    real_events = [
        TrackingEvent(
            event_id=f"E-{i}",
            shipment_id=ships[i % n_ships].shipment_id,
            state=ShipmentState.PICKED_UP,
            occurred_at=ships[i % n_ships].created_at + timedelta(hours=1),
            hub_code=None,
        )
        for i in range(n_ships)
    ]
    orphan_events = [
        TrackingEvent(
            event_id=f"O-{i}",
            shipment_id=f"GHOST-{i}",
            state=rng.choice(list(ShipmentState)),
            occurred_at=_BASE + timedelta(hours=rng.randint(1, 50)),
            hub_code=None,
        )
        for i in range(5)
    ]
    a = apply_events(ships, real_events)
    b = apply_events(ships, real_events + orphan_events)
    for sid in (s.shipment_id for s in ships):
        assert a[sid].state == b[sid].state
        assert a[sid].n_dropped_events == b[sid].n_dropped_events


@given(state=st.sampled_from(list(ShipmentState)))
@settings(max_examples=20, deadline=None)
def test_idempotent_reemit_is_always_legal(state: ShipmentState) -> None:
    assert is_legal_transition(state, state)


@given(n=st.integers(min_value=1, max_value=20))
@settings(max_examples=20, deadline=None)
def test_history_preserved_in_order(n: int) -> None:
    """``status.history`` records events in arrival order after the resort."""
    ship = _make_ship(0)
    evs = [
        TrackingEvent(
            event_id=f"E-{i}",
            shipment_id=ship.shipment_id,
            state=ShipmentState.PICKED_UP,
            occurred_at=ship.created_at + timedelta(hours=i + 1),
            hub_code=None,
        )
        for i in range(n)
    ]
    # All but the first are idempotent re-emits.
    statuses = apply_events([ship], evs)
    history = statuses[ship.shipment_id].history
    times = [e.occurred_at for e in history]
    assert times == sorted(times)
