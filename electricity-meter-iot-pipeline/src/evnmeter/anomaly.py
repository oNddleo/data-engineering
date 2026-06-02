"""Anomaly detectors over derived consumption intervals.

Three things EVN ops watches for:

* **GAP** — the derived stream contains a long ``is_estimated`` run
  (signal was lost; the bill may understate or overstate actual
  consumption).
* **SPIKE** — an interval's per-hour consumption is more than
  ``k × historical_mean`` (default 5×). Could indicate a stuck AC,
  a faulty meter, or actual theft via a bypassed neutral.
* **STUCK** — many consecutive intervals with zero or near-zero
  consumption. Either the meter is dead, the customer left for
  long-term travel, or a wire was cut upstream.

Each detector is a pure function over a list of
``ConsumptionInterval`` plus thresholds the caller can tune. No I/O,
no clock dependencies — easy to unit-test deterministically.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from evnmeter.schema import ConsumptionInterval


class AnomalyKind(str, Enum):
    GAP = "GAP"
    SPIKE = "SPIKE"
    STUCK = "STUCK"


@dataclass(frozen=True, slots=True)
class Anomaly:
    """One ops-actionable issue with one meter's stream."""

    kind: AnomalyKind
    meter_id: str
    start_at: datetime
    end_at: datetime
    detail: str
    metric: int  # context-dependent: gap minutes, spike kWh×100, etc.


def find_gaps(
    intervals: list[ConsumptionInterval],
    *,
    min_minutes: int = 120,
) -> list[Anomaly]:
    """Flag runs of estimated intervals lasting ≥ ``min_minutes`` per meter."""
    if min_minutes <= 0:
        raise ValueError("min_minutes must be > 0")
    by_meter: dict[str, list[ConsumptionInterval]] = defaultdict(list)
    for c in intervals:
        by_meter[c.meter_id].append(c)
    out: list[Anomaly] = []
    for meter_id, group in by_meter.items():
        group.sort(key=lambda c: c.start_at)
        run_start_idx: int | None = None
        for i, c in enumerate(group):
            if c.is_estimated and run_start_idx is None:
                run_start_idx = i
                continue
            if not c.is_estimated and run_start_idx is not None:
                # Flush the run.
                run_start = group[run_start_idx]
                run_end = group[i - 1]
                duration_min = (run_end.end_at - run_start.start_at).total_seconds() / 60
                if duration_min >= min_minutes:
                    out.append(
                        Anomaly(
                            kind=AnomalyKind.GAP,
                            meter_id=meter_id,
                            start_at=run_start.start_at,
                            end_at=run_end.end_at,
                            detail=f"estimated run of {int(duration_min)} minutes",
                            metric=int(duration_min),
                        )
                    )
                run_start_idx = None
        # Trailing run that touches the end.
        if run_start_idx is not None:
            run_start = group[run_start_idx]
            run_end = group[-1]
            duration_min = (run_end.end_at - run_start.start_at).total_seconds() / 60
            if duration_min >= min_minutes:
                out.append(
                    Anomaly(
                        kind=AnomalyKind.GAP,
                        meter_id=meter_id,
                        start_at=run_start.start_at,
                        end_at=run_end.end_at,
                        detail=f"estimated run of {int(duration_min)} minutes",
                        metric=int(duration_min),
                    )
                )
    return out


def _per_hour_kwh_x100(c: ConsumptionInterval) -> float:
    """Normalise to kWh-per-hour for spike detection (intervals vary in length)."""
    hours = (c.end_at - c.start_at).total_seconds() / 3600
    if hours <= 0:
        return 0.0
    return c.kwh_x100 / hours


def find_spikes(
    intervals: list[ConsumptionInterval],
    *,
    multiplier: float = 5.0,
    min_historical_intervals: int = 10,
) -> list[Anomaly]:
    """Flag intervals where per-hour kWh > ``multiplier × historical_mean``.

    The historical mean is computed per-meter over **non-estimated**
    intervals only — gap-filled intervals are too uncertain to use as
    baseline. Meters with fewer than ``min_historical_intervals``
    real readings are skipped (cold-start tolerance).
    """
    if multiplier <= 1.0:
        raise ValueError("multiplier must be > 1.0")
    if min_historical_intervals < 2:
        raise ValueError("min_historical_intervals must be >= 2")
    by_meter: dict[str, list[ConsumptionInterval]] = defaultdict(list)
    for c in intervals:
        by_meter[c.meter_id].append(c)
    out: list[Anomaly] = []
    for meter_id, group in by_meter.items():
        real = [c for c in group if not c.is_estimated]
        if len(real) < min_historical_intervals:
            continue
        per_hour = [_per_hour_kwh_x100(c) for c in real]
        mean = sum(per_hour) / len(per_hour)
        if mean == 0:
            continue
        threshold = mean * multiplier
        for c in real:
            if _per_hour_kwh_x100(c) >= threshold:
                out.append(
                    Anomaly(
                        kind=AnomalyKind.SPIKE,
                        meter_id=meter_id,
                        start_at=c.start_at,
                        end_at=c.end_at,
                        detail=f"per-hour kwh×100={_per_hour_kwh_x100(c):.0f} ≥ {threshold:.0f} (mean {mean:.0f})",
                        metric=c.kwh_x100,
                    )
                )
    return out


def find_stuck(
    intervals: list[ConsumptionInterval],
    *,
    min_zero_intervals: int = 12,
    near_zero_threshold_x100: int = 10,
) -> list[Anomaly]:
    """Flag runs of ≥ ``min_zero_intervals`` intervals at or below the
    near-zero threshold (kWh × 100). Default threshold is 0.10 kWh —
    typical baseline for a fridge alone is 5-10 W ≈ 0.005-0.01 kWh
    in a 30-minute window, so the threshold is the right order of
    magnitude for "really nothing on except baseline electronics".
    """
    if min_zero_intervals <= 0:
        raise ValueError("min_zero_intervals must be > 0")
    if near_zero_threshold_x100 < 0:
        raise ValueError("near_zero_threshold_x100 must be >= 0")
    by_meter: dict[str, list[ConsumptionInterval]] = defaultdict(list)
    for c in intervals:
        by_meter[c.meter_id].append(c)
    out: list[Anomaly] = []
    for meter_id, group in by_meter.items():
        group.sort(key=lambda c: c.start_at)
        run_start_idx: int | None = None
        for i, c in enumerate(group):
            if c.kwh_x100 <= near_zero_threshold_x100:
                if run_start_idx is None:
                    run_start_idx = i
                continue
            if run_start_idx is not None:
                run_len = i - run_start_idx
                if run_len >= min_zero_intervals:
                    rs = group[run_start_idx]
                    re = group[i - 1]
                    out.append(
                        Anomaly(
                            kind=AnomalyKind.STUCK,
                            meter_id=meter_id,
                            start_at=rs.start_at,
                            end_at=re.end_at,
                            detail=f"{run_len} consecutive near-zero intervals",
                            metric=run_len,
                        )
                    )
                run_start_idx = None
        # Trailing run.
        if run_start_idx is not None:
            run_len = len(group) - run_start_idx
            if run_len >= min_zero_intervals:
                rs = group[run_start_idx]
                re = group[-1]
                out.append(
                    Anomaly(
                        kind=AnomalyKind.STUCK,
                        meter_id=meter_id,
                        start_at=rs.start_at,
                        end_at=re.end_at,
                        detail=f"{run_len} consecutive near-zero intervals",
                        metric=run_len,
                    )
                )
    return out


__all__ = ["Anomaly", "AnomalyKind", "find_gaps", "find_spikes", "find_stuck"]
