"""Shipment schema + carrier registry + delivery-state machine.

Modelled on the four VN 3PLs that dominate marketplace fulfilment:

* **GHN** (Giao Hàng Nhanh) — Shopee's primary partner.
* **GHTK** (Giao Hàng Tiết Kiệm) — Tiki / Lazada / SME.
* **VTP** (Viettel Post) — nationwide last-mile, telco-backed.
* **VNPOST** (Vietnam Post) — government postal service.

The delivery-state machine has 7 nodes and the legal transitions baked
in as a frozenset. Production carriers can emit out-of-order or
duplicate events, so the validator only rejects **impossible**
transitions (e.g. ``DELIVERED → IN_TRANSIT``), not idempotent re-emits
of the current state.

| State              | Meaning                                          |
| ------------------ | ------------------------------------------------ |
| ``CREATED``        | Order placed, carrier not yet picked up.         |
| ``PICKED_UP``      | First-mile pickup done; in carrier's hands.      |
| ``IN_TRANSIT``     | Between hubs; long-haul leg.                     |
| ``AT_HUB``         | Sorted at a hub awaiting next leg.               |
| ``OUT_FOR_DELIVERY``| Driver dispatched on last mile.                 |
| ``DELIVERED``      | Terminal. Customer signed / left at door.        |
| ``FAILED``         | Terminal. Customer unreachable after retries.    |
| ``RETURNED``       | Terminal. Refused / returned to seller.          |
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))


class Carrier(str, Enum):
    """Big-four VN 3PLs. Add more by extending — downstream is enum-driven."""

    GHN = "GHN"
    GHTK = "GHTK"
    VTP = "VTP"
    VNPOST = "VNPOST"


class ShipmentState(str, Enum):
    """Delivery-state machine nodes."""

    CREATED = "CREATED"
    PICKED_UP = "PICKED_UP"
    IN_TRANSIT = "IN_TRANSIT"
    AT_HUB = "AT_HUB"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    RETURNED = "RETURNED"


TERMINAL_STATES: frozenset[ShipmentState] = frozenset(
    {ShipmentState.DELIVERED, ShipmentState.FAILED, ShipmentState.RETURNED}
)


# Legal forward transitions. Reflexive transitions (idempotent re-emit
# of the current state) are permitted separately by the validator.
_LEGAL: frozenset[tuple[ShipmentState, ShipmentState]] = frozenset(
    {
        (ShipmentState.CREATED, ShipmentState.PICKED_UP),
        (ShipmentState.CREATED, ShipmentState.FAILED),  # pickup failed
        (ShipmentState.PICKED_UP, ShipmentState.IN_TRANSIT),
        (ShipmentState.PICKED_UP, ShipmentState.AT_HUB),
        (ShipmentState.IN_TRANSIT, ShipmentState.AT_HUB),
        (ShipmentState.IN_TRANSIT, ShipmentState.OUT_FOR_DELIVERY),
        (ShipmentState.AT_HUB, ShipmentState.IN_TRANSIT),
        (ShipmentState.AT_HUB, ShipmentState.OUT_FOR_DELIVERY),
        (ShipmentState.OUT_FOR_DELIVERY, ShipmentState.DELIVERED),
        (ShipmentState.OUT_FOR_DELIVERY, ShipmentState.FAILED),  # customer not home
        (ShipmentState.OUT_FOR_DELIVERY, ShipmentState.AT_HUB),  # retry tomorrow
        (ShipmentState.FAILED, ShipmentState.RETURNED),
        (ShipmentState.FAILED, ShipmentState.OUT_FOR_DELIVERY),  # one more try
    }
)


def is_legal_transition(prev: ShipmentState, nxt: ShipmentState) -> bool:
    """``True`` if ``prev → nxt`` is a legal forward step or an idempotent re-emit."""
    if prev == nxt:
        return True
    return (prev, nxt) in _LEGAL


@dataclass(frozen=True, slots=True)
class Shipment:
    """Manifest record — what we know at order time."""

    shipment_id: str
    order_id: str
    carrier: Carrier
    origin_district: str
    dest_district: str
    weight_g: int
    declared_value_vnd: int
    promised_at: datetime  # SLA deadline (carrier's quoted delivery time)
    created_at: datetime

    def __post_init__(self) -> None:
        if not self.shipment_id:
            raise ValueError("shipment_id must be non-empty")
        if not self.order_id:
            raise ValueError("order_id must be non-empty")
        if not self.origin_district:
            raise ValueError("origin_district must be non-empty")
        if not self.dest_district:
            raise ValueError("dest_district must be non-empty")
        if self.weight_g <= 0:
            raise ValueError(f"weight_g must be > 0, got {self.weight_g}")
        if self.declared_value_vnd < 0:
            raise ValueError(f"declared_value_vnd must be >= 0, got {self.declared_value_vnd}")
        if self.promised_at.tzinfo is None:
            raise ValueError("promised_at must be timezone-aware")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")
        if self.promised_at < self.created_at:
            raise ValueError(
                f"promised_at ({self.promised_at}) must be >= created_at ({self.created_at})"
            )


@dataclass(frozen=True, slots=True)
class TrackingEvent:
    """One state transition emitted by a carrier webhook / poller."""

    event_id: str
    shipment_id: str
    state: ShipmentState
    occurred_at: datetime
    hub_code: str | None  # only set for IN_TRANSIT / AT_HUB / OUT_FOR_DELIVERY

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id must be non-empty")
        if not self.shipment_id:
            raise ValueError("shipment_id must be non-empty")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        if self.hub_code is not None and not self.hub_code:
            raise ValueError("hub_code, if present, must be non-empty")


def lane_key(origin: str, dest: str, carrier: Carrier) -> tuple[str, str, Carrier]:
    """The cardinality unit for ETA stats: an O-D-carrier triple."""
    return (origin, dest, carrier)


__all__ = [
    "TERMINAL_STATES",
    "VN_TZ",
    "Carrier",
    "Shipment",
    "ShipmentState",
    "TrackingEvent",
    "is_legal_transition",
    "lane_key",
]
