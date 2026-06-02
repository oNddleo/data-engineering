"""SLA computation (Tết-aware)."""

from __future__ import annotations

from datetime import datetime, timedelta

from vnpost.schema import VN_TZ, CourierCode
from vnpost.sla import compute_sla, hours_in_tet_block
from vnpost.state import stitch

from ._fixtures import (
    DEFAULT_TS,
    at_hub,
    created,
    delivered,
    in_transit,
    out_for_delivery,
    picked_up,
)


def _full_trip(
    tracking: str,
    pickup_offset_h: int = 1,
    delivered_offset_h: int = 24,
    courier: CourierCode = CourierCode.GHN,
    origin_hub: str = "HCM-TPN",
    dest_hub: str = "HN-CG",
) -> list:
    return [
        created(tracking, DEFAULT_TS, courier=courier),
        picked_up(
            tracking,
            DEFAULT_TS + timedelta(hours=pickup_offset_h),
            hub=origin_hub,
            courier=courier,
        ),
        at_hub(
            tracking,
            DEFAULT_TS + timedelta(hours=pickup_offset_h + 2),
            origin_hub,
            courier=courier,
        ),
        in_transit(
            tracking,
            DEFAULT_TS + timedelta(hours=pickup_offset_h + 8),
            "VN-NSC",
            courier=courier,
        ),
        out_for_delivery(
            tracking,
            DEFAULT_TS + timedelta(hours=delivered_offset_h - 2),
            dest_hub,
            courier=courier,
        ),
        delivered(
            tracking,
            DEFAULT_TS + timedelta(hours=delivered_offset_h),
            courier=courier,
        ),
    ]


# ---------- compute_sla ------------------------------------------------------


def test_compute_sla_basic():
    events = []
    for i in range(5):
        events.extend(_full_trip(f"T-{i}", delivered_offset_h=24))
    parcels = stitch(events)
    [sla] = compute_sla(parcels, tet_aware=False)
    assert sla.courier is CourierCode.GHN
    assert sla.n_parcels == 5
    assert sla.n_delivered == 5
    # GHN inter-city SLA = 72h; 24h < 72h → all on time
    assert sla.n_on_time == 5
    assert sla.on_time_rate_pct == 100.0


def test_compute_sla_groups_by_courier():
    events = []
    events.extend(_full_trip("T-1", courier=CourierCode.GHN))
    events.extend(_full_trip("T-2", courier=CourierCode.VTP))
    events.extend(_full_trip("T-3", courier=CourierCode.JT))
    parcels = stitch(events)
    slas = compute_sla(parcels)
    assert len(slas) == 3
    codes = [s.courier for s in slas]
    assert sorted(codes, key=lambda c: c.value) == codes


def test_compute_sla_late_parcel():
    """Inter-city parcel delivered after 96h misses GHN's 72h SLA."""
    events = _full_trip("T-1", delivered_offset_h=96)
    parcels = stitch(events)
    [sla] = compute_sla(parcels, tet_aware=False)
    assert sla.n_on_time == 0
    assert sla.on_time_rate_pct == 0.0


def test_compute_sla_same_city_tighter_threshold():
    """Same-city has 24h SLA — a 48h transit is late."""
    events = _full_trip(
        "T-1",
        delivered_offset_h=48,
        origin_hub="HCM-TPN",
        dest_hub="HCM-Q12",
    )
    parcels = stitch(events)
    [sla] = compute_sla(parcels, tet_aware=False)
    assert sla.n_delivered == 1
    # 48h > 24h same-city → late
    assert sla.n_on_time == 0


# ---------- hours_in_tet_block ----------------------------------------------


def test_tet_block_no_overlap():
    a = datetime(2026, 5, 1, 0, 0, 0, tzinfo=VN_TZ)
    b = datetime(2026, 5, 3, 0, 0, 0, tzinfo=VN_TZ)
    assert hours_in_tet_block(a, b) == 0


def test_tet_block_full_overlap():
    """An interval entirely inside Tết 2026 (Feb 16-21)."""
    a = datetime(2026, 2, 17, 0, 0, 0, tzinfo=VN_TZ)
    b = datetime(2026, 2, 19, 0, 0, 0, tzinfo=VN_TZ)
    h = hours_in_tet_block(a, b)
    assert h == 48


def test_tet_block_partial_overlap_at_start():
    """Interval starts before Tết and ends inside it."""
    a = datetime(2026, 2, 14, 0, 0, 0, tzinfo=VN_TZ)
    b = datetime(2026, 2, 18, 0, 0, 0, tzinfo=VN_TZ)
    h = hours_in_tet_block(a, b)
    # Block starts Feb 16 → overlap Feb 16 00:00 to Feb 18 00:00 = 48h
    assert h == 48


def test_tet_block_zero_when_inverted():
    a = datetime(2026, 5, 18, 0, 0, 0, tzinfo=VN_TZ)
    b = datetime(2026, 5, 1, 0, 0, 0, tzinfo=VN_TZ)
    assert hours_in_tet_block(a, b) == 0


def test_compute_sla_tet_aware_subtracts_block():
    """A parcel transiting through Tết should be on-time after Tết adjustment."""
    # Pickup Feb 14 2026, delivered Feb 22 2026 — total 192h elapsed.
    # Tết block: Feb 16-21 = 5 days = 120h overlap with [14, 22).
    pickup_at = datetime(2026, 2, 14, 9, 0, 0, tzinfo=VN_TZ)
    delivered_at = datetime(2026, 2, 22, 9, 0, 0, tzinfo=VN_TZ)
    events = [
        picked_up("T-tet", pickup_at, hub="HCM-TPN"),
        at_hub("T-tet", pickup_at + timedelta(hours=2), "HCM-TPN"),
        in_transit("T-tet", pickup_at + timedelta(hours=10), "VN-NSC"),
        out_for_delivery("T-tet", delivered_at - timedelta(hours=2), "HN-CG"),
        delivered("T-tet", delivered_at),
    ]
    parcels = stitch(events)
    [sla_no_adj] = compute_sla(parcels, tet_aware=False)
    [sla_adj] = compute_sla(parcels, tet_aware=True)
    # Without Tết: 192h transit > 72h SLA → late.
    assert sla_no_adj.n_on_time == 0
    # With Tết: 192h - ~120h = ~72h, should be on-time (== threshold).
    assert sla_adj.n_on_time == 1
