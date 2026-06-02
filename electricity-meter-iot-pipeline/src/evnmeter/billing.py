"""Monthly billing from derived consumption intervals.

Aggregates a meter's intervals over a billing window, applies the
6-tier progressive tariff, and produces one ``MonthlyBill`` per
``(meter_id, period)``. The pipeline is:

1. Filter intervals to ``[period_start, period_end)`` per meter.
2. Sum ``kwh_x100`` across the window; floor-divide by 100 to get
   billable whole kWh (EVN's billing convention — fractional kWh
   round down on each invoice).
3. Apply :func:`tariff.compute_bill` for the breakdown + totals.
4. Materialise a :class:`MonthlyBill`.

Intervals partially overlapping the window are pro-rated by elapsed
seconds. This matters at month boundaries — a 23:30 → 00:00 interval
straddling Mar 31 / Apr 1 is split 30 min into March and 0 min into
April.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

from evnmeter.tariff import DEFAULT_VAT_BPS, TierBreakdown, compute_bill, default_tiers

if TYPE_CHECKING:
    from datetime import datetime

    from evnmeter.schema import ConsumptionInterval
    from evnmeter.tariff import TierBreak


@dataclass(frozen=True, slots=True)
class MonthlyBill:
    """One bill for one ``(meter_id, period_start)`` cell."""

    meter_id: str
    period_start: datetime
    period_end: datetime
    billed_kwh: int
    breakdown: tuple[TierBreakdown, ...]
    subtotal_vnd: int
    vat_vnd: int
    grand_total_vnd: int
    n_estimated_intervals: int


def _overlap_seconds(c: ConsumptionInterval, start: datetime, end: datetime) -> float:
    """Seconds the interval ``c`` overlaps the half-open ``[start, end)``."""
    lo = max(c.start_at, start)
    hi = min(c.end_at, end)
    if hi <= lo:
        return 0.0
    return (hi - lo).total_seconds()


def bill_meters(
    intervals: list[ConsumptionInterval],
    period_start: datetime,
    period_end: datetime,
    tiers: tuple[TierBreak, ...] | None = None,
    vat_bps: int = DEFAULT_VAT_BPS,
) -> list[MonthlyBill]:
    """Compute one ``MonthlyBill`` per meter that has any usage in the window.

    Meters with zero in-window consumption are skipped — the bill
    would be 0 VND and dashboards don't need empty rows.
    """
    if period_start.tzinfo is None or period_end.tzinfo is None:
        raise ValueError("period_start + period_end must be timezone-aware")
    if period_start >= period_end:
        raise ValueError(f"period_start {period_start} must be < period_end {period_end}")
    use_tiers = tiers if tiers is not None else default_tiers()

    # Sum prorated kWh×100 per meter.
    by_meter_kwh: dict[str, int] = defaultdict(int)
    by_meter_estimated: dict[str, int] = defaultdict(int)
    for c in intervals:
        overlap = _overlap_seconds(c, period_start, period_end)
        if overlap <= 0:
            continue
        total = (c.end_at - c.start_at).total_seconds()
        if total <= 0:
            continue
        prorated = int(c.kwh_x100 * overlap / total)
        by_meter_kwh[c.meter_id] += prorated
        if c.is_estimated:
            by_meter_estimated[c.meter_id] += 1

    out: list[MonthlyBill] = []
    for meter_id, kwh_x100 in sorted(by_meter_kwh.items()):
        if kwh_x100 == 0:
            continue
        billed_kwh = kwh_x100 // 100  # whole-kWh floor per EVN convention
        breakdown, subtotal, vat, grand = compute_bill(billed_kwh, use_tiers, vat_bps)
        out.append(
            MonthlyBill(
                meter_id=meter_id,
                period_start=period_start,
                period_end=period_end,
                billed_kwh=billed_kwh,
                breakdown=tuple(breakdown),
                subtotal_vnd=subtotal,
                vat_vnd=vat,
                grand_total_vnd=grand,
                n_estimated_intervals=by_meter_estimated[meter_id],
            )
        )
    return out


__all__ = ["MonthlyBill", "bill_meters"]
