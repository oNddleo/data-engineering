"""Shared test fixtures: OHLC bar + order + trade builders."""

from __future__ import annotations

from datetime import date
from typing import Any

from vnstock.bars import Trade
from vnstock.schema import Exchange, OHLCBar, Order, OrderKind, OrderSide


def make_bar(**overrides: Any) -> OHLCBar:
    """Build an OHLC bar.

    If only ``close_vnd`` is overridden without ``open/high/low``, those
    fields are auto-scaled around the new close so the OHLC invariants
    still hold without burdening every test caller.
    """
    defaults: dict[str, Any] = {
        "symbol": "VIC",
        "exchange": Exchange.HOSE,
        "date": date(2025, 5, 19),
        "open_vnd": 60_000,
        "high_vnd": 62_000,
        "low_vnd": 59_500,
        "close_vnd": 61_500,
        "volume": 1_000_000,
        "reference_price_vnd": 60_000,
    }
    overrode_close = "close_vnd" in overrides
    overrode_open = "open_vnd" in overrides
    overrode_high = "high_vnd" in overrides
    overrode_low = "low_vnd" in overrides
    defaults.update(overrides)
    if overrode_close and not (overrode_open and overrode_high and overrode_low):
        close = int(defaults["close_vnd"])
        if not overrode_open:
            defaults["open_vnd"] = close
        if not overrode_high:
            defaults["high_vnd"] = max(close, int(defaults["open_vnd"])) + 500
        if not overrode_low:
            defaults["low_vnd"] = max(
                1,
                min(close, int(defaults["open_vnd"])) - 500,
            )
    return OHLCBar(**defaults)


def make_order(**overrides: Any) -> Order:
    defaults: dict[str, Any] = {
        "order_id": "O-1",
        "symbol": "VIC",
        "exchange": Exchange.HOSE,
        "side": OrderSide.BUY,
        "kind": OrderKind.LO,
        "quantity": 1_000,
        "limit_price_vnd": 60_000,
    }
    defaults.update(overrides)
    return Order(**defaults)


def make_trade(**overrides: Any) -> Trade:
    defaults: dict[str, Any] = {
        "symbol": "VIC",
        "exchange": Exchange.HOSE,
        "ts_ms": 1_715_000_000_000,
        "price_vnd": 60_000,
        "volume": 100,
    }
    defaults.update(overrides)
    return Trade(**defaults)


__all__ = ["make_bar", "make_order", "make_trade"]
