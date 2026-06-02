"""OHLC bar aggregation from intraday trades."""

from __future__ import annotations

from datetime import date

import pytest

from vnstock.bars import aggregate_bar
from vnstock.schema import Exchange

from ._fixtures import make_trade


def test_trade_basic() -> None:
    t = make_trade()
    assert t.price_vnd == 60_000


def test_trade_rejects_zero_price() -> None:
    with pytest.raises(ValueError, match="price_vnd"):
        make_trade(price_vnd=0)


def test_trade_rejects_zero_volume() -> None:
    with pytest.raises(ValueError, match="volume"):
        make_trade(volume=0)


def test_trade_rejects_negative_ts() -> None:
    with pytest.raises(ValueError, match="ts_ms"):
        make_trade(ts_ms=-1)


# ---------- aggregate_bar --------------------------------------------------


def test_aggregate_single_trade() -> None:
    """One trade → open=high=low=close, volume=trade.volume."""
    t = make_trade(price_vnd=60_000, volume=100)
    bar = aggregate_bar([t], date(2025, 5, 19), reference_price_vnd=60_000)
    assert bar.open_vnd == 60_000
    assert bar.high_vnd == 60_000
    assert bar.low_vnd == 60_000
    assert bar.close_vnd == 60_000
    assert bar.volume == 100


def test_aggregate_multiple_trades() -> None:
    trades = [
        make_trade(ts_ms=1_000, price_vnd=60_000, volume=100),
        make_trade(ts_ms=2_000, price_vnd=62_000, volume=200),
        make_trade(ts_ms=3_000, price_vnd=58_000, volume=150),
        make_trade(ts_ms=4_000, price_vnd=61_500, volume=300),
    ]
    bar = aggregate_bar(trades, date(2025, 5, 19), reference_price_vnd=60_000)
    assert bar.open_vnd == 60_000  # first by ts_ms
    assert bar.close_vnd == 61_500  # last by ts_ms
    assert bar.high_vnd == 62_000
    assert bar.low_vnd == 58_000
    assert bar.volume == 750


def test_aggregate_handles_out_of_order_trades() -> None:
    """aggregate_bar sorts by ts_ms internally."""
    trades = [
        make_trade(ts_ms=4_000, price_vnd=61_500),  # later in time
        make_trade(ts_ms=1_000, price_vnd=60_000),  # earlier
    ]
    bar = aggregate_bar(trades, date(2025, 5, 19), reference_price_vnd=60_000)
    assert bar.open_vnd == 60_000
    assert bar.close_vnd == 61_500


def test_aggregate_rejects_empty() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        aggregate_bar([], date(2025, 5, 19), reference_price_vnd=60_000)


def test_aggregate_rejects_mixed_symbols() -> None:
    trades = [
        make_trade(symbol="VIC"),
        make_trade(symbol="VNM"),
    ]
    with pytest.raises(ValueError, match="symbol"):
        aggregate_bar(trades, date(2025, 5, 19), reference_price_vnd=60_000)


def test_aggregate_rejects_mixed_exchanges() -> None:
    trades = [
        make_trade(exchange=Exchange.HOSE),
        make_trade(exchange=Exchange.HNX),
    ]
    with pytest.raises(ValueError, match="symbol"):
        aggregate_bar(trades, date(2025, 5, 19), reference_price_vnd=60_000)


def test_aggregate_rejects_zero_ref() -> None:
    with pytest.raises(ValueError, match="reference"):
        aggregate_bar([make_trade()], date(2025, 5, 19), reference_price_vnd=0)


def test_aggregate_preserves_symbol_exchange() -> None:
    t = make_trade(symbol="VNM", exchange=Exchange.HOSE)
    bar = aggregate_bar([t], date(2025, 5, 19), reference_price_vnd=70_000)
    assert bar.symbol == "VNM"
    assert bar.exchange is Exchange.HOSE
