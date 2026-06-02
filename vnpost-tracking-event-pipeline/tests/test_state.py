"""State machine validation + stitching."""

from __future__ import annotations

from datetime import timedelta

import pytest

from vnpost.schema import ParcelStatus
from vnpost.state import stitch, validate

from ._fixtures import (
    DEFAULT_TS,
    at_hub,
    created,
    delivered,
    in_transit,
    out_for_delivery,
    picked_up,
    return_to_sender,
)

# ---------- validate ---------------------------------------------------------


def test_validate_happy_path():
    events = [
        created("T-1", DEFAULT_TS),
        picked_up("T-1", DEFAULT_TS + timedelta(hours=2)),
        at_hub("T-1", DEFAULT_TS + timedelta(hours=4), "HCM-TPN"),
        out_for_delivery("T-1", DEFAULT_TS + timedelta(hours=20), "HN-CG"),
        delivered("T-1", DEFAULT_TS + timedelta(hours=24)),
    ]
    validate(events)


def test_validate_starting_at_picked_up_ok():
    """Couriers that skip CREATED → start at PICKED_UP."""
    events = [
        picked_up("T-1", DEFAULT_TS),
        at_hub("T-1", DEFAULT_TS + timedelta(hours=2), "HCM-TPN"),
        out_for_delivery("T-1", DEFAULT_TS + timedelta(hours=20), "HN-CG"),
        delivered("T-1", DEFAULT_TS + timedelta(hours=24)),
    ]
    validate(events)


def test_validate_rejects_start_at_delivered():
    events = [delivered("T-1", DEFAULT_TS)]
    with pytest.raises(ValueError, match="must start with"):
        validate(events)


def test_validate_rejects_post_terminal_scan():
    events = [
        picked_up("T-1", DEFAULT_TS),
        out_for_delivery("T-1", DEFAULT_TS + timedelta(hours=2), "HCM-TPN"),
        delivered("T-1", DEFAULT_TS + timedelta(hours=4)),
        in_transit("T-1", DEFAULT_TS + timedelta(hours=5), "HN-CG"),
    ]
    with pytest.raises(ValueError, match="after terminal"):
        validate(events)


def test_validate_allows_same_city_picked_to_out():
    """PICKED_UP → OUT_FOR_DELIVERY is legal (same-city single-driver)."""
    events = [
        picked_up("T-1", DEFAULT_TS, hub="HCM-TPN"),
        out_for_delivery("T-1", DEFAULT_TS + timedelta(hours=4), "HCM-Q12"),
        delivered("T-1", DEFAULT_TS + timedelta(hours=6)),
    ]
    validate(events)


def test_validate_rejects_illegal_jump():
    """CREATED → DELIVERED is not a legal transition."""
    events = [
        created("T-1", DEFAULT_TS),
        delivered("T-1", DEFAULT_TS + timedelta(hours=1)),
    ]
    with pytest.raises(ValueError, match="illegal"):
        validate(events)


def test_validate_repeat_at_hub_legal():
    """A parcel can hop multiple AT_HUBs in a row."""
    events = [
        picked_up("T-1", DEFAULT_TS, hub="HCM-TPN"),
        at_hub("T-1", DEFAULT_TS + timedelta(hours=2), "HCM-TPN"),
        at_hub("T-1", DEFAULT_TS + timedelta(hours=8), "VN-NSC"),
        at_hub("T-1", DEFAULT_TS + timedelta(hours=20), "HN-CG"),
        out_for_delivery("T-1", DEFAULT_TS + timedelta(hours=22), "HN-HD"),
        delivered("T-1", DEFAULT_TS + timedelta(hours=24)),
    ]
    validate(events)


def test_validate_rejects_empty():
    with pytest.raises(ValueError, match="empty"):
        validate([])


# ---------- stitch -----------------------------------------------------------


def test_stitch_one_parcel_delivered():
    events = [
        created("T-1", DEFAULT_TS),
        picked_up("T-1", DEFAULT_TS + timedelta(hours=2), hub="HCM-TPN"),
        at_hub("T-1", DEFAULT_TS + timedelta(hours=8), "HN-CG"),
        out_for_delivery("T-1", DEFAULT_TS + timedelta(hours=20), "HN-HD"),
        delivered("T-1", DEFAULT_TS + timedelta(hours=24)),
    ]
    [p] = stitch(events)
    assert p.status is ParcelStatus.DELIVERED
    assert p.origin_hub == "HCM-TPN"
    assert p.dest_hub == "HN-HD"
    assert p.transit_hours == 22


def test_stitch_returned_parcel():
    events = [
        created("T-1", DEFAULT_TS),
        picked_up("T-1", DEFAULT_TS + timedelta(hours=2), hub="HCM-TPN"),
        out_for_delivery("T-1", DEFAULT_TS + timedelta(hours=20), "HN-HD"),
        return_to_sender("T-1", DEFAULT_TS + timedelta(hours=24)),
    ]
    [p] = stitch(events)
    assert p.status is ParcelStatus.RETURNED
    assert p.returned_at is not None


def test_stitch_pending_parcel():
    """Created but never picked up = PENDING."""
    events = [created("T-1", DEFAULT_TS)]
    [p] = stitch(events)
    assert p.status is ParcelStatus.PENDING


def test_stitch_in_flight_parcel():
    """Picked up but not yet delivered = IN_FLIGHT."""
    events = [
        created("T-1", DEFAULT_TS),
        picked_up("T-1", DEFAULT_TS + timedelta(hours=2)),
        at_hub("T-1", DEFAULT_TS + timedelta(hours=6), "HCM-TPN"),
    ]
    [p] = stitch(events)
    assert p.status is ParcelStatus.IN_FLIGHT


def test_stitch_multiple_parcels_sorted():
    """Parcels emitted in creation-time order."""
    events = [
        created("T-1", DEFAULT_TS + timedelta(hours=10)),
        created("T-2", DEFAULT_TS),
        created("T-3", DEFAULT_TS + timedelta(hours=5)),
    ]
    out = stitch(events)
    assert [p.tracking_id for p in out] == ["T-2", "T-3", "T-1"]


def test_stitch_counts_hubs():
    events = [
        picked_up("T-1", DEFAULT_TS, hub="HCM-TPN"),
        at_hub("T-1", DEFAULT_TS + timedelta(hours=2), "HCM-Q12"),
        at_hub("T-1", DEFAULT_TS + timedelta(hours=6), "VN-NSC"),
        at_hub("T-1", DEFAULT_TS + timedelta(hours=10), "HN-CG"),
        out_for_delivery("T-1", DEFAULT_TS + timedelta(hours=20), "HN-HD"),
        delivered("T-1", DEFAULT_TS + timedelta(hours=24)),
    ]
    [p] = stitch(events)
    # Hubs: HCM-TPN, HCM-Q12, VN-NSC, HN-CG, HN-HD = 5 distinct
    assert p.n_hubs_visited == 5
