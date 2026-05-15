"""Hypothesis properties — invariants of resampler + indicators."""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from vntick.indicators import bollinger, sma
from vntick.resampler import resample

from ._fixtures import make_close_bars, make_tick


@st.composite
def _tick_list(draw: st.DrawFn) -> list:  # type: ignore[type-arg]
    from datetime import timedelta

    from ._fixtures import DEFAULT_TS

    n = draw(st.integers(min_value=1, max_value=30))
    prices = draw(st.lists(st.integers(min_value=1_000, max_value=200_000), min_size=n, max_size=n))
    return [
        make_tick(price_vnd=p, volume=100, occurred_at=DEFAULT_TS + timedelta(seconds=i * 30))
        for i, p in enumerate(prices)
    ]


@given(ticks=_tick_list())
@settings(max_examples=50, deadline=None)
def test_bar_ohlc_invariants_always_hold(ticks: list) -> None:  # type: ignore[type-arg]
    """For any tick stream, the resampler produces OHLC-consistent bars."""
    bars = resample(ticks, interval="1m")
    for b in bars:
        assert b.low_vnd <= b.open_vnd <= b.high_vnd
        assert b.low_vnd <= b.close_vnd <= b.high_vnd
        assert b.n_trades >= 1
        # Each tick contributes at least 1 share of volume.
        assert b.volume >= b.n_trades


@given(ticks=_tick_list())
@settings(max_examples=50, deadline=None)
def test_bar_volume_equals_tick_sum(ticks: list) -> None:  # type: ignore[type-arg]
    """Total volume across bars equals total volume across ticks."""
    bars = resample(ticks, interval="1m")
    assert sum(b.volume for b in bars) == sum(t.volume for t in ticks)


@given(ticks=_tick_list())
@settings(max_examples=50, deadline=None)
def test_bar_trade_count_equals_tick_count(ticks: list) -> None:  # type: ignore[type-arg]
    bars = resample(ticks, interval="1m")
    assert sum(b.n_trades for b in bars) == len(ticks)


@given(
    closes=st.lists(st.integers(min_value=1_000, max_value=200_000), min_size=5, max_size=50),
    period=st.integers(min_value=2, max_value=5),
)
@settings(max_examples=30, deadline=None)
def test_sma_within_minmax_of_window(closes: list[int], period: int) -> None:
    """SMA at index i is bounded by the min/max of the window."""
    if len(closes) < period:
        return
    bars = make_close_bars(closes)
    out = sma(bars, period=period)
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1 : i + 1]
        v = out[i]
        assert v is not None
        assert min(window) <= v <= max(window)


@given(
    closes=st.lists(st.integers(min_value=1_000, max_value=200_000), min_size=20, max_size=40),
)
@settings(max_examples=30, deadline=None)
def test_bollinger_upper_ge_middle_ge_lower(closes: list[int]) -> None:
    """Upper band ≥ middle ≥ lower for every Bollinger output."""
    bars = make_close_bars(closes)
    out = bollinger(bars, period=20, n_std=2.0)
    for b in out:
        if b is None:
            continue
        assert b.upper >= b.middle >= b.lower
