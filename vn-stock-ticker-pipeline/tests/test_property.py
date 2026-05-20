"""Hypothesis property tests for VN-stock invariants."""

from __future__ import annotations

from datetime import date, timedelta

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from vnstock.aggregator import (
    aggregate_ticker_stats,
    moving_average_close,
    volume_weighted_avg_price,
)
from vnstock.io_jsonl import bar_from_dict, bar_to_dict
from vnstock.pricing import (
    ceiling_floor,
    is_valid_lot,
    is_valid_tick,
    is_within_band,
    round_to_tick,
    tick_size,
)
from vnstock.schema import Exchange, OHLCBar


@st.composite
def ohlc_bar(draw: st.DrawFn) -> OHLCBar:
    """An OHLC bar with realistic prices."""
    exchange = draw(st.sampled_from(list(Exchange)))
    symbol = draw(st.sampled_from(["VIC", "VNM", "FPT", "ACB", "BSR", "TCB"]))
    # Snap reference price to a 100-VND tick to avoid sub-tick refs.
    raw_ref = draw(st.integers(min_value=10_000, max_value=200_000))
    ref = (raw_ref // 100) * 100
    open_p = ref + draw(st.integers(min_value=-2_000, max_value=2_000))
    close_p = ref + draw(st.integers(min_value=-2_000, max_value=2_000))
    high_p = max(open_p, close_p) + draw(st.integers(min_value=0, max_value=500))
    low_p = max(1, min(open_p, close_p) - draw(st.integers(min_value=0, max_value=500)))
    day = draw(st.integers(min_value=0, max_value=29))
    return OHLCBar(
        symbol=symbol,
        exchange=exchange,
        date=date(2025, 1, 6) + timedelta(days=day),
        open_vnd=open_p,
        high_vnd=high_p,
        low_vnd=low_p,
        close_vnd=close_p,
        volume=draw(st.integers(min_value=0, max_value=10_000_000)),
        reference_price_vnd=ref,
    )


# ---------- Tick size + lot size invariants -------------------------------


@given(
    st.sampled_from(list(Exchange)),
    st.integers(min_value=1, max_value=1_000_000),
)
def test_tick_size_always_positive(exchange: Exchange, price: int) -> None:
    """Tick size is always > 0 for any valid price."""
    assert tick_size(price, exchange) > 0


@given(
    st.sampled_from(list(Exchange)),
    st.integers(min_value=1, max_value=1_000_000),
)
def test_round_down_le_input(exchange: Exchange, price: int) -> None:
    """round_to_tick(p, down) ≤ p."""
    assert round_to_tick(price, exchange, mode="down") <= price


@given(
    st.sampled_from(list(Exchange)),
    st.integers(min_value=1, max_value=1_000_000),
)
def test_round_up_ge_input(exchange: Exchange, price: int) -> None:
    """round_to_tick(p, up) ≥ p."""
    assert round_to_tick(price, exchange, mode="up") >= price


@given(
    st.sampled_from(list(Exchange)),
    st.integers(min_value=1, max_value=1_000_000),
)
def test_round_down_is_valid_tick(exchange: Exchange, price: int) -> None:
    """Anything rounded down should pass is_valid_tick."""
    snapped = round_to_tick(price, exchange, mode="down")
    if snapped > 0:
        assert is_valid_tick(snapped, exchange)


@given(
    st.sampled_from(list(Exchange)),
    st.integers(min_value=1, max_value=1_000_000),
)
def test_lot_100_always_valid(exchange: Exchange, multiplier: int) -> None:
    """Any positive multiple of 100 is a valid lot."""
    assert is_valid_lot(100 * multiplier, exchange)


# ---------- Price band invariants -----------------------------------------


@given(
    st.sampled_from(list(Exchange)),
    st.integers(min_value=100, max_value=1_000_000),
)
def test_band_floor_le_ref_le_ceiling(exchange: Exchange, ref: int) -> None:
    """floor ≤ reference ≤ ceiling (modulo tick rounding)."""
    ceiling, floor = ceiling_floor(ref, exchange)
    assert floor <= ceiling
    # Reference is roughly between floor and ceiling; allow rounding slack.
    assert floor - 200 <= ref <= ceiling + 200


@given(
    st.sampled_from(list(Exchange)),
    st.integers(min_value=100, max_value=1_000_000),
)
def test_band_within_at_ref(exchange: Exchange, ref: int) -> None:
    """The reference price is always within its own band."""
    snapped = round_to_tick(ref, exchange, mode="down")
    if snapped <= 0:
        return
    assert is_within_band(snapped, snapped, exchange)


@given(
    st.sampled_from(list(Exchange)),
    st.integers(min_value=100, max_value=1_000_000),
)
def test_ipo_band_wider_than_normal(exchange: Exchange, ref: int) -> None:
    """IPO-day band is always wider than the normal band."""
    normal_c, normal_f = ceiling_floor(ref, exchange)
    ipo_c, ipo_f = ceiling_floor(ref, exchange, is_ipo_day=True)
    assert ipo_c >= normal_c
    assert ipo_f <= normal_f


# ---------- OHLC bar invariants -------------------------------------------


@given(ohlc_bar())
@settings(max_examples=80)
def test_bar_high_ge_others(b: OHLCBar) -> None:
    assert b.high_vnd >= max(b.open_vnd, b.close_vnd, b.low_vnd)


@given(ohlc_bar())
@settings(max_examples=80)
def test_bar_low_le_others(b: OHLCBar) -> None:
    assert b.low_vnd <= min(b.open_vnd, b.close_vnd, b.high_vnd)


@given(ohlc_bar())
@settings(max_examples=80)
def test_bar_volume_non_negative(b: OHLCBar) -> None:
    assert b.volume >= 0


# ---------- JSONL round-trip ----------------------------------------------


@given(ohlc_bar())
@settings(max_examples=60)
def test_bar_jsonl_roundtrip(b: OHLCBar) -> None:
    assert bar_from_dict(bar_to_dict(b)) == b


# ---------- Aggregator conservation ---------------------------------------


@given(st.lists(ohlc_bar(), min_size=1, max_size=20))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=20)
def test_stats_volume_sums(bars: list[OHLCBar]) -> None:
    """Sum of per-ticker total_volume equals sum of bar.volume."""
    # Dedup by (symbol, exchange, date) to satisfy schema.
    seen: set[tuple[str, str, date]] = set()
    unique: list[OHLCBar] = []
    for b in bars:
        key = (b.symbol, b.exchange.value, b.date)
        if key in seen:
            continue
        seen.add(key)
        unique.append(b)
    stats = aggregate_ticker_stats(unique)
    total_stats = sum(s.total_volume for s in stats)
    total_bars = sum(b.volume for b in unique)
    assert total_stats == total_bars


