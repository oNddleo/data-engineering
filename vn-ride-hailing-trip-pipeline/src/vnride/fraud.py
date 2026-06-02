"""Ride-hailing fraud signals — three patterns operators actually watch.

* **Ghost ride** — a COMPLETED trip with implausibly small distance
  (< 100 m default) AND duration (< 30 s default). The classic
  driver/rider collusion to harvest a promo bonus or run up loyalty
  points. We flag the *trip*, not the driver — context for triage.

* **Cancellation abuse** — a driver whose cancellation rate (cancelled /
  (completed + cancelled)) crosses ``min_cancel_rate`` (default 0.50)
  while having ≥ ``min_trips`` total trips (default 20). Real drivers
  cancel < 10% in normal operation.

* **Surge gaming** — a (rider, driver) pair that has shared
  ≥ ``min_surge_trips`` (default 5) trips, *all* of them during
  surge windows (multiplier > 1.0). High likelihood of off-platform
  coordination to time pickups for inflated fares.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from vnride.schema import TripState

if TYPE_CHECKING:
    from vnride.schema import Trip


class FraudKind(str, Enum):
    """Three fraud-signal types."""

    GHOST_RIDE = "GHOST_RIDE"
    CANCELLATION_ABUSE = "CANCELLATION_ABUSE"
    SURGE_GAMING = "SURGE_GAMING"


@dataclass(frozen=True, slots=True)
class FraudFinding:
    """One ops-actionable fraud signal."""

    kind: FraudKind
    subject_id: str  # trip_id, driver_id, or pair id
    operator: str
    detail: str
    metric: int


def find_ghost_rides(
    trips: list[Trip],
    *,
    max_distance_cm: int = 10_000,  # 100 m
    max_duration_seconds: int = 30,
) -> list[FraudFinding]:
    """Surface trips whose realised distance + duration are implausibly small."""
    if max_distance_cm < 0:
        raise ValueError("max_distance_cm must be >= 0")
    if max_duration_seconds < 0:
        raise ValueError("max_duration_seconds must be >= 0")
    out: list[FraudFinding] = []
    for t in trips:
        if t.state is not TripState.COMPLETED:
            continue
        if t.distance_cm > max_distance_cm:
            continue
        if t.duration_seconds > max_duration_seconds:
            continue
        out.append(
            FraudFinding(
                kind=FraudKind.GHOST_RIDE,
                subject_id=t.trip_id,
                operator=t.operator,
                detail=(
                    f"trip {t.trip_id}: {t.distance_cm} cm in "
                    f"{t.duration_seconds} s ({t.service.value})"
                ),
                metric=t.distance_cm + t.duration_seconds,
            )
        )
    out.sort(key=lambda f: (f.metric, f.subject_id))
    return out


def find_cancellation_abuse(
    trips: list[Trip],
    *,
    min_trips: int = 20,
    min_cancel_rate: float = 0.50,
) -> list[FraudFinding]:
    """Surface drivers with high cancel rates over enough sample size."""
    if min_trips < 1:
        raise ValueError("min_trips must be >= 1")
    if not 0 < min_cancel_rate <= 1:
        raise ValueError("min_cancel_rate must be in (0, 1]")
    per_driver: dict[tuple[str, str], tuple[int, int]] = defaultdict(
        lambda: (0, 0),
    )
    for t in trips:
        if not t.driver_id:
            continue
        if t.state not in {TripState.COMPLETED, TripState.CANCELLED}:
            continue
        comp, canc = per_driver[(t.driver_id, t.operator)]
        if t.state is TripState.COMPLETED:
            per_driver[(t.driver_id, t.operator)] = (comp + 1, canc)
        else:
            per_driver[(t.driver_id, t.operator)] = (comp, canc + 1)
    out: list[FraudFinding] = []
    for (driver_id, operator), (comp, canc) in per_driver.items():
        total = comp + canc
        if total < min_trips:
            continue
        rate = canc / total if total > 0 else 0.0
        if rate >= min_cancel_rate:
            out.append(
                FraudFinding(
                    kind=FraudKind.CANCELLATION_ABUSE,
                    subject_id=driver_id,
                    operator=operator,
                    detail=(
                        f"driver {driver_id}: {canc}/{total} cancelled " f"({rate * 100:.0f}%)"
                    ),
                    metric=int(rate * 100),
                )
            )
    out.sort(key=lambda f: (-f.metric, f.subject_id))
    return out


def find_surge_gaming(
    trips: list[Trip],
    *,
    min_surge_trips: int = 5,
) -> list[FraudFinding]:
    """Surface (rider, driver) pairs sharing many surge-only trips."""
    if min_surge_trips < 2:
        raise ValueError("min_surge_trips must be >= 2")
    per_pair: dict[tuple[str, str, str], list[Trip]] = defaultdict(list)
    for t in trips:
        if t.state is not TripState.COMPLETED:
            continue
        if not t.driver_id:
            continue
        per_pair[(t.rider_id, t.driver_id, t.operator)].append(t)
    out: list[FraudFinding] = []
    for (rider, driver, operator), shared in per_pair.items():
        if len(shared) < min_surge_trips:
            continue
        # Every shared trip must be in a surge window (multiplier > 1.0).
        all_surge = all(t.fare is not None and t.fare.surge_multiplier_bps > 10_000 for t in shared)
        if not all_surge:
            continue
        out.append(
            FraudFinding(
                kind=FraudKind.SURGE_GAMING,
                subject_id=f"{rider}|{driver}",
                operator=operator,
                detail=(f"rider {rider} ↔ driver {driver}: {len(shared)} " f"surge-only trips"),
                metric=len(shared),
            )
        )
    out.sort(key=lambda f: (-f.metric, f.subject_id))
    return out


__all__ = [
    "FraudFinding",
    "FraudKind",
    "find_cancellation_abuse",
    "find_ghost_rides",
    "find_surge_gaming",
]
