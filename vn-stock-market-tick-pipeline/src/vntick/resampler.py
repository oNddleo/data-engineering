"""Resample tick streams into OHLCV bars at fixed intervals.

The resampler is a **single-pass fold**: ticks are pre-sorted by
``occurred_at``, then bucketed into left-closed bars whose boundaries
are aligned to the VN_TZ epoch (so a 1-minute bar always starts on
``:00`` seconds, a 5-minute bar on ``:00 / :05 / :10 / …``).

Standard intervals (mirror the names every retail VN-broker UI uses):

| Interval | Seconds | Use case                       |
| -------- | ------- | ------------------------------ |
| ``1m``   | 60      | scalping, sub-minute volatility |
| ``5m``   | 300     | intraday strategy backtesting   |
| ``15m``  | 900     | swing-trade screening           |
| ``1h``   | 3600    | day-trading                     |
| ``1d``   | 86400   | EOD daily bars                  |

Edge cases:

* Bars with **zero ticks** are skipped (the bar stream is sparse).
* A single tick produces a degenerate bar where ``OHLC`` all equal
  the tick's ``price_vnd`` — this is correct and what every retail
  platform shows.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from vntick.schema import VN_TZ, OHLCVBar

if TYPE_CHECKING:
    from collections.abc import Iterable

    from vntick.schema import Tick


INTERVAL_SECONDS: dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "1d": 86400,
}


def parse_interval(name: str) -> int:
    """Map ``"1m" → 60``, etc. Raises ``ValueError`` for unknown names."""
    if name not in INTERVAL_SECONDS:
        raise ValueError(f"unknown interval {name!r}; expected one of {sorted(INTERVAL_SECONDS)}")
    return INTERVAL_SECONDS[name]


def _floor_to_interval(ts: datetime, interval_seconds: int) -> datetime:
    """Floor ``ts`` (UTC instant) to the nearest interval boundary in ``VN_TZ``.

    1-day bars floor to ``00:00 VN_TZ``; intra-day bars floor to the
    minute boundary inside the trading day.
    """
    local = ts.astimezone(VN_TZ)
    if interval_seconds >= 86400:
        # Daily bar — floor to midnight VN_TZ.
        floored = local.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        # Floor to the interval boundary inside the day.
        seconds_into_day = local.hour * 3600 + local.minute * 60 + local.second
        delta = seconds_into_day % interval_seconds
        floored = local - timedelta(seconds=delta, microseconds=local.microsecond)
    return floored.astimezone(timezone.utc).astimezone(VN_TZ)


def resample(ticks: Iterable[Tick], interval: str = "1m") -> list[OHLCVBar]:
    """Fold ``ticks`` into OHLCV bars at ``interval``.

    The output is sorted by ``(code, bar_start)``. Bars are emitted
    only for buckets that had at least one tick (sparse output).
    """
    interval_seconds = parse_interval(interval)
    buckets: dict[tuple[str, datetime], list[Tick]] = defaultdict(list)
    for tick in sorted(ticks, key=lambda t: t.occurred_at):
        bar_start = _floor_to_interval(tick.occurred_at, interval_seconds)
        buckets[(tick.code, bar_start)].append(tick)

    out: list[OHLCVBar] = []
    for (code, bar_start), group in sorted(buckets.items()):
        # ``group`` is already sorted because we iterated ticks in order
        # and dict insertion order preserves that.
        open_price = group[0].price_vnd
        close_price = group[-1].price_vnd
        high_price = max(t.price_vnd for t in group)
        low_price = min(t.price_vnd for t in group)
        volume = sum(t.volume for t in group)
        out.append(
            OHLCVBar(
                code=code,
                interval_seconds=interval_seconds,
                bar_start=bar_start,
                open_vnd=open_price,
                high_vnd=high_price,
                low_vnd=low_price,
                close_vnd=close_price,
                volume=volume,
                n_trades=len(group),
            )
        )
    return out


__all__ = ["INTERVAL_SECONDS", "parse_interval", "resample"]
