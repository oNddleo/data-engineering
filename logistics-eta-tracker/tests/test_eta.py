"""ETA predictor: lane stats + fallback tiers."""

from __future__ import annotations

from datetime import timedelta

import pytest

from logietr.eta import build_lane_stats, predict_eta
from logietr.schema import Carrier, ShipmentState
from logietr.tracker import ShipmentStatus

from ._fixtures import DEFAULT_TS, make_shipment


def _delivered(
    ship_id: str, hours: float, carrier: Carrier = Carrier.GHN, origin: str = "A", dest: str = "B"
) -> ShipmentStatus:
    s = make_shipment(
        shipment_id=ship_id,
        carrier=carrier,
        origin_district=origin,
        dest_district=dest,
        created_at=DEFAULT_TS,
        promised_at=DEFAULT_TS + timedelta(hours=36),
    )
    return ShipmentStatus(
        shipment=s,
        state=ShipmentState.DELIVERED,
        last_event_at=DEFAULT_TS + timedelta(hours=hours),
    )


def _pending(
    ship_id: str, carrier: Carrier = Carrier.GHN, origin: str = "A", dest: str = "B"
) -> ShipmentStatus:
    s = make_shipment(
        shipment_id=ship_id,
        carrier=carrier,
        origin_district=origin,
        dest_district=dest,
        created_at=DEFAULT_TS,
        promised_at=DEFAULT_TS + timedelta(hours=36),
    )
    return ShipmentStatus(
        shipment=s,
        state=ShipmentState.PICKED_UP,
        last_event_at=DEFAULT_TS + timedelta(hours=1),
    )


def test_lane_stats_built_from_delivered_only():
    # 3 delivered on lane (A, B, GHN); 1 failed should not contribute.
    completed = [
        _delivered("S-1", 24),
        _delivered("S-2", 25),
        _delivered("S-3", 30),
    ]
    # Failed shipment — should not appear in stats.
    failed_ship = make_shipment(shipment_id="S-4")
    failed_status = ShipmentStatus(
        shipment=failed_ship,
        state=ShipmentState.FAILED,
        last_event_at=DEFAULT_TS + timedelta(hours=50),
    )
    stats = build_lane_stats([*completed, failed_status], min_samples=3)
    assert ("A", "B", Carrier.GHN) in stats
    lane = stats[("A", "B", Carrier.GHN)]
    assert lane.n_samples == 3
    # p50 ~ 25h, p90 ~ 30h
    assert 24 * 3600 <= lane.p50_seconds <= 26 * 3600
    assert lane.p90_seconds >= lane.p50_seconds


def test_lane_skipped_below_min_samples():
    completed = [_delivered("S-1", 24), _delivered("S-2", 25)]  # only 2
    stats = build_lane_stats(completed, min_samples=3)
    assert stats == {}


def test_predict_eta_uses_lane_when_available():
    completed = [_delivered(f"S-{i}", 24) for i in range(5)]
    stats = build_lane_stats(completed, min_samples=3)
    pending = [_pending("S-PEND", origin="A", dest="B", carrier=Carrier.GHN)]
    preds = predict_eta(pending, stats)
    assert len(preds) == 1
    assert preds[0].source == "lane"


def test_predict_eta_falls_back_to_carrier():
    """Pending lane has no samples; carrier has samples on another lane."""
    completed = [_delivered(f"S-{i}", 24, origin="A", dest="B") for i in range(5)]
    stats = build_lane_stats(completed, min_samples=3)
    pending = [_pending("S-NEW", origin="X", dest="Y", carrier=Carrier.GHN)]
    preds = predict_eta(pending, stats)
    assert preds[0].source == "carrier_fallback"


def test_predict_eta_falls_back_to_global():
    """Pending carrier has zero history → global fallback."""
    completed = [_delivered(f"S-{i}", 24, carrier=Carrier.GHN) for i in range(5)]
    stats = build_lane_stats(completed, min_samples=3)
    pending = [_pending("S-NEW", origin="X", dest="Y", carrier=Carrier.GHTK)]
    preds = predict_eta(pending, stats)
    assert preds[0].source == "global_fallback"


def test_predict_eta_no_history_pessimistic_default():
    """No completed shipments anywhere — predictor still returns something."""
    pending = [_pending("S-NEW")]
    preds = predict_eta(pending, {})
    assert preds[0].source == "global_fallback"
    # 48h pessimistic default.
    assert preds[0].predicted_p50 == DEFAULT_TS + timedelta(hours=48)


def test_predict_eta_skips_terminal_shipments():
    completed = [_delivered("S-1", 24)]
    preds = predict_eta(completed, {})
    assert preds == []


def test_predict_eta_p90_bigger_than_p50():
    completed = [_delivered(f"S-{i}", 24 + i) for i in range(10)]
    stats = build_lane_stats(completed, min_samples=3)
    pending = [_pending("S-NEW")]
    preds = predict_eta(pending, stats)
    assert preds[0].predicted_p90 >= preds[0].predicted_p50
    assert preds[0].confidence_band_seconds >= 0


def test_build_lane_stats_validates_min_samples():
    with pytest.raises(ValueError):
        build_lane_stats([], min_samples=0)


def test_lane_stats_hours_properties():
    completed = [_delivered(f"S-{i}", 24) for i in range(5)]
    stats = build_lane_stats(completed, min_samples=3)
    lane = stats[("A", "B", Carrier.GHN)]
    assert 23 <= lane.p50_hours <= 25
    assert lane.p90_hours >= lane.p50_hours
