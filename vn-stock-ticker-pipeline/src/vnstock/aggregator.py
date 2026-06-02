"""Multi-day OHLC aggregation — N-day moving averages + per-ticker stats.

For each ticker we compute:

* ``TickerStats`` — high water mark + low water mark + total volume +
  average close + average volume across the supplied date range.

* ``moving_average_close(bars, n)`` — N-day rolling mean of the
  close price, returned as a list aligned with the input bars (the
  first n-1 entries are ``None``).

* ``volume_weighted_avg_price(bars)`` — VWAP across the bar set
  (sum(close × volume) / sum(volume)).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vnstock.schema import Exchange, OHLCBar


@dataclass(frozen=True, slots=True)
class TickerStats:
    """Aggregate statistics over a date range for one ticker."""

    symbol: str
    exchange: Exchange
    n_bars: int
    high_water_mark_vnd: int  # max high across the period
    low_water_mark_vnd: int  # min low across the period
    total_volume: int
    avg_close_vnd: int
    avg_volume: int
    first_close_vnd: int
    last_close_vnd: int

    def __post_init__(self) -> None:
        if self.n_bars < 0:
            raise ValueError("n_bars must be >= 0")
        if self.high_water_mark_vnd < self.low_water_mark_vnd:
            raise ValueError(
                f"high_water_mark ({self.high_water_mark_vnd}) "
                f"< low_water_mark ({self.low_water_mark_vnd})",
            )

    @property
    def period_change_vnd(self) -> int:
        """Last close − first close."""
        return self.last_close_vnd - self.first_close_vnd


def aggregate_ticker_stats(bars: list[OHLCBar]) -> list[TickerStats]:
    """Per-(symbol, exchange) rollup across the supplied bars."""
    groups: dict[tuple[str, Exchange], list[OHLCBar]] = defaultdict(list)
    for b in bars:
        groups[(b.symbol, b.exchange)].append(b)

    out: list[TickerStats] = []
    for (symbol, exchange), group in groups.items():
        ordered = sorted(group, key=lambda b: b.date)
        total_vol = sum(b.volume for b in ordered)
        n = len(ordered)
        avg_close = sum(b.close_vnd for b in ordered) // n
        avg_volume = total_vol // n if n > 0 else 0
        out.append(
            TickerStats(
                symbol=symbol,
                exchange=exchange,
                n_bars=n,
                high_water_mark_vnd=max(b.high_vnd for b in ordered),
                low_water_mark_vnd=min(b.low_vnd for b in ordered),
                total_volume=total_vol,
                avg_close_vnd=avg_close,
                avg_volume=avg_volume,
                first_close_vnd=ordered[0].close_vnd,
                last_close_vnd=ordered[-1].close_vnd,
            )
        )
    out.sort(key=lambda s: (s.exchange.value, s.symbol))
    return out


def moving_average_close(
    bars: list[OHLCBar],
    n: int,
) -> list[int | None]:
    """N-day moving average of ``close_vnd`` over a chronologically-sorted
    list of bars (for one ticker). The first ``n - 1`` entries are
    ``None``. Output length matches ``len(bars)``.
    """
    if n < 1:
        raise ValueError(f"n must be >= 1, got {n}")
    if not bars:
        return []
    # Defensive: caller is expected to pass one ticker's bars.
    ordered = sorted(bars, key=lambda b: b.date)
    out: list[int | None] = []
    window_sum = 0
    for i, bar in enumerate(ordered):
        window_sum += bar.close_vnd
        if i >= n:
            window_sum -= ordered[i - n].close_vnd
        if i < n - 1:
            out.append(None)
        else:
            out.append(window_sum // n)
    return out


def volume_weighted_avg_price(bars: list[OHLCBar]) -> int:
    """VWAP across the supplied bars (sum(close × volume) / sum(volume))."""
    if not bars:
        raise ValueError("bars must be non-empty")
    total_vol = sum(b.volume for b in bars)
    if total_vol == 0:
        raise ValueError("total volume is zero; VWAP undefined")
    weighted = sum(b.close_vnd * b.volume for b in bars)
    return weighted // total_vol


__all__ = [
    "TickerStats",
    "aggregate_ticker_stats",
    "moving_average_close",
    "volume_weighted_avg_price",
]
