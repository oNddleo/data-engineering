"""Meter-reading anomaly detection — the three patterns EVN ops actually watch.

* **Zero usage** — any month with ``kwh_used == 0`` from a customer
  with a recent non-zero history. Surfaces vacant-property loops
  and possible meter tampering / theft. (Genuinely vacant accounts
  show a long zero streak and aren't flagged again.)

* **Sudden drop** — current month's usage is more than
  ``max_drop_ratio`` (default 80%) below the trailing-3-month
  average. Strong indicator of meter bypass or under-reading.

* **Unrealistic spike** — current month's usage is more than
  ``min_spike_multiplier`` (default 5×) the trailing-3-month
  average. Indicates billing-system error or meter malfunction.

All three need at least 3 prior readings per customer to establish a
baseline; customers with fewer readings are skipped.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from evn.schema import AnomalyFinding, AnomalyKind

if TYPE_CHECKING:
    from evn.schema import MeterReading

_MIN_BASELINE_MONTHS = 3


def find_zero_usage(readings: list[MeterReading]) -> list[AnomalyFinding]:
    """Surface zero-kWh readings from customers with a recent non-zero history."""
    per_customer = _group_by_customer(readings)
    out: list[AnomalyFinding] = []
    for customer_code, history in per_customer.items():
        if len(history) < _MIN_BASELINE_MONTHS + 1:
            continue
        history.sort(key=lambda r: r.period_start)
        latest = history[-1]
        if latest.kwh_used != 0:
            continue
        # Skip when the trailing 3 months were also zero (true vacancy).
        prior = history[-(_MIN_BASELINE_MONTHS + 1) : -1]
        if all(p.kwh_used == 0 for p in prior):
            continue
        out.append(
            AnomalyFinding(
                kind=AnomalyKind.ZERO_USAGE,
                customer_code=customer_code,
                category=latest.category,
                detail=(
                    f"customer {customer_code}: 0 kWh in "
                    f"{latest.period_start.isoformat()}..{latest.period_end.isoformat()} "
                    f"after a non-zero trailing window"
                ),
                metric=sum(p.kwh_used for p in prior),
            )
        )
    out.sort(key=lambda f: (-f.metric, f.customer_code))
    return out


def find_sudden_drops(
    readings: list[MeterReading],
    *,
    max_drop_ratio: float = 0.80,
) -> list[AnomalyFinding]:
    """Surface customers whose latest usage dropped > ``max_drop_ratio``."""
    if not 0 < max_drop_ratio < 1:
        raise ValueError(
            f"max_drop_ratio must be in (0, 1), got {max_drop_ratio}",
        )
    per_customer = _group_by_customer(readings)
    out: list[AnomalyFinding] = []
    for customer_code, history in per_customer.items():
        if len(history) < _MIN_BASELINE_MONTHS + 1:
            continue
        history.sort(key=lambda r: r.period_start)
        latest = history[-1]
        prior = history[-(_MIN_BASELINE_MONTHS + 1) : -1]
        baseline = sum(p.kwh_used for p in prior) / len(prior)
        # Require a non-trivial baseline; tiny ones aren't actionable.
        if baseline < 10:
            continue
        # Skip true zeros — that's the ZERO_USAGE signal's job.
        if latest.kwh_used == 0:
            continue
        drop = (baseline - latest.kwh_used) / baseline
        if drop >= max_drop_ratio:
            out.append(
                AnomalyFinding(
                    kind=AnomalyKind.SUDDEN_DROP,
                    customer_code=customer_code,
                    category=latest.category,
                    detail=(
                        f"customer {customer_code}: {latest.kwh_used} kWh "
                        f"vs {baseline:.0f} baseline ({drop * 100:.0f}% drop)"
                    ),
                    metric=int(drop * 100),
                )
            )
    out.sort(key=lambda f: (-f.metric, f.customer_code))
    return out


def find_unrealistic_spikes(
    readings: list[MeterReading],
    *,
    min_spike_multiplier: float = 5.0,
) -> list[AnomalyFinding]:
    """Surface customers whose latest usage spiked > ``min_spike_multiplier``."""
    if min_spike_multiplier <= 1.0:
        raise ValueError(
            f"min_spike_multiplier must be > 1.0, got {min_spike_multiplier}",
        )
    per_customer = _group_by_customer(readings)
    out: list[AnomalyFinding] = []
    for customer_code, history in per_customer.items():
        if len(history) < _MIN_BASELINE_MONTHS + 1:
            continue
        history.sort(key=lambda r: r.period_start)
        latest = history[-1]
        prior = history[-(_MIN_BASELINE_MONTHS + 1) : -1]
        baseline = sum(p.kwh_used for p in prior) / len(prior)
        if baseline < 10:
            continue
        ratio = latest.kwh_used / baseline
        if ratio >= min_spike_multiplier:
            out.append(
                AnomalyFinding(
                    kind=AnomalyKind.UNREALISTIC_SPIKE,
                    customer_code=customer_code,
                    category=latest.category,
                    detail=(
                        f"customer {customer_code}: {latest.kwh_used} kWh "
                        f"vs {baseline:.0f} baseline ({ratio:.1f}× spike)"
                    ),
                    metric=int(ratio * 100),
                )
            )
    out.sort(key=lambda f: (-f.metric, f.customer_code))
    return out


def _group_by_customer(
    readings: list[MeterReading],
) -> dict[str, list[MeterReading]]:
    groups: dict[str, list[MeterReading]] = defaultdict(list)
    for r in readings:
        groups[r.customer_code].append(r)
    return groups


__all__ = [
    "find_sudden_drops",
    "find_unrealistic_spikes",
    "find_zero_usage",
]
