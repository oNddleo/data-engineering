"""OHLCV resampler behaviour."""

from __future__ import annotations

from datetime import timedelta

import pytest

from vntick.resampler import INTERVAL_SECONDS, parse_interval, resample

from ._fixtures import DEFAULT_TS, make_tick


def test_parse_interval_known():
    assert parse_interval("1m") == 60
    assert parse_interval("5m") == 300
    assert parse_interval("1h") == 3600


def test_parse_interval_unknown():
    with pytest.raises(ValueError):
        parse_interval("7m")


def test_intervals_map_to_seconds():
    assert INTERVAL_SECONDS["1d"] == 86400


def test_resample_single_tick_produces_doji():
    """One tick → one bar where OHLC all equal the tick price."""
    bars = resample([make_tick(price_vnd=100_000, volume=200)], interval="1m")
    assert len(bars) == 1
    b = bars[0]
    assert b.open_vnd == b.close_vnd == b.high_vnd == b.low_vnd == 100_000
    assert b.volume == 200
    assert b.n_trades == 1


def test_resample_aggregates_intra_bar_ticks():
    ticks = [
        make_tick(price_vnd=100_000, volume=100, occurred_at=DEFAULT_TS + timedelta(seconds=5)),
        make_tick(price_vnd=102_000, volume=200, occurred_at=DEFAULT_TS + timedelta(seconds=15)),
        make_tick(price_vnd=99_000, volume=300, occurred_at=DEFAULT_TS + timedelta(seconds=30)),
        make_tick(price_vnd=101_000, volume=100, occurred_at=DEFAULT_TS + timedelta(seconds=55)),
    ]
    [bar] = resample(ticks, interval="1m")
    assert bar.open_vnd == 100_000
    assert bar.close_vnd == 101_000
    assert bar.high_vnd == 102_000
    assert bar.low_vnd == 99_000
    assert bar.volume == 700
    assert bar.n_trades == 4


def test_resample_separates_bars_by_interval():
    """Ticks straddling a minute boundary land in two bars."""
    ticks = [
        make_tick(occurred_at=DEFAULT_TS),  # 09:30:00
        make_tick(occurred_at=DEFAULT_TS + timedelta(seconds=30)),  # 09:30:30
        make_tick(occurred_at=DEFAULT_TS + timedelta(seconds=70)),  # 09:31:10
        make_tick(occurred_at=DEFAULT_TS + timedelta(seconds=90)),  # 09:31:30
    ]
    bars = resample(ticks, interval="1m")
    assert len(bars) == 2
    assert bars[0].n_trades == 2
    assert bars[1].n_trades == 2


def test_resample_bars_aligned_to_5m_boundaries():
    """A 5-minute bar starts on :00 / :05 / :10."""
    # Tick at 09:32:30 should bucket into the 09:30 5m bar.
    t = make_tick(occurred_at=DEFAULT_TS + timedelta(seconds=150))
    [bar] = resample([t], interval="5m")
    assert bar.bar_start.minute == 30
    assert bar.bar_start.second == 0


def test_resample_separates_codes():
    ticks = [
        make_tick(code="VCB"),
        make_tick(code="VIC", price_vnd=42_000),
    ]
    bars = resample(ticks, interval="1m")
    assert len(bars) == 2
    assert {b.code for b in bars} == {"VCB", "VIC"}


def test_resample_sorts_output_by_code_then_time():
    t1 = make_tick(code="VIC", occurred_at=DEFAULT_TS + timedelta(minutes=2))
    t2 = make_tick(code="VCB", occurred_at=DEFAULT_TS + timedelta(minutes=1))
    bars = resample([t1, t2], interval="1m")
    # Sorted by (code, bar_start): VCB first, then VIC.
    assert bars[0].code == "VCB"
    assert bars[1].code == "VIC"


def test_resample_empty_input():
    assert resample([], interval="5m") == []


def test_resample_unsorted_ticks_still_correct():
    """Resampler must sort ticks internally so open/close are right."""
    ticks = [
        make_tick(price_vnd=200_000, volume=100, occurred_at=DEFAULT_TS + timedelta(seconds=30)),
        make_tick(
            price_vnd=100_000, volume=100, occurred_at=DEFAULT_TS + timedelta(seconds=10)
        ),  # earlier
    ]
    [bar] = resample(ticks, interval="1m")
    # The 09:30:10 tick is the open (earlier).
    assert bar.open_vnd == 100_000
    assert bar.close_vnd == 200_000


def test_resample_daily_floors_to_midnight_vn():
    """A 1-day bar starts at 00:00 VN_TZ regardless of trade time."""
    t = make_tick(occurred_at=DEFAULT_TS + timedelta(hours=4))  # 13:30 VN
    [bar] = resample([t], interval="1d")
    assert bar.bar_start.hour == 0
    assert bar.bar_start.minute == 0
