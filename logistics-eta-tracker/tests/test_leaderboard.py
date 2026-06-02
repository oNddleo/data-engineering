"""Carrier leaderboard."""

from __future__ import annotations

from datetime import timedelta

import pytest

from logietr.leaderboard import carrier_scorecards, rank_by_on_time
from logietr.schema import Carrier, ShipmentState
from logietr.tracker import ShipmentStatus

from ._fixtures import DEFAULT_TS, make_shipment


def _status(
    ship_id: str,
    carrier: Carrier,
    final_state: ShipmentState,
    delivered_hours: float = 24,
    promised_hours: float = 36,
) -> ShipmentStatus:
    s = make_shipment(
        shipment_id=ship_id,
        order_id=f"O-{ship_id}",
        carrier=carrier,
        promised_at=DEFAULT_TS + timedelta(hours=promised_hours),
    )
    return ShipmentStatus(
        shipment=s,
        state=final_state,
        last_event_at=DEFAULT_TS + timedelta(hours=delivered_hours),
    )


def test_scorecards_per_carrier():
    statuses = [
        _status("1", Carrier.GHN, ShipmentState.DELIVERED, 24),
        _status("2", Carrier.GHN, ShipmentState.DELIVERED, 26),
        _status("3", Carrier.GHN, ShipmentState.FAILED, 50),
        _status("4", Carrier.GHTK, ShipmentState.DELIVERED, 30),
    ]
    cards = carrier_scorecards(statuses)
    assert cards[Carrier.GHN].n_total == 3
    assert cards[Carrier.GHN].n_delivered == 2
    assert cards[Carrier.GHN].n_failed == 1
    assert cards[Carrier.GHTK].n_total == 1


def test_delivered_pct_computed():
    statuses = [_status(f"S-{i}", Carrier.GHN, ShipmentState.DELIVERED) for i in range(8)]
    statuses += [_status(f"F-{i}", Carrier.GHN, ShipmentState.FAILED) for i in range(2)]
    cards = carrier_scorecards(statuses)
    assert cards[Carrier.GHN].delivered_pct == 80.0


def test_on_time_pct_counts_delivered_before_promised():
    statuses = [
        _status("1", Carrier.GHN, ShipmentState.DELIVERED, delivered_hours=24, promised_hours=36),
        _status("2", Carrier.GHN, ShipmentState.DELIVERED, delivered_hours=48, promised_hours=36),
    ]
    cards = carrier_scorecards(statuses)
    # 1 of 2 delivered on time.
    assert cards[Carrier.GHN].on_time_pct == 50.0


def test_on_time_pct_zero_with_no_delivered():
    statuses = [_status("1", Carrier.GHN, ShipmentState.FAILED)]
    cards = carrier_scorecards(statuses)
    assert cards[Carrier.GHN].on_time_pct == 0.0


def test_median_transit_zero_without_delivered():
    statuses = [_status("1", Carrier.GHN, ShipmentState.FAILED)]
    cards = carrier_scorecards(statuses)
    assert cards[Carrier.GHN].median_transit_seconds == 0


def test_median_transit_computed():
    statuses = [
        _status(f"S-{i}", Carrier.GHN, ShipmentState.DELIVERED, delivered_hours=h)
        for i, h in enumerate([20, 24, 28])
    ]
    cards = carrier_scorecards(statuses)
    # Median of [20, 24, 28] hours = 24h.
    assert cards[Carrier.GHN].median_transit_seconds == 24 * 3600
    assert cards[Carrier.GHN].median_transit_hours == 24.0


def test_failure_pct_counts_failed_and_returned():
    statuses = [
        _status("1", Carrier.GHN, ShipmentState.DELIVERED),
        _status("2", Carrier.GHN, ShipmentState.FAILED),
        _status("3", Carrier.GHN, ShipmentState.RETURNED),
    ]
    cards = carrier_scorecards(statuses)
    # 2 of 3 failed/returned.
    assert abs(cards[Carrier.GHN].failure_pct - 200 / 3) < 0.01


def test_rank_by_on_time_filters_low_volume():
    # Carrier A: 1 delivered, 100% on-time. Carrier B: 20 delivered, 95% on-time.
    statuses = [_status("A1", Carrier.GHN, ShipmentState.DELIVERED, 24, 36)]
    statuses += [
        _status(
            f"B{i}",
            Carrier.GHTK,
            ShipmentState.DELIVERED,
            delivered_hours=24 if i < 19 else 50,
            promised_hours=36,
        )
        for i in range(20)
    ]
    cards = carrier_scorecards(statuses)
    # min_volume=10 filters GHN (only 1 delivered).
    ranked = rank_by_on_time(cards, min_volume=10)
    assert len(ranked) == 1
    assert ranked[0].carrier is Carrier.GHTK


def test_rank_by_on_time_validates_min_volume():
    with pytest.raises(ValueError):
        rank_by_on_time({}, min_volume=-1)


def test_scorecard_zero_total_safe():
    """Defensive — empty input should not div-by-zero."""
    cards = carrier_scorecards([])
    assert cards == {}


def test_empty_volume_carrier_excluded_from_rank():
    """Carrier with 0 deliveries cannot be on the on-time leaderboard."""
    statuses = [_status("1", Carrier.GHN, ShipmentState.FAILED)]
    cards = carrier_scorecards(statuses)
    assert cards[Carrier.GHN].n_delivered == 0
    assert rank_by_on_time(cards, min_volume=1) == []
