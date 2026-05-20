"""Multi-day aggregator: TickerStats, moving averages, VWAP."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from vnstock.aggregator import (
    aggregate_ticker_stats,
    moving_average_close,
    volume_weighted_avg_price,
)
from vnstock.schema import Exchange

from ._fixtures import make_bar


def _bar_at(day: int, **overrides: object) -> object:
    """Build a bar for a specific day offset from 2025-01-06."""
    base = date(2025, 1, 6)
    defaults = {"date": base + timedelta(days=day)}
    defaults.update(overrides)
    return make_bar(**defaults)


def test_stats_single_ticker() -> None:
    bars = [make_bar(date=date(2025, 1, 6 + i)) for i in range(5)]
    stats = aggregate_ticker_stats(bars)
    assert len(stats) == 1
    assert stats[0].symbol == "VIC"
    assert stats[0].n_bars == 5


def test_stats_multiple_tickers() -> None:
    bars = [
        make_bar(symbol="VIC"),
        make_bar(symbol="VNM"),
    ]
    stats = aggregate_ticker_stats(bars)
    assert len(stats) == 2
    assert {s.symbol for s in stats} == {"VIC", "VNM"}


def test_stats_high_water_mark() -> None:
    bars = [
        make_bar(high_vnd=62_000),
        make_bar(date=date(2025, 1, 7), high_vnd=65_000),
        make_bar(date=date(2025, 1, 8), high_vnd=63_000),
    ]
    stats = aggregate_ticker_stats(bars)
    assert stats[0].high_water_mark_vnd == 65_000


def test_stats_low_water_mark() -> None:
    bars = [
        make_bar(low_vnd=58_000),
        make_bar(date=date(2025, 1, 7), low_vnd=55_000),
        make_bar(date=date(2025, 1, 8), low_vnd=57_000),
    ]
    stats = aggregate_ticker_stats(bars)
    assert stats[0].low_water_mark_vnd == 55_000


def test_stats_total_volume_sums() -> None:
    bars = [
        make_bar(volume=1_000_000),
        make_bar(date=date(2025, 1, 7), volume=2_000_000),
    ]
    stats = aggregate_ticker_stats(bars)
    assert stats[0].total_volume == 3_000_000


def test_stats_period_change() -> None:
    bars = [
        make_bar(date=date(2025, 1, 6), close_vnd=60_000),
        make_bar(
            date=date(2025, 1, 7),
            close_vnd=63_000,
            high_vnd=63_500,
        ),
    ]
    stats = aggregate_ticker_stats(bars)
    assert stats[0].period_change_vnd == 3_000


def test_stats_sorted_by_exchange_symbol() -> None:
    bars = [
        make_bar(symbol="VNM", exchange=Exchange.HOSE),
        make_bar(symbol="ACB", exchange=Exchange.HNX),
        make_bar(symbol="VIC", exchange=Exchange.HOSE),
    ]
    stats = aggregate_ticker_stats(bars)
    # HNX < HOSE alphabetically, then symbols sorted within exchange.
    assert [s.symbol for s in stats] == ["ACB", "VIC", "VNM"]


def test_stats_empty() -> None:
    assert aggregate_ticker_stats([]) == []


# ---------- Moving averages -----------------------------------------------


def test_moving_average_basic() -> None:
    bars = [
        make_bar(date=date(2025, 1, 6 + i), close_vnd=close)
        for i, close in enumerate([10_000, 20_000, 30_000, 40_000, 50_000])
    ]
    avgs = moving_average_close(bars, n=3)
    assert avgs == [None, None, 20_000, 30_000, 40_000]


def test_moving_average_window_one() -> None:
    """n=1 → identity (each entry is its own close)."""
    bars = [make_bar(date=date(2025, 1, 6 + i), close_vnd=10_000 + i * 1_000) for i in range(3)]
    avgs = moving_average_close(bars, n=1)
    assert avgs == [10_000, 11_000, 12_000]


def test_moving_average_window_too_large() -> None:
    """Window > input length → all None."""
    bars = [make_bar()]
    assert moving_average_close(bars, n=5) == [None]


def test_moving_average_empty() -> None:
    assert moving_average_close([], n=3) == []


def test_moving_average_rejects_zero_n() -> None:
    with pytest.raises(ValueError, match="n"):
        moving_average_close([], n=0)


def test_moving_average_handles_unsorted_input() -> None:
    """The function sorts by date internally."""
    bars = [
        make_bar(date=date(2025, 1, 8), close_vnd=30_000),
        make_bar(date=date(2025, 1, 6), close_vnd=10_000),
        make_bar(date=date(2025, 1, 7), close_vnd=20_000),
    ]
    avgs = moving_average_close(bars, n=2)
    assert avgs == [None, 15_000, 25_000]


# ---------- VWAP -----------------------------------------------------------


def test_vwap_basic() -> None:
    bars = [
        make_bar(close_vnd=60_000, volume=1_000_000),
        make_bar(date=date(2025, 1, 7), close_vnd=70_000, volume=2_000_000),
    ]
    # VWAP = (60000*1M + 70000*2M) / 3M = 200_000_000_000 / 3_000_000 ≈ 66,666
    assert volume_weighted_avg_price(bars) == 66_666


def test_vwap_uniform_volume() -> None:
    """VWAP with equal volumes equals the average."""
    bars = [
        make_bar(close_vnd=50_000, volume=1_000),
        make_bar(date=date(2025, 1, 7), close_vnd=70_000, volume=1_000),
    ]
    assert volume_weighted_avg_price(bars) == 60_000


def test_vwap_rejects_empty() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        volume_weighted_avg_price([])


def test_vwap_rejects_zero_volume() -> None:
    bars = [make_bar(volume=0)]
    with pytest.raises(ValueError, match="zero"):
        volume_weighted_avg_price(bars)
