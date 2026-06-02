"""Customer Lifetime Value (CLV) forecast.

We use the **historical CLV** formula — appropriate for marketplaces
where most customers have short histories (months, not years):

    CLV = AOV × purchase_frequency × expected_lifetime_days / window_days

* **AOV** = monetary / frequency (or 0 if frequency = 0).
* **purchase_frequency** = orders / observation_window_days.
* **expected_lifetime_days** is a per-segment lookup — segments differ
  dramatically in retention behaviour:

| Segment              | Expected lifetime |
| -------------------- | ----------------- |
| CHAMPIONS            | 1095 days (3 yr)  |
| LOYAL_CUSTOMERS      | 730 days (2 yr)   |
| POTENTIAL_LOYALISTS  | 540 days          |
| NEW_CUSTOMERS        | 365 days          |
| NEED_ATTENTION       | 270 days          |
| ABOUT_TO_SLEEP       | 180 days          |
| AT_RISK              | 120 days          |
| CANT_LOSE_THEM       | 90 days           |
| HIBERNATING          | 60 days           |
| LOST                 | 0 days            |

These are conservative VN-marketplace defaults — actual values
should come from cohort-survival analysis. Override via the
``lifetime_days`` parameter for testing or per-vertical tuning.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from clvseg.schema import Segment

if TYPE_CHECKING:
    from clvseg.schema import RFMScore


_DEFAULT_LIFETIME_DAYS: dict[Segment, int] = {
    Segment.CHAMPIONS: 1095,
    Segment.LOYAL_CUSTOMERS: 730,
    Segment.POTENTIAL_LOYALISTS: 540,
    Segment.NEW_CUSTOMERS: 365,
    Segment.NEED_ATTENTION: 270,
    Segment.ABOUT_TO_SLEEP: 180,
    Segment.AT_RISK: 120,
    Segment.CANT_LOSE_THEM: 90,
    Segment.HIBERNATING: 60,
    Segment.LOST: 0,
}


@dataclass(frozen=True, slots=True)
class CLVForecast:
    """Per-customer CLV forecast in integer VND."""

    customer_id: str
    segment: Segment
    historical_aov_vnd: int  # 0 for never-bought
    historical_frequency: int
    window_days: int
    expected_lifetime_days: int
    forecast_vnd: int


def forecast(
    scores: list[RFMScore],
    assignments: dict[str, Segment],
    window_days: int,
    lifetime_days: dict[Segment, int] | None = None,
) -> list[CLVForecast]:
    """Compute :class:`CLVForecast` for every scored customer.

    ``window_days`` is the observation window length the RFM scores
    were computed over — the same value the simulator + scoring engine
    used. Passing the wrong value silently produces wrong CLVs.
    """
    if window_days <= 0:
        raise ValueError("window_days must be > 0")
    lookup = lifetime_days if lifetime_days is not None else _DEFAULT_LIFETIME_DAYS
    out: list[CLVForecast] = []
    for s in scores:
        seg = assignments.get(s.customer_id, Segment.LOST)
        aov = s.monetary_vnd // s.frequency if s.frequency > 0 else 0
        lifetime = lookup.get(seg, 0)
        if s.frequency > 0 and aov > 0 and lifetime > 0:
            # Daily-frequency × AOV × lifetime → expected total spend.
            forecast_vnd = aov * s.frequency * lifetime // window_days
        else:
            forecast_vnd = 0
        out.append(
            CLVForecast(
                customer_id=s.customer_id,
                segment=seg,
                historical_aov_vnd=aov,
                historical_frequency=s.frequency,
                window_days=window_days,
                expected_lifetime_days=lifetime,
                forecast_vnd=forecast_vnd,
            )
        )
    return out


def total_clv_by_segment(forecasts: list[CLVForecast]) -> dict[Segment, int]:
    """Roll up total forecasted CLV per segment — for portfolio dashboards."""
    out: dict[Segment, int] = {seg: 0 for seg in Segment}
    for f in forecasts:
        out[f.segment] += f.forecast_vnd
    return out


def top_clv(forecasts: list[CLVForecast], n: int = 20) -> list[CLVForecast]:
    """Top ``n`` customers by forecasted CLV. Ties broken by ``customer_id``."""
    if n <= 0:
        raise ValueError("n must be > 0")
    items = sorted(forecasts, key=lambda f: (-f.forecast_vnd, f.customer_id))
    return items[:n]


__all__ = ["CLVForecast", "forecast", "top_clv", "total_clv_by_segment"]
