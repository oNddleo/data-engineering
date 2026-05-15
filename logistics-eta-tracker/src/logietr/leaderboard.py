"""Carrier comparison: who delivers fastest and most reliably?

Operations teams switch between GHN / GHTK / VTP / VNPOST per lane.
The leaderboard exposes the comparison: per-carrier delivered rate,
on-time rate (delivered before ``promised_at``), failure rate, and
median transit time. It's a pure function over completed
``ShipmentStatus`` so it composes cleanly with the tracker.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from logietr.schema import Carrier, ShipmentState

if TYPE_CHECKING:
    from logietr.tracker import ShipmentStatus


@dataclass(frozen=True, slots=True)
class CarrierScorecard:
    """One row of the carrier leaderboard."""

    carrier: Carrier
    n_total: int
    n_delivered: int
    n_failed: int
    n_returned: int
    n_on_time: int  # delivered before promised_at
    median_transit_seconds: int  # 0 when n_delivered == 0

    @property
    def delivered_pct(self) -> float:
        return self.n_delivered / self.n_total * 100 if self.n_total else 0.0

    @property
    def failure_pct(self) -> float:
        if self.n_total == 0:
            return 0.0
        return (self.n_failed + self.n_returned) / self.n_total * 100

    @property
    def on_time_pct(self) -> float:
        """Of delivered shipments, how many made it before ``promised_at``."""
        if self.n_delivered == 0:
            return 0.0
        return self.n_on_time / self.n_delivered * 100

    @property
    def median_transit_hours(self) -> float:
        return self.median_transit_seconds / 3600


def carrier_scorecards(
    statuses: list[ShipmentStatus],
) -> dict[Carrier, CarrierScorecard]:
    """Aggregate every (terminal + non-terminal) shipment by carrier."""
    by_carrier: dict[Carrier, list[ShipmentStatus]] = defaultdict(list)
    for st in statuses:
        by_carrier[st.shipment.carrier].append(st)
    out: dict[Carrier, CarrierScorecard] = {}
    for carrier, group in by_carrier.items():
        n_delivered = sum(1 for s in group if s.state is ShipmentState.DELIVERED)
        n_failed = sum(1 for s in group if s.state is ShipmentState.FAILED)
        n_returned = sum(1 for s in group if s.state is ShipmentState.RETURNED)
        delivered_durations = sorted(
            int((s.last_event_at - s.shipment.created_at).total_seconds())
            for s in group
            if s.state is ShipmentState.DELIVERED
        )
        if delivered_durations:
            mid = len(delivered_durations) // 2
            median = delivered_durations[mid]
        else:
            median = 0
        n_on_time = sum(
            1
            for s in group
            if s.state is ShipmentState.DELIVERED and s.last_event_at <= s.shipment.promised_at
        )
        out[carrier] = CarrierScorecard(
            carrier=carrier,
            n_total=len(group),
            n_delivered=n_delivered,
            n_failed=n_failed,
            n_returned=n_returned,
            n_on_time=n_on_time,
            median_transit_seconds=median,
        )
    return out


def rank_by_on_time(
    cards: dict[Carrier, CarrierScorecard], min_volume: int = 10
) -> list[CarrierScorecard]:
    """Order carriers by on-time-percentage desc, filtered to ``min_volume``.

    The volume filter prevents a carrier with 1 delivery and 100%
    on-time from out-ranking a carrier with 1000 deliveries and 95%
    on-time.
    """
    if min_volume < 0:
        raise ValueError("min_volume must be >= 0")
    items = [c for c in cards.values() if c.n_delivered >= min_volume]
    items.sort(key=lambda c: (-c.on_time_pct, c.carrier.value))
    return items


__all__ = ["CarrierScorecard", "carrier_scorecards", "rank_by_on_time"]