@given(st.lists(ohlc_bar(), min_size=1, max_size=20))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=20)
def test_stats_high_water_marks_max(bars: list[OHLCBar]) -> None:
    """high_water_mark = max(b.high_vnd) per group."""
    seen: set[tuple[str, str, date]] = set()
    unique: list[OHLCBar] = []
    for b in bars:
        key = (b.symbol, b.exchange.value, b.date)
        if key in seen:
            continue
        seen.add(key)
        unique.append(b)
    stats = aggregate_ticker_stats(unique)
    for s in stats:
        group = [b for b in unique if b.symbol == s.symbol and b.exchange is s.exchange]
        assert s.high_water_mark_vnd == max(b.high_vnd for b in group)


# ---------- Moving average ------------------------------------------------


@given(
    st.lists(ohlc_bar(), min_size=1, max_size=20),
    st.integers(min_value=1, max_value=10),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=20)
def test_moving_average_length(bars: list[OHLCBar], n: int) -> None:
    """Output length matches input length."""
    avgs = moving_average_close(bars, n=n)
    assert len(avgs) == len(bars)


@given(st.lists(ohlc_bar(), min_size=1, max_size=10))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=20)
def test_moving_average_window_one_is_close(bars: list[OHLCBar]) -> None:
    """MA(1) just returns each close in date order."""
    avgs = moving_average_close(bars, n=1)
    ordered = sorted(bars, key=lambda b: b.date)
    assert avgs == [b.close_vnd for b in ordered]


# ---------- VWAP ----------------------------------------------------------


@given(st.lists(ohlc_bar(), min_size=1, max_size=10))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=20)
def test_vwap_between_min_and_max_close(bars: list[OHLCBar]) -> None:
    """VWAP is bounded by the min and max close prices."""
    # Skip degenerate all-zero-volume cases.
    total_vol = sum(b.volume for b in bars)
    if total_vol == 0:
        return
    vwap = volume_weighted_avg_price(bars)
    min_close = min(b.close_vnd for b in bars)
    max_close = max(b.close_vnd for b in bars)
    assert min_close <= vwap <= max_close
