"""VN ride-hailing schema — Trip lifecycle + fare breakdown + settlements.

Models the core entities in a Vietnamese ride-hailing pipeline. The
domain has three flavours of service (CAR / BIKE / DELIVERY), four
active commission-based operators (Grab, Be, Xanh SM, Maxim) — Gojek
exited Vietnam in September 2024 — and a state machine that admits
both happy-path completions and rider/driver cancellations.

All money is **integer VND** (no Decimal, no float drift). All
timestamps are tz-aware in ``VN_TZ`` (UTC+7). Distances are
**centimetres** (avoiding km / metres precision quirks in tests),
durations are **seconds**.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))


class ServiceType(str, Enum):
    """Three service flavours covering ~99% of operator volume."""

    CAR = "CAR"  # 4-seat / 7-seat sedan/SUV
    BIKE = "BIKE"  # motorbike (xe ôm công nghệ)
    DELIVERY = "DELIVERY"  # food / parcel / courier


class TripState(str, Enum):
    """Trip lifecycle. NO_DRIVER and CANCELLED are terminal failures."""

    REQUESTED = "REQUESTED"  # rider submitted, awaiting match
    ASSIGNED = "ASSIGNED"  # driver matched, en route to pickup
    ARRIVING = "ARRIVING"  # driver < 5 min from pickup
    PICKED_UP = "PICKED_UP"  # rider on board (ON_TRIP)
    COMPLETED = "COMPLETED"  # trip ended at dropoff
    CANCELLED = "CANCELLED"  # cancelled by rider or driver
    NO_DRIVER = "NO_DRIVER"  # no match within search window


class PaymentMethod(str, Enum):
    """Five settlement modes."""

    CASH = "CASH"  # rider pays driver directly
    EWALLET = "EWALLET"  # MoMo / ZaloPay / ShopeePay
    BANK_CARD = "BANK_CARD"  # in-app card on file
    CORPORATE = "CORPORATE"  # company-billed (B4B)
    VOUCHER = "VOUCHER"  # promo code / credit


class CancelledBy(str, Enum):
    """Three possible cancellation actors."""

    RIDER = "RIDER"
    DRIVER = "DRIVER"
    SYSTEM = "SYSTEM"  # auto-cancel after timeout


@dataclass(frozen=True, slots=True)
class FareBreakdown:
    """The four components of a final fare, all integer VND.

    ``total_vnd = base_vnd + distance_vnd + duration_vnd + booking_vnd``
    times the surge multiplier (encoded into the individual VND
    amounts so the breakdown adds up exactly).
    """

    base_vnd: int  # flat starting fee
    distance_vnd: int  # per-km × km_travelled × surge
    duration_vnd: int  # per-min × min_travelled × surge
    booking_vnd: int  # platform booking fee (flat)
    surge_multiplier_bps: int = 10_000  # 10_000 bps = 1.0× (no surge)

    def __post_init__(self) -> None:
        for name, val in (
            ("base_vnd", self.base_vnd),
            ("distance_vnd", self.distance_vnd),
            ("duration_vnd", self.duration_vnd),
            ("booking_vnd", self.booking_vnd),
        ):
            if val < 0:
                raise ValueError(f"{name} must be >= 0, got {val}")
        if self.surge_multiplier_bps < 10_000:
            raise ValueError(
                f"surge_multiplier_bps must be >= 10_000 (1.0×), "
                f"got {self.surge_multiplier_bps}",
            )

    @property
    def total_vnd(self) -> int:
        """Final amount the rider pays."""
        return self.base_vnd + self.distance_vnd + self.duration_vnd + self.booking_vnd

    @property
    def surge_multiplier(self) -> float:
        """The surge multiplier as a human-friendly float (e.g. 1.4×)."""
        return self.surge_multiplier_bps / 10_000


@dataclass(frozen=True, slots=True)
class Trip:
    """One ride-hailing trip — request to terminal state.

    ``distance_cm`` and ``duration_seconds`` are the *realised*
    distance/duration after pickup; pre-pickup is not billable.
    ``cancelled_by`` is set iff ``state is CANCELLED`` or ``NO_DRIVER``.
    """

    trip_id: str
    operator: str  # operator abbreviation (GRAB/BE/...)
    city: str  # 3-letter VN city code (SGN/HAN/...)
    service: ServiceType
    rider_id: str
    driver_id: str  # "" if NO_DRIVER
    state: TripState
    requested_at: datetime
    completed_at: datetime | None = None  # set iff state in {COMPLETED, CANCELLED, NO_DRIVER}
    distance_cm: int = 0  # billable distance, cm
    duration_seconds: int = 0  # billable time, seconds
    fare: FareBreakdown | None = None  # None iff state not COMPLETED
    payment_method: PaymentMethod = PaymentMethod.CASH
    cancelled_by: CancelledBy | None = None

    def __post_init__(self) -> None:
        if not self.trip_id:
            raise ValueError("trip_id must be non-empty")
        if not self.rider_id:
            raise ValueError("rider_id must be non-empty")
        if not self.operator:
            raise ValueError("operator must be non-empty")
        if not self.city:
            raise ValueError("city must be non-empty")
        if self.requested_at.tzinfo is None:
            raise ValueError("requested_at must be timezone-aware")
        if self.completed_at is not None and self.completed_at.tzinfo is None:
            raise ValueError("completed_at must be timezone-aware")
        if self.distance_cm < 0:
            raise ValueError(f"distance_cm must be >= 0, got {self.distance_cm}")
        if self.duration_seconds < 0:
            raise ValueError(
                f"duration_seconds must be >= 0, got {self.duration_seconds}",
            )
        # Terminal-state invariants.
        if self.state is TripState.COMPLETED:
            if self.fare is None:
                raise ValueError("COMPLETED trip must have a fare")
            if self.driver_id == "":
                raise ValueError("COMPLETED trip must have a driver_id")
            if self.completed_at is None:
                raise ValueError("COMPLETED trip must have completed_at")
        elif self.state in {TripState.CANCELLED, TripState.NO_DRIVER}:
            if self.fare is not None:
                raise ValueError(
                    f"{self.state.value} trip must not have a fare",
                )
            if self.cancelled_by is None:
                raise ValueError(
                    f"{self.state.value} trip must record cancelled_by",
                )
        elif self.fare is not None:
            raise ValueError(
                f"non-terminal trip (state={self.state.value}) must not have a fare",
            )

    @property
    def distance_km(self) -> float:
        return self.distance_cm / 100_000

    @property
    def duration_minutes(self) -> float:
        return self.duration_seconds / 60


@dataclass(frozen=True, slots=True)
class DriverSettlement:
    """Daily per-driver rollup — what the operator pays the driver."""

    driver_id: str
    operator: str
    date: str  # ISO YYYY-MM-DD
    n_completed_trips: int
    n_cancelled_trips: int
    gross_revenue_vnd: int  # sum of fares on COMPLETED trips
    commission_vnd: int  # operator's cut
    cash_collected_vnd: int  # rider→driver cash already in hand
    net_payable_vnd: int  # what the operator owes / claws back

    def __post_init__(self) -> None:
        for name, val in (
            ("n_completed_trips", self.n_completed_trips),
            ("n_cancelled_trips", self.n_cancelled_trips),
            ("gross_revenue_vnd", self.gross_revenue_vnd),
            ("commission_vnd", self.commission_vnd),
            ("cash_collected_vnd", self.cash_collected_vnd),
        ):
            if val < 0:
                raise ValueError(f"{name} must be >= 0, got {val}")

    @property
    def cancellation_rate(self) -> float:
        total = self.n_completed_trips + self.n_cancelled_trips
        return self.n_cancelled_trips / total if total > 0 else 0.0


__all__ = [
    "VN_TZ",
    "CancelledBy",
    "DriverSettlement",
    "FareBreakdown",
    "PaymentMethod",
    "ServiceType",
    "Trip",
    "TripState",
]
