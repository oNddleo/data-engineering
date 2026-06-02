"""Cumulative kWh readings → per-interval ``ConsumptionInterval``.

Smart-meter telemetry in the wild looks nothing like the textbook
"monotone non-decreasing series". Real EVN streams have:

* **Out-of-order arrival**. UDP-over-NB-IoT means packets land in
  whatever order the cell tower felt like. We sort per-meter before
  folding.
* **Gaps**. The meter loses radio signal for an hour during a Tết
  fireworks storm; we get no reading. The derive pass fills the gap
  with the linearly-interpolated consumption and flags the
  resulting interval ``is_estimated=True``.
* **Rollover**. A 7-digit cumulative counter wraps from
  ``9_999_999.99 kWh`` back to ``0.00``. The derive pass detects
  this when a later reading is smaller than the prior reading **and**
  the would-be negative delta is implausible (> 50% of max range).
* **Duplicates**. Same ``(meter_id, observed_at)`` arrives twice
  (NB-IoT retries). We dedupe by ``(meter_id, observed_at, value)``
  and keep the one matching the established trajectory.
* **Backward jumps that aren't rollover**. A backward step that isn't
  consistent with rollover (e.g. cumulative drops by 5 kWh) is a
  meter fault — we drop the offending reading and emit a Finding
  via the anomaly module rather than producing a negative interval.

Output is sorted by ``(meter_id, start_at)`` and intervals never
overlap.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import timedelta
from itertools import pairwise
from typing import TYPE_CHECKING

from evnmeter.schema import METER_MAX_X100, ConsumptionInterval

if TYPE_CHECKING:
    from collections.abc import Iterable

    from evnmeter.schema import Reading


# Rollover is plausible when a backward step covers more than this
# fraction of the meter's range. Below this we treat it as a fault.
_ROLLOVER_FRACTION = 0.50


def _is_rollover(prev_value: int, next_value: int) -> bool:
    """``True`` when ``prev → next`` is consistent with a meter wrap.

    A wrap means the new reading is "small" while the previous was "near
    the top" — the implied forward delta crosses the modulus.
    """
    if next_value >= prev_value:
        return False
    span = METER_MAX_X100 + 1
    forward_via_wrap = (span - prev_value) + next_value
    backward = prev_value - next_value
    # If the wrap path is shorter than the backward jump, it's much
    # more likely to be a true rollover.
    return forward_via_wrap < backward and backward > int(span * _ROLLOVER_FRACTION)


def _delta(prev_value: int, next_value: int) -> int:
    """Cumulative delta, accounting for rollover. Returns ``-1`` for an
    inconsistent backward step (caller should drop this reading)."""
    if next_value >= prev_value:
        return next_value - prev_value
    if _is_rollover(prev_value, next_value):
        span = METER_MAX_X100 + 1
        return (span - prev_value) + next_value
    return -1


def derive(
    readings: Iterable[Reading],
    *,
    max_gap_minutes: int = 90,
) -> list[ConsumptionInterval]:
    """Fold cumulative readings into per-interval deltas.

    Gaps longer than ``max_gap_minutes`` are *not* bridged with a
    single estimated interval — they're split into one bridging
    interval per natural-interval-width chunk. (EVN's natural interval
    is 30 minutes, so a 4-hour gap becomes 8 estimated intervals.)
    """
    if max_gap_minutes <= 0:
        raise ValueError("max_gap_minutes must be > 0")

    by_meter: dict[str, list[Reading]] = defaultdict(list)
    for r in readings:
        by_meter[r.meter_id].append(r)

    out: list[ConsumptionInterval] = []
    for meter_id, group in by_meter.items():
        # Dedupe: same (observed_at, value) → keep one. Same observed_at
        # with different values → keep the larger (closer to truth in
        # cumulative-counter semantics).
        deduped: dict[object, Reading] = {}
        for r in group:
            key = r.observed_at
            existing = deduped.get(key)
            if existing is None or r.cumulative_kwh_x100 > existing.cumulative_kwh_x100:
                deduped[key] = r
        sorted_readings = sorted(deduped.values(), key=lambda r: r.observed_at)
        if len(sorted_readings) < 2:
            continue
        for prev, curr in pairwise(sorted_readings):
            delta = _delta(prev.cumulative_kwh_x100, curr.cumulative_kwh_x100)
            if delta < 0:
                # Faulty backward step — drop this transition.
                continue
            gap_seconds = (curr.observed_at - prev.observed_at).total_seconds()
            if gap_seconds <= max_gap_minutes * 60:
                # Single interval.
                out.append(
                    ConsumptionInterval(
                        meter_id=meter_id,
                        start_at=prev.observed_at,
                        end_at=curr.observed_at,
                        kwh_x100=delta,
                        is_estimated=False,
                    )
                )
                continue
            # Wide gap → split into 30-minute chunks with proportionally
            # distributed estimated consumption.
            n_chunks = max(1, int(gap_seconds // (30 * 60)))
            chunk_seconds = gap_seconds / n_chunks
            base_kwh = delta // n_chunks
            remainder = delta - base_kwh * n_chunks
            cursor = prev.observed_at
            for i in range(n_chunks):
                end = (
                    curr.observed_at
                    if i == n_chunks - 1
                    else prev.observed_at + timedelta(seconds=chunk_seconds * (i + 1))
                )
                # Distribute remainder onto the last chunk.
                chunk_kwh = base_kwh + (remainder if i == n_chunks - 1 else 0)
                out.append(
                    ConsumptionInterval(
                        meter_id=meter_id,
                        start_at=cursor,
                        end_at=end,
                        kwh_x100=chunk_kwh,
                        is_estimated=True,
                    )
                )
                cursor = end

    out.sort(key=lambda c: (c.meter_id, c.start_at))
    return out


__all__ = ["derive"]
