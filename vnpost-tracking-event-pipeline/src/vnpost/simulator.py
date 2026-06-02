"""Seeded synthetic courier tracking-event stream.

Generates realistic VN courier scan streams with five trip outcomes:

| Outcome              | Default mix |
| -------------------- | ----------- |
| delivered normally   | 80%         |
| delivered late       | 8%          |
| returned to sender   | 5%          |
| scan-skipping fraud  | 2%          |
| abnormal hub dwell   | 3%          |
| exception / pending  | 2%          |

Each parcel walks a realistic hub network: origin courier hub →
gateway → national sortation center → destination gateway → dest
hub → last-mile.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from vnpost.couriers import sla_hours
from vnpost.hubs import all_hubs, gateways
from vnpost.schema import VN_TZ, CourierCode, ParcelEvent, ParcelEventKind

if TYPE_CHECKING:
    from collections.abc import Callable

    _EidFn = Callable[[], str]


def generate(
    *,
    n_parcels: int = 200,
    base_time: datetime | None = None,
    delivered_fraction: float = 0.80,
    late_fraction: float = 0.08,
    returned_fraction: float = 0.05,
    scan_skipping_fraction: float = 0.02,
    abnormal_dwell_fraction: float = 0.03,
    seed: int = 0,
) -> list[ParcelEvent]:
    """Generate a synthetic tracking event stream over ``n_parcels`` parcels."""
    fractions = (
        delivered_fraction,
        late_fraction,
        returned_fraction,
        scan_skipping_fraction,
        abnormal_dwell_fraction,
    )
    if any(not 0 <= f <= 1 for f in fractions):
        raise ValueError("each fraction must be in [0, 1]")
    if sum(fractions) > 1.0 + 1e-9:
        raise ValueError(f"fractions sum to {sum(fractions)} > 1.0")
    if n_parcels < 0:
        raise ValueError("n_parcels must be >= 0")

    rng = random.Random(seed)
    base = base_time or datetime(2026, 5, 1, 8, 0, 0, tzinfo=VN_TZ)
    couriers = list(CourierCode)
    hubs = list(all_hubs())
    gateway_hubs = gateways()

    events: list[ParcelEvent] = []
    counter = 0

    def _eid() -> str:
        nonlocal counter
        eid = f"E-{counter:08d}"
        counter += 1
        return eid

    cum = (
        delivered_fraction,
        delivered_fraction + late_fraction,
        delivered_fraction + late_fraction + returned_fraction,
        delivered_fraction + late_fraction + returned_fraction + scan_skipping_fraction,
        delivered_fraction
        + late_fraction
        + returned_fraction
        + scan_skipping_fraction
        + abnormal_dwell_fraction,
    )
    for i in range(n_parcels):
        tracking_id = f"T-{i:08d}"
        courier = rng.choice(couriers)
        origin_hub = rng.choice(hubs)
        dest_hub_candidates = [h for h in hubs if h.city != origin_hub.city]
        dest_hub = rng.choice(dest_hub_candidates) if dest_hub_candidates else origin_hub
        same_city = origin_hub.city == dest_hub.city
        request_time = base + timedelta(
            days=rng.randint(0, 14),
            hours=rng.randint(0, 23),
        )
        target_h = sla_hours(
            courier,
            origin_city=origin_hub.city,
            dest_city=dest_hub.city,
        )

        # Walk the full trip first.
        gw_origin = rng.choice(
            [g for g in gateway_hubs if g.city == origin_hub.city] or gateway_hubs
        )
        gw_dest = rng.choice([g for g in gateway_hubs if g.city == dest_hub.city] or gateway_hubs)

        r = rng.random()
        if r < cum[0]:
            _emit_normal(
                events,
                _eid,
                tracking_id,
                courier,
                request_time,
                origin_hub.code,
                gw_origin.code,
                gw_dest.code,
                dest_hub.code,
                target_h,
                late=False,
                same_city=same_city,
                rng=rng,
            )
        elif r < cum[1]:
            _emit_normal(
                events,
                _eid,
                tracking_id,
                courier,
                request_time,
                origin_hub.code,
                gw_origin.code,
                gw_dest.code,
                dest_hub.code,
                target_h,
                late=True,
                same_city=same_city,
                rng=rng,
            )
        elif r < cum[2]:
            _emit_returned(
                events,
                _eid,
                tracking_id,
                courier,
                request_time,
                origin_hub.code,
                gw_origin.code,
                gw_dest.code,
                dest_hub.code,
                target_h,
                rng,
            )
        elif r < cum[3]:
            _emit_scan_skip(
                events,
                _eid,
                tracking_id,
                courier,
                request_time,
                origin_hub.code,
                dest_hub.code,
                target_h,
                rng,
            )
        elif r < cum[4]:
            _emit_abnormal_dwell(
                events,
                _eid,
                tracking_id,
                courier,
                request_time,
                origin_hub.code,
                gw_origin.code,
                gw_dest.code,
                dest_hub.code,
                target_h,
                rng,
            )
        else:
            # exception / pending — single CREATED + EXCEPTION
            events.append(
                ParcelEvent(
                    event_id=_eid(),
                    tracking_id=tracking_id,
                    courier=courier,
                    kind=ParcelEventKind.CREATED,
                    occurred_at=request_time,
                    hub_code="",
                )
            )
            events.append(
                ParcelEvent(
                    event_id=_eid(),
                    tracking_id=tracking_id,
                    courier=courier,
                    kind=ParcelEventKind.EXCEPTION,
                    occurred_at=request_time + timedelta(hours=2),
                    hub_code=origin_hub.code,
                    note="bad recipient phone",
                )
            )
    events.sort(key=lambda e: (e.occurred_at, e.event_id))
    return events


def _emit_normal(
    events: list[ParcelEvent],
    eid: _EidFn,
    tracking_id: str,
    courier: CourierCode,
    req_time: datetime,
    origin_hub: str,
    gw_origin: str,
    gw_dest: str,
    dest_hub: str,
    target_h: int,
    *,
    late: bool,
    same_city: bool,
    rng: random.Random,
) -> None:
    """Emit a healthy delivered parcel scan sequence."""
    elapsed_h = (
        rng.randint(int(target_h * 0.6), target_h - 1)
        if not late
        else rng.randint(target_h + 4, target_h * 2)
    )
    # Spread the scans evenly within the elapsed window.
    t = req_time
    events.append(
        ParcelEvent(
            event_id=eid(),
            tracking_id=tracking_id,
            courier=courier,
            kind=ParcelEventKind.CREATED,
            occurred_at=t,
            hub_code="",
        )
    )
    t += timedelta(hours=rng.randint(1, 4))
    events.append(
        ParcelEvent(
            event_id=eid(),
            tracking_id=tracking_id,
            courier=courier,
            kind=ParcelEventKind.PICKED_UP,
            occurred_at=t,
            hub_code="",
        )
    )
    t += timedelta(hours=rng.randint(2, 6))
    events.append(
        ParcelEvent(
            event_id=eid(),
            tracking_id=tracking_id,
            courier=courier,
            kind=ParcelEventKind.AT_HUB,
            occurred_at=t,
            hub_code=origin_hub,
        )
    )
    if not same_city:
        t += timedelta(hours=rng.randint(4, 12))
        events.append(
            ParcelEvent(
                event_id=eid(),
                tracking_id=tracking_id,
                courier=courier,
                kind=ParcelEventKind.IN_TRANSIT,
                occurred_at=t,
                hub_code=gw_origin,
            )
        )
        t += timedelta(hours=rng.randint(8, 24))
        events.append(
            ParcelEvent(
                event_id=eid(),
                tracking_id=tracking_id,
                courier=courier,
                kind=ParcelEventKind.AT_HUB,
                occurred_at=t,
                hub_code=gw_dest,
            )
        )
    t += timedelta(hours=max(2, elapsed_h - int((t - req_time).total_seconds() / 3600) - 4))
    events.append(
        ParcelEvent(
            event_id=eid(),
            tracking_id=tracking_id,
            courier=courier,
            kind=ParcelEventKind.OUT_FOR_DELIVERY,
            occurred_at=t,
            hub_code=dest_hub,
        )
    )
    t += timedelta(hours=rng.randint(2, 8))
    events.append(
        ParcelEvent(
            event_id=eid(),
            tracking_id=tracking_id,
            courier=courier,
            kind=ParcelEventKind.DELIVERED,
            occurred_at=t,
            hub_code="",
        )
    )


def _emit_returned(
    events: list[ParcelEvent],
    eid: _EidFn,
    tracking_id: str,
    courier: CourierCode,
    req_time: datetime,
    origin_hub: str,
    gw_origin: str,
    gw_dest: str,
    dest_hub: str,
    target_h: int,
    rng: random.Random,
) -> None:
    """Emit a parcel returned to sender after OUT_FOR_DELIVERY."""
    t = req_time
    events.append(
        ParcelEvent(
            event_id=eid(),
            tracking_id=tracking_id,
            courier=courier,
            kind=ParcelEventKind.CREATED,
            occurred_at=t,
        )
    )
    t += timedelta(hours=rng.randint(1, 4))
    events.append(
        ParcelEvent(
            event_id=eid(),
            tracking_id=tracking_id,
            courier=courier,
            kind=ParcelEventKind.PICKED_UP,
            occurred_at=t,
        )
    )
    t += timedelta(hours=rng.randint(4, 12))
    events.append(
        ParcelEvent(
            event_id=eid(),
            tracking_id=tracking_id,
            courier=courier,
            kind=ParcelEventKind.AT_HUB,
            occurred_at=t,
            hub_code=origin_hub,
        )
    )
    t += timedelta(hours=rng.randint(8, 24))
    events.append(
        ParcelEvent(
            event_id=eid(),
            tracking_id=tracking_id,
            courier=courier,
            kind=ParcelEventKind.AT_HUB,
            occurred_at=t,
            hub_code=gw_dest,
        )
    )
    t += timedelta(hours=rng.randint(4, 8))
    events.append(
        ParcelEvent(
            event_id=eid(),
            tracking_id=tracking_id,
            courier=courier,
            kind=ParcelEventKind.OUT_FOR_DELIVERY,
            occurred_at=t,
            hub_code=dest_hub,
        )
    )
    t += timedelta(hours=rng.randint(2, 6))
    events.append(
        ParcelEvent(
            event_id=eid(),
            tracking_id=tracking_id,
            courier=courier,
            kind=ParcelEventKind.RETURN_TO_SENDER,
            occurred_at=t,
            note="recipient unreachable",
        )
    )


def _emit_scan_skip(
    events: list[ParcelEvent],
    eid: _EidFn,
    tracking_id: str,
    courier: CourierCode,
    req_time: datetime,
    origin_hub: str,
    dest_hub: str,
    target_h: int,
    rng: random.Random,
) -> None:
    """Emit a fraud-pattern parcel: 3 scans only for an inter-city journey.

    The "scan skip" pattern in real life often shows up as PICKED_UP →
    OUT_FOR_DELIVERY → DELIVERED with no AT_HUB or IN_TRANSIT scans
    in between — either the courier failed to scan en route or the
    driver faked the delivery to clear a backlog. We omit CREATED so
    the total is 3, below the inter-city threshold of 4.
    """
    t = req_time
    events.append(
        ParcelEvent(
            event_id=eid(),
            tracking_id=tracking_id,
            courier=courier,
            kind=ParcelEventKind.PICKED_UP,
            occurred_at=t,
            hub_code=origin_hub,
        )
    )
    t += timedelta(hours=rng.randint(2, 8))
    events.append(
        ParcelEvent(
            event_id=eid(),
            tracking_id=tracking_id,
            courier=courier,
            kind=ParcelEventKind.OUT_FOR_DELIVERY,
            occurred_at=t,
            hub_code=dest_hub,
        )
    )
    t += timedelta(hours=1)
    events.append(
        ParcelEvent(
            event_id=eid(),
            tracking_id=tracking_id,
            courier=courier,
            kind=ParcelEventKind.DELIVERED,
            occurred_at=t,
        )
    )


def _emit_abnormal_dwell(
    events: list[ParcelEvent],
    eid: _EidFn,
    tracking_id: str,
    courier: CourierCode,
    req_time: datetime,
    origin_hub: str,
    gw_origin: str,
    gw_dest: str,
    dest_hub: str,
    target_h: int,
    rng: random.Random,
) -> None:
    """Emit a delivered parcel that sat at an intermediate hub far too long."""
    t = req_time
    events.append(
        ParcelEvent(
            event_id=eid(),
            tracking_id=tracking_id,
            courier=courier,
            kind=ParcelEventKind.CREATED,
            occurred_at=t,
        )
    )
    t += timedelta(hours=rng.randint(1, 3))
    events.append(
        ParcelEvent(
            event_id=eid(),
            tracking_id=tracking_id,
            courier=courier,
            kind=ParcelEventKind.PICKED_UP,
            occurred_at=t,
        )
    )
    t += timedelta(hours=rng.randint(2, 6))
    events.append(
        ParcelEvent(
            event_id=eid(),
            tracking_id=tracking_id,
            courier=courier,
            kind=ParcelEventKind.AT_HUB,
            occurred_at=t,
            hub_code=origin_hub,
        )
    )
    # Long dwell at the gateway origin
    t += timedelta(hours=rng.randint(72, 168))  # 3-7 days stuck
    events.append(
        ParcelEvent(
            event_id=eid(),
            tracking_id=tracking_id,
            courier=courier,
            kind=ParcelEventKind.AT_HUB,
            occurred_at=t,
            hub_code=gw_origin,
            note="customs hold",
        )
    )
    t += timedelta(hours=rng.randint(12, 24))
    events.append(
        ParcelEvent(
            event_id=eid(),
            tracking_id=tracking_id,
            courier=courier,
            kind=ParcelEventKind.OUT_FOR_DELIVERY,
            occurred_at=t,
            hub_code=dest_hub,
        )
    )
    t += timedelta(hours=rng.randint(2, 6))
    events.append(
        ParcelEvent(
            event_id=eid(),
            tracking_id=tracking_id,
            courier=courier,
            kind=ParcelEventKind.DELIVERED,
            occurred_at=t,
        )
    )


__all__ = ["generate"]
