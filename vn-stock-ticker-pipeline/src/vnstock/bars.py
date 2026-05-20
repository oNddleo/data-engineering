"""OHLC bar utilities — aggregation from intraday trades.

A **trade** carries ``(price, volume, ts_ms)``. We aggregate a stream
of trades for one (symbol, exchange, date) into a single
``OHLCBar`` using the standard rules:

* ``open`` = first trade's price (lowest ``ts_ms``)
* ``high`` = max trade price
* ``low``  = min trade price
* ``close`` = last trade's price (highest ``ts_ms``)
* ``volume`` = sum of trade volumes

If the trade stream is empty, we cannot produce a bar — the caller
must supply at least one trade per day.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from vnstock.schema import OHLCBar

if TYPE_CHECKING:
    from datetime import date

    from vnstock.schema import Exchange


@dataclass(frozen=True, slots=True)
class Trade:
    """One executed trade — the unit fed into bar aggregation."""

    symbol: str
    exchange: Exchange
    ts_ms: int
    price_vnd: int
    volume: int

    def __post_init__(self) -> None:
        if not self.symbol:
            raise ValueError("symbol must be non-empty")
        if self.price_vnd <= 0:
            raise ValueError(f"price_vnd must be > 0, got {self.price_vnd}")
        if self.volume <= 0:
            raise ValueError(f"volume must be > 0, got {self.volume}")
        if self.ts_ms < 0:
            raise ValueError(f"ts_ms must be >= 0, got {self.ts_ms}")


def aggregate_bar(
    trades: list[Trade],
    bar_date: date,
    reference_price_vnd: int,
) -> OHLCBar:
    """Aggregate a list of trades into one OHLC bar for ``bar_date``."""
    if not trades:
        raise ValueError("trades must be non-empty")
    # All trades must share symbol + exchange.
    first = trades[0]
    for t in trades[1:]:
        if t.symbol != first.symbol or t.exchange is not first.exchange:
            raise ValueError("trades must all share (symbol, exchange)")
    if reference_price_vnd <= 0:
        raise ValueError(
            f"reference_price_vnd must be > 0, got {reference_price_vnd}",
        )

    ordered = sorted(trades, key=lambda t: t.ts_ms)
    return OHLCBar(
        symbol=first.symbol,
        exchange=first.exchange,
        date=bar_date,
        open_vnd=ordered[0].price_vnd,
        close_vnd=ordered[-1].price_vnd,
        high_vnd=max(t.price_vnd for t in ordered),
        low_vnd=min(t.price_vnd for t in ordered),
        volume=sum(t.volume for t in ordered),
        reference_price_vnd=reference_price_vnd,
    )


__all__ = ["Trade", "aggregate_bar"]
