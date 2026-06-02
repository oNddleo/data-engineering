"""Schema + state-machine invariants."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from logietr.schema import (
    TERMINAL_STATES,
    VN_TZ,
    Carrier,
    ShipmentState,
    is_legal_transition,
    lane_key,
)

from ._fixtures import DEFAULT_TS, make_event, make_shipment


def test_vn_tz_offset():
    offset = VN_TZ.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == 7 * 3600


def test_terminal_states():
    assert TERMINAL_STATES == frozenset(
        {ShipmentState.DELIVERED, ShipmentState.FAILED, ShipmentState.RETURNED}
    )


def test_carrier_enum_values():
    assert {c.value for c in Carrier} == {"GHN", "GHTK", "VTP", "VNPOST"}


def test_legal_transition_happy_path():
    from itertools import pairwise

    happy = [
        ShipmentState.CREATED,
        ShipmentState.PICKED_UP,
        ShipmentState.IN_TRANSIT,
        ShipmentState.AT_HUB,
        ShipmentState.OUT_FOR_DELIVERY,
        ShipmentState.DELIVERED,
    ]
    for prev, nxt in pairwise(happy):
        assert is_legal_transition(prev, nxt), f"{prev} -> {nxt} should be legal"


def test_idempotent_reemit_is_legal():
    for state in ShipmentState:
        assert is_legal_transition(state, state)


def test_illegal_backwards_transition():
    assert not is_legal_transition(ShipmentState.DELIVERED, ShipmentState.IN_TRANSIT)
    assert not is_legal_transition(ShipmentState.RETURNED, ShipmentState.PICKED_UP)


def test_failure_recovery_is_legal():
    # FAILED can recover into one-more-try.
    assert is_legal_transition(ShipmentState.FAILED, ShipmentState.OUT_FOR_DELIVERY)
    # FAILED can also be returned.
    assert is_legal_transition(ShipmentState.FAILED, ShipmentState.RETURNED)


def test_out_for_delivery_retry_legal():
    # Driver couldn't reach customer — back to hub for tomorrow.
    assert is_legal_transition(ShipmentState.OUT_FOR_DELIVERY, ShipmentState.AT_HUB)


def test_lane_key_triple():
    assert lane_key("A", "B", Carrier.GHN) == ("A", "B", Carrier.GHN)


def test_shipment_rejects_empty_ids():
    with pytest.raises(ValueError):
        make_shipment(shipment_id="")
    with pytest.raises(ValueError):
        make_shipment(order_id="")
    with pytest.raises(ValueError):
        make_shipment(origin_district="")
    with pytest.raises(ValueError):
        make_shipment(dest_district="")


def test_shipment_rejects_bad_weight():
    with pytest.raises(ValueError):
        make_shipment(weight_g=0)
    with pytest.raises(ValueError):
        make_shipment(weight_g=-1)


def test_shipment_rejects_naive_datetimes():
    with pytest.raises(ValueError):
        make_shipment(promised_at=datetime(2026, 5, 10))
    with pytest.raises(ValueError):
        make_shipment(created_at=datetime(2026, 5, 10))


def test_shipment_rejects_promised_before_created():
    with pytest.raises(ValueError, match="promised_at"):
        make_shipment(promised_at=DEFAULT_TS - timedelta(hours=1))


def test_shipment_rejects_negative_value():
    with pytest.raises(ValueError):
        make_shipment(declared_value_vnd=-1)


def test_event_rejects_empty_ids():
    with pytest.raises(ValueError):
        make_event(event_id="")
    with pytest.raises(ValueError):
        make_event(shipment_id="")


def test_event_rejects_empty_hub_string():
    """``hub_code`` is ``str | None``; if a string is supplied it must be non-empty."""
    with pytest.raises(ValueError):
        make_event(hub_code="")


def test_event_accepts_none_hub_code():
    ev = make_event(hub_code=None)
    assert ev.hub_code is None
