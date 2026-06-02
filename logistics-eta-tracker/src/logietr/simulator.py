"""Seeded synthetic shipment + event streams.

Produces a coherent batch where:

* every event references a real shipment;
* events follow a legal state-machine path;
* per-carrier transit times follow distinct distributions
  (GHN ~ 24h p50, GHTK ~ 36h, VTP ~ 30h, VNPOST ~ 48h), so the
  leaderboard and lane stats have something to rank;
* a configurable ``failure_rate`` fraction never reaches
  ``DELIVERED`` — they end in ``FAILED`` or ``RETURNED``.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta

from logietr.schema import VN_TZ, Carrier, Shipment, ShipmentState, TrackingEvent

_DEFAULT_BASE_TS = datetime(2026, 5, 1, 8, 0, 0, tzinfo=VN_TZ)

# VN districts the marketplace ships to most. Roughly N-Central-S buckets.
_DISTRICTS = (
    "HCMC_District1",
    "HCMC_District7",
    "HCMC_ThuDuc",
    "HN_HoanKiem",
    "HN_CauGiay",
    "HN_HaDong",
    "DN_HaiChau",
    "DN_SonTra",
    "CT_NinhKieu",
    "HP_LeChan",
)


# Carrier base p50 transit time + intra-carrier variance σ (both seconds).
_CARRIER_BASE: dict[Carrier, tuple[int, int]] = {
    Carrier.GHN: (24 * 3600, 6 * 3600),
    Carrier.GHTK: (36 * 3600, 9 * 3600),
    Carrier.VTP: (30 * 3600, 7 * 3600),
    Carrier.VNPOST: (48 * 3600, 12 * 3600),
}


_HAPPY_PATH: tuple[ShipmentState, ...] = (
    ShipmentState.PICKED_UP,
    ShipmentState.IN_TRANSIT,
    ShipmentState.AT_HUB,
    ShipmentState.OUT_FOR_DELIVERY,
    ShipmentState.DELIVERED,
)


def generate(
    *,
    n_shipments: int = 200,
    failure_rate: float = 0.05,
    pending_fraction: float = 0.20,
    seed: int = 0,
    base_time: datetime | None = None,
) -> tuple[list[Shipment], list[TrackingEvent]]:
    """Generate shipments + their event histories.

    ``pending_fraction`` controls how many shipments stop mid-journey
    (truncated event histories) so the ETA + SLA paths have in-flight
    work to predict on. Without this, every shipment terminates and
    the ETA predictor has no pending input.
    """
    if n_shipments < 1:
        raise ValueError("n_shipments must be >= 1")
    if not 0.0 <= failure_rate <= 1.0:
        raise ValueError("failure_rate must be in [0, 1]")
    if not 0.0 <= pending_fraction <= 1.0:
        raise ValueError("pending_fraction must be in [0, 1]")
    rng = random.Random(seed)
    base = base_time or _DEFAULT_BASE_TS

    shipments: list[Shipment] = []
    events: list[TrackingEvent] = []
    event_counter = 0
    for i in range(n_shipments):
        carrier = rng.choice(list(Carrier))
        origin = rng.choice(_DISTRICTS)
        dest = rng.choice([d for d in _DISTRICTS if d != origin])
        created = base + timedelta(minutes=i * 17)
        p50, sigma = _CARRIER_BASE[carrier]
        # Carrier's SLA quote: p50 + 12h cushion.
        promised = created + timedelta(seconds=p50 + 12 * 3600)
        ship = Shipment(
            shipment_id=f"S-{i:06d}",
            order_id=f"O-{i:06d}",
            carrier=carrier,
            origin_district=origin,
            dest_district=dest,
            weight_g=rng.choice((300, 500, 800, 1200, 2000)),
            declared_value_vnd=rng.choice((99_000, 199_000, 499_000, 990_000)),
            promised_at=promised,
            created_at=created,
        )
        shipments.append(ship)

        # Emit happy-path or failure path.
        fail = rng.random() < failure_rate
        path = (
            _HAPPY_PATH
            if not fail
            else (
                ShipmentState.PICKED_UP,
                ShipmentState.IN_TRANSIT,
                ShipmentState.OUT_FOR_DELIVERY,
                ShipmentState.FAILED,
                ShipmentState.RETURNED,
            )
        )
        # In-flight shipments emit a prefix of the path only.
        if rng.random() < pending_fraction:
            stop_after = rng.randint(1, max(1, len(path) - 2))
            path = path[:stop_after]
        cursor = created
        for state in path:
            # Each leg takes a fraction of total transit; jitter ±σ.
            leg_seconds = max(
                300,
                int(rng.gauss(p50 / len(_HAPPY_PATH), sigma / len(_HAPPY_PATH))),
            )
            cursor = cursor + timedelta(seconds=leg_seconds)
            hub = None
            if state in (
                ShipmentState.IN_TRANSIT,
                ShipmentState.AT_HUB,
                ShipmentState.OUT_FOR_DELIVERY,
            ):
                hub = f"HUB_{rng.randint(1, 12):02d}"
            events.append(
                TrackingEvent(
                    event_id=f"E-{event_counter:08d}",
                    shipment_id=ship.shipment_id,
                    state=state,
                    occurred_at=cursor,
                    hub_code=hub,
                )
            )
            event_counter += 1

    # Carriers emit events out of order — shuffle 10% of them by ±1 slot
    # to exercise the tracker's resort step.
    for i in range(len(events) - 1):
        if rng.random() < 0.10:
            events[i], events[i + 1] = events[i + 1], events[i]

    return shipments, events


__all__ = ["generate"]
