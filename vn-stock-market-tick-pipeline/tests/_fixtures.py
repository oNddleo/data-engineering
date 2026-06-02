"""Canonical record builders for tests."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from vntick.schema import VN_TZ, Exchange, OHLCVBar, Symbol, Tick

DEFAULT_TS = datetime(2026, 5, 4, 9, 30, 0, tzinfo=VN_TZ)


def make_symbol(**overrides: Any) -> Symbol:
    defaults = {
        "code": "VCB",
        "exchange": Exchange.HOSE,
        "name": "Vietcombank",
        "sector": "banking",
        "listed_shares": 5_500_000_000,
    }
    defaults.update(overrides)
    return Symbol(**defaults)  # type: ignore[arg-type]


def make_tick(**overrides: Any) -> Tick:
    defaults = {
        "code": "VCB",
        "price_vnd": 88_500,
        "volume": 100,
        "occurred_at": DEFAULT_TS,
        "side": "B",
    }
    defaults.update(overrides)
    return Tick(**defaults)  # type: ignore[arg-type]


def make_bar(**overrides: Any) -> OHLCVBar:
    defaults = {
        "code": "VCB",
        "interval_seconds": 60,
        "bar_start": DEFAULT_TS,
        "open_vnd": 88_500,
        "high_vnd": 89_000,
        "low_vnd": 88_300,
        "close_vnd": 88_800,
        "volume": 1_500,
        "n_trades": 5,
    }
    defaults.update(overrides)
    return OHLCVBar(**defaults)  # type: ignore[arg-type]


def make_close_bars(
    closes: list[int], code: str = "VCB", interval_seconds: int = 60
) -> list[OHLCVBar]:
    """Build a sequence of bars whose OHLC all equal ``closes[i]``."""
    bars: list[OHLCVBar] = []
    for i, c in enumerate(closes):
        bars.append(
            OHLCVBar(
                code=code,
                interval_seconds=interval_seconds,
                bar_start=DEFAULT_TS + timedelta(seconds=i * interval_seconds),
                open_vnd=c,
                high_vnd=c,
                low_vnd=c,
                close_vnd=c,
                volume=100,
                n_trades=1,
            )
        )
    return bars


__all__ = ["DEFAULT_TS", "make_bar", "make_close_bars", "make_symbol", "make_tick"]
