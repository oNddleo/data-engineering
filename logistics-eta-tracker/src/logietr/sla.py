"""SLA breach detector.

Two kinds of breach are surfaced to ops:

* **OVERDUE** — non-terminal shipment whose ``promised_at`` is in
  the past relative to ``now``. The carrier missed the SLA they
  themselves quoted.
* **STUCK** — shipment that's been in the same non-terminal state
  for longer than the configured threshold. Common in VN logistics
  when a parcel gets stuck at a regional hub during Tết.

Both breach types are pure functions over ``ShipmentStatus`` + a
``now`` timestamp injected by the caller — no global clocks, so
tests can pin time deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from logietr.schema import ShipmentState
    from logietr.tracker import ShipmentStatus


class BreachKind(str, Enum):
    OVERDUE = "OVERDUE"
    STUCK = "STUCK"


@dataclass(frozen=True, slots=True)
class Breach:
    """One ops-actionable SLA violation."""

    kind: BreachKind
    shipment_id: str
    state: ShipmentState
    detected_at: datetime
    overdue_seconds: int  # seconds past the deadline (OVERDUE) or threshold (STUCK)

    @property
    def overdue_hours(self) -> float:
        return self.overdue_seconds / 3600


def find_overdue(statuses: dict[str, ShipmentStatus], now: datetime) -> list[Breach]:
    """Non-terminal shipments whose ``promised_at`` is in the past."""
    out: list[Breach] = []
    for st in statuses.values():
        if st.is_terminal:
            continue
        if now > st.shipment.promised_at:
            out.append(
                Breach(
                    kind=BreachKind.OVERDUE,
                    shipment_id=st.shipment.shipment_id,
                    state=st.state,
                    detected_at=now,
                    overdue_seconds=int((now - st.shipment.promised_at).total_seconds()),
                )
            )
    return sorted(out, key=lambda b: (-b.overdue_seconds, b.shipment_id))


def find_stuck(
    statuses: dict[str, ShipmentStatus],
    now: datetime,
    stuck_after: timedelta = timedelta(hours=24),
) -> list[Breach]:
    """Shipments that haven't transitioned in longer than ``stuck_after``.

    Skips terminal states and skips ``CREATED`` shipments where no
    event has fired yet but the carrier hasn't picked up either —
    those are the seller's problem, not the carrier's.
    """
    if stuck_after.total_seconds() <= 0:
        raise ValueError("stuck_after must be positive")
    out: list[Breach] = []
    for st in statuses.values():
        if st.is_terminal:
            continue
        # Only flag shipments the carrier has acknowledged — at least
        # one event landed (or we'd treat every just-created shipment
        # as stuck).
        if not st.history:
            continue
        gap = now - st.last_event_at
        if gap > stuck_after:
            out.append(
                Breach(
                    kind=BreachKind.STUCK,
                    shipment_id=st.shipment.shipment_id,
                    state=st.state,
                    detected_at=now,
                    overdue_seconds=int((gap - stuck_after).total_seconds()),
                )
            )
    return sorted(out, key=lambda b: (-b.overdue_seconds, b.shipment_id))


__all__ = ["Breach", "BreachKind", "find_overdue", "find_stuck"]
