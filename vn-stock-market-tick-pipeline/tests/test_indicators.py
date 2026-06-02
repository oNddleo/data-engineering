"""Indicator math."""

from __future__ import annotations

import pytest

from vntick.indicators import bollinger, ema, macd, rsi, sma

from ._fixtures import make_close_bars


def test_sma_returns_none_until_full_window():
    bars = make_close_bars([100, 101, 102, 103, 104])
    out = sma(bars, period=3)
    assert out[:2] == [None, None]
    assert out[2] == 101.0  # mean(100, 101, 102)
    assert out[3] == 102.0
    assert out[4] == 103.0


def test_sma_validates_period():
    with pytest.raises(ValueError):
        sma([], period=0)


def test_sma_short_history_all_none():
    bars = make_close_bars([100, 101])
    assert sma(bars, period=5) == [None, None]


def test_ema_seeds_with_sma():
    bars = make_close_bars([100, 100, 100, 100])
    out = ema(bars, period=4)
    # First three are None, fourth is the SMA seed.
    assert out[:3] == [None, None, None]
    assert out[3] == 100.0


def test_ema_validates_period():
    with pytest.raises(ValueError):
        ema([], period=0)


def test_ema_constant_input_constant_output():
    """A flat price series gives a flat EMA equal to that price."""
    bars = make_close_bars([100_000] * 10)
    out = ema(bars, period=5)
    for v in out[4:]:
        assert v == 100_000.0


def test_rsi_validates_period():
    with pytest.raises(ValueError):
        rsi([], period=1)


def test_rsi_extreme_uptrend_approaches_100():
    """Monotonically rising prices → RSI → 100."""
    bars = make_close_bars(list(range(100, 130)))
    out = rsi(bars, period=14)
    # First 14 are None.
    assert out[:14] == [None] * 14
    last = out[-1]
    assert last is not None
    assert last == 100.0


def test_rsi_extreme_downtrend_approaches_zero():
    bars = make_close_bars(list(range(200, 170, -1)))
    out = rsi(bars, period=14)
    last = out[-1]
    assert last is not None
    assert last == 0.0


def test_rsi_short_history_all_none():
    bars = make_close_bars([100, 101, 102])
    assert rsi(bars, period=14) == [None, None, None]


def test_macd_validates_periods():
    with pytest.raises(ValueError):
        macd([], fast=26, slow=12)  # swapped
    with pytest.raises(ValueError):
        macd([], signal=0)


def test_macd_constant_input_zero_macd():
    """Flat prices ⇒ EMA(12) == EMA(26) ⇒ MACD line is 0."""
    bars = make_close_bars([100_000] * 40)
    out = macd(bars, fast=12, slow=26, signal=9)
    # Last point is well past warmup; macd and signal both ~ 0.
    last = out[-1]
    assert last is not None
    assert abs(last.macd) < 1e-6
    assert abs(last.histogram) < 1e-6


def test_bollinger_validates():
    with pytest.raises(ValueError):
        bollinger([], period=1)
    with pytest.raises(ValueError):
        bollinger([], period=20, n_std=0)


def test_bollinger_constant_input_zero_width():
    """Flat price ⇒ σ = 0 ⇒ all three bands collapse to the price."""
    bars = make_close_bars([100_000] * 25)
    out = bollinger(bars, period=20, n_std=2.0)
    last = out[-1]
    assert last is not None
    assert last.upper == last.middle == last.lower == 100_000.0


def test_bollinger_short_history_all_none():
    bars = make_close_bars([100, 101, 102])
    assert bollinger(bars, period=20) == [None, None, None]


def test_bollinger_widens_with_volatility():
    """Higher-variance series produces wider bands than flat series."""
    flat = make_close_bars([100_000] * 25)
    swung = make_close_bars([100_000 + (-1) ** i * 5_000 for i in range(25)])
    flat_band = bollinger(flat, period=20)[-1]
    swung_band = bollinger(swung, period=20)[-1]
    assert flat_band is not None and swung_band is not None
    flat_width = flat_band.upper - flat_band.lower
    swung_width = swung_band.upper - swung_band.lower
    assert swung_width > flat_width


def test_sma_matches_manual_mean():
    bars = make_close_bars([10, 20, 30, 40, 50])
    out = sma(bars, period=5)
    assert out[-1] == 30.0  # (10+20+30+40+50)/5
