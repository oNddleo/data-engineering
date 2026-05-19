"""Courier-level fraud detection — two classic patterns.

**Scan-skipping** (a.k.a. "ghost in transit"): a parcel jumps from
PICKED_UP straight to DELIVERED with no intermediate IN_TRANSIT /
AT_HUB scans. Either the courier failed to scan en route (operational
bug) or — more often — a driver is faking a delivery to clear his
backlog. Manifests as ``n_events ≤ 3`` for an inter-city parcel.

**Abnormal dwell**: a parcel sits at a hub for far longer than the
distribution suggests — could be lost inventory, customs hold, or
shipper mishandling. We flag when ``hub_dwell_hours > p95 + 3 *
(p95 - p50)`` (three IQR-like deviations above p95).

Both detectors are pure functions over stitched ``Parcel`` lists +
the original event stream. Output ``FraudFinding`` records that ops
review tools can render directly.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from vnpost.schema import ParcelEventKind, ParcelStatus

if TYPE_CHECKING:
    from vnpost.schema import CourierCode, Parcel, ParcelEvent


class FraudKind(str, Enum):
    """Two surfaced fraud / quality signals."""

    SCAN_SKIPPING = "SCAN_SKIPPING"
    ABNORMAL_DWELL = "ABNORMAL_DWELL"


@dataclass(frozen=True, slots=True)
class FraudFinding:
    """One ops-actionable fraud / quality finding."""

    kind: FraudKind
    courier: CourierCode
    tracking_id: str
    detail: str
    metric: int  # context-dependent (n_events for SCAN_SKIPPING, dwell hours)


def find_scan_skipping(
    parcels: list[Parcel],
    *,
    min_events_inter_city: int = 4,
    min_events_same_city: int = 3,
) -> list[FraudFinding]:
    """Surface delivered parcels with too few scans for their distance class.

    Inter-city parcels (origin city ≠ dest city) need at minimum
    PICKED_UP → IN_TRANSIT → OUT_FOR_DELIVERY → DELIVERED = 4 scans.
    Same-city parcels can legitimately have 3 (PICKED_UP →
    OUT_FOR_DELIVERY → DELIVERED).
    """
    if min_events_inter_city < 2 or min_events_same_city < 2:
        raise ValueError("min_events thresholds must be >= 2")
    out: list[FraudFinding] = []
    for p in parcels:
        if p.status is not ParcelStatus.DELIVERED:
            continue
        origin_city = p.origin_hub.split("-")[0] if p.origin_hub else ""
        dest_city = p.dest_hub.split("-")[0] if p.dest_hub else origin_city
        threshold = min_events_same_city if origin_city == dest_city else min_events_inter_city
        if p.n_events < threshold:
            out.append(
                FraudFinding(
                    kind=FraudKind.SCAN_SKIPPING,
                    courier=p.courier,
                    tracking_id=p.tracking_id,
                    detail=(
                        f"only {p.n_events} scans for "
                        f"{origin_city or '?'}→{dest_city or '?'} (need ≥{threshold})"
                    ),
                    metric=p.n_events,
                )
            )
    out.sort(key=lambda f: (f.courier.value, f.tracking_id))
    return out


def find_abnormal_dwell(
    events: list[ParcelEvent],
    *,
    iqr_multiplier: int = 3,
) -> list[FraudFinding]:
    """Surface tracking IDs whose hub-dwell time is an outlier.

    Algorithm:

    1. For each parcel, compute the time gap between consecutive
       ``AT_HUB`` / ``IN_TRANSIT`` scans (the "dwell" at the
       intermediate hub).
    2. Compute the overall p50 and p95 dwell across the population.
    3. Flag any dwell > p95 + ``iqr_multiplier × (p95 - p50)``.
    """
    if iqr_multiplier < 1:
        raise ValueError("iqr_multiplier must be >= 1")
    # Group events by tracking_id (sorted within).
    per_tracking: dict[str, list[ParcelEvent]] = defaultdict(list)
    for e in events:
        per_tracking[e.tracking_id].append(e)

    # Collect all hub dwells across the population.
    all_dwells: list[int] = []
    per_tracking_dwells: dict[str, list[tuple[int, str]]] = defaultdict(list)
    transit_kinds = (ParcelEventKind.AT_HUB, ParcelEventKind.IN_TRANSIT)
    for tid, group in per_tracking.items():
        sorted_g = sorted(group, key=lambda e: (e.occurred_at, e.event_id))
        prev = None
        for e in sorted_g:
            if e.kind in transit_kinds:
                if prev is not None:
                    h = int((e.occurred_at - prev.occurred_at).total_seconds() // 3600)
                    if h >= 0:
                        all_dwells.append(h)
                        per_tracking_dwells[tid].append((h, e.hub_code or "?"))
                prev = e
            elif e.kind in (ParcelEventKind.PICKED_UP, ParcelEventKind.OUT_FOR_DELIVERY):
                prev = e
            else:
                prev = e
    if not all_dwells:
        return []
    sorted_dwells = sorted(all_dwells)
    p50 = sorted_dwells[len(sorted_dwells) // 2]
    p95 = sorted_dwells[int(round(0.95 * (len(sorted_dwells) - 1)))]
    threshold = p95 + iqr_multiplier * (p95 - p50)
    if threshold <= 0:
        return []

    courier_by_tracking: dict[str, CourierCode] = {
        events_[0].tracking_id: events_[0].courier for events_ in per_tracking.values() if events_
    }
    out: list[FraudFinding] = []
    for tid, dwells in per_tracking_dwells.items():
        for hours, hub in dwells:
            if hours > threshold:
                out.append(
                    FraudFinding(
                        kind=FraudKind.ABNORMAL_DWELL,
                        courier=courier_by_tracking[tid],
                        tracking_id=tid,
                        detail=(
                            f"dwell {hours}h at {hub} " f"(threshold {threshold}h, p95 {p95}h)"
                        ),
                        metric=hours,
                    )
                )
    out.sort(key=lambda f: (-f.metric, f.tracking_id))
    return out


__all__ = [
    "FraudFinding",
    "FraudKind",
    "find_abnormal_dwell",
    "find_scan_skipping",
]
