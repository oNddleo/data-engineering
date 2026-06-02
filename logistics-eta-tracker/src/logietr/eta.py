"""ETA predictor — p50 / p90 transit time per ``(origin, dest, carrier)``.

Builds a lookup of historical delivery durations from completed
shipments, then predicts each in-flight shipment's expected
arrival from its ``created_at`` plus the lane's p50 / p90.

The model is deliberately non-parametric (empirical quantiles, not
a Gaussian fit) because VN logistics distributions are heavy-tailed:
weekend / Tết / monsoon outliers would skew a mean-based estimate
by hours. p50 / p90 are robust.

Lanes with fewer than ``min_samples`` historical observations fall
back to the carrier-wide aggregate; lanes the carrier has never run
fall back to the global p50 / p90 across all completed shipments.
This three-tier fallback is the difference between a useful ETA and
"unknown" on cold-start lanes.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from logietr.schema import Carrier, ShipmentState, lane_key

if TYPE_CHECKING:
    from datetime import datetime

    from logietr.tracker import ShipmentStatus


@dataclass(frozen=True, slots=True)
class LaneStats:
    """Empirical p50 / p90 transit-time (seconds) for one lane."""

    origin: str
    dest: str
    carrier: Carrier
    n_samples: int
    p50_seconds: int
    p90_seconds: int

    @property
    def p50_hours(self) -> float:
        return self.p50_seconds / 3600

    @property
    def p90_hours(self) -> float:
        return self.p90_seconds / 3600


@dataclass(frozen=True, slots=True)
class ETAPrediction:
    """Per-shipment prediction with confidence band."""

    shipment_id: str
    predicted_p50: datetime
    predicted_p90: datetime
    source: str  # "lane", "carrier_fallback", "global_fallback"

    @property
    def confidence_band_seconds(self) -> int:
        return int((self.predicted_p90 - self.predicted_p50).total_seconds())


def _quantile(sorted_values: list[int], q: float) -> int:
    """Nearest-rank percentile — no interpolation, integer output."""
    if not sorted_values:
        raise ValueError("cannot compute quantile of empty list")
    if not 0.0 < q <= 1.0:
        raise ValueError(f"q must be in (0, 1], got {q}")
    rank = max(1, min(len(sorted_values), int(q * len(sorted_values) + 0.5)))
    return sorted_values[rank - 1]


def build_lane_stats(
    completed: list[ShipmentStatus], min_samples: int = 3
) -> dict[tuple[str, str, Carrier], LaneStats]:
    """Aggregate delivered shipments into one ``LaneStats`` per O-D-carrier lane.

    Only ``DELIVERED`` shipments contribute — failures and returns have
    different time distributions and would bias the ETA upward.
    """
    if min_samples < 1:
        raise ValueError("min_samples must be >= 1")
    durations: dict[tuple[str, str, Carrier], list[int]] = defaultdict(list)
    for st in completed:
        if st.state is not ShipmentState.DELIVERED:
            continue
        key = lane_key(st.shipment.origin_district, st.shipment.dest_district, st.shipment.carrier)
        duration = int((st.last_event_at - st.shipment.created_at).total_seconds())
        if duration > 0:
            durations[key].append(duration)
    out: dict[tuple[str, str, Carrier], LaneStats] = {}
    for key, vals in durations.items():
        if len(vals) < min_samples:
            continue
        vals_sorted = sorted(vals)
        out[key] = LaneStats(
            origin=key[0],
            dest=key[1],
            carrier=key[2],
            n_samples=len(vals),
            p50_seconds=_quantile(vals_sorted, 0.5),
            p90_seconds=_quantile(vals_sorted, 0.9),
        )
    return out


def _carrier_fallback(
    lanes: dict[tuple[str, str, Carrier], LaneStats],
) -> dict[Carrier, tuple[int, int]]:
    """Aggregate lane stats up to one ``(p50, p90)`` per carrier."""
    per_carrier: dict[Carrier, list[int]] = defaultdict(list)
    per_carrier_p90: dict[Carrier, list[int]] = defaultdict(list)
    for ln in lanes.values():
        per_carrier[ln.carrier].append(ln.p50_seconds)
        per_carrier_p90[ln.carrier].append(ln.p90_seconds)
    out: dict[Carrier, tuple[int, int]] = {}
    for carrier, p50s in per_carrier.items():
        p50s_sorted = sorted(p50s)
        p90s_sorted = sorted(per_carrier_p90[carrier])
        out[carrier] = (_quantile(p50s_sorted, 0.5), _quantile(p90s_sorted, 0.5))
    return out


def _global_fallback(lanes: dict[tuple[str, str, Carrier], LaneStats]) -> tuple[int, int]:
    """Single ``(p50, p90)`` across all lanes — last-resort cold-start."""
    if not lanes:
        # No completed shipments anywhere → use a 48h / 96h pessimistic guess.
        return (48 * 3600, 96 * 3600)
    p50s = sorted(ln.p50_seconds for ln in lanes.values())
    p90s = sorted(ln.p90_seconds for ln in lanes.values())
    return (_quantile(p50s, 0.5), _quantile(p90s, 0.5))


def predict_eta(
    pending: list[ShipmentStatus],
    lanes: dict[tuple[str, str, Carrier], LaneStats],
) -> list[ETAPrediction]:
    """Predict ETA for every non-terminal shipment.

    Falls through: lane → carrier-wide → global. ``source`` records
    which tier produced the estimate, so dashboards can highlight
    cold-start predictions.
    """
    carrier_fb = _carrier_fallback(lanes)
    global_fb = _global_fallback(lanes)
    out: list[ETAPrediction] = []
    for st in pending:
        if st.is_terminal:
            continue
        key = lane_key(st.shipment.origin_district, st.shipment.dest_district, st.shipment.carrier)
        ln = lanes.get(key)
        if ln is not None:
            p50_s, p90_s, source = ln.p50_seconds, ln.p90_seconds, "lane"
        elif st.shipment.carrier in carrier_fb:
            p50_s, p90_s = carrier_fb[st.shipment.carrier]
            source = "carrier_fallback"
        else:
            p50_s, p90_s = global_fb
            source = "global_fallback"
        out.append(
            ETAPrediction(
                shipment_id=st.shipment.shipment_id,
                predicted_p50=st.shipment.created_at + timedelta(seconds=p50_s),
                predicted_p90=st.shipment.created_at + timedelta(seconds=p90_s),
                source=source,
            )
        )
    return out


__all__ = ["ETAPrediction", "LaneStats", "build_lane_stats", "predict_eta"]
