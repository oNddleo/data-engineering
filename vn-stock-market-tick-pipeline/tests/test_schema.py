"""Schema invariants + exchange-rule helpers."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from vntick.schema import (
    VN_TZ,
    Exchange,
    ceiling_price,
    daily_band_bps,
    floor_price,
    is_in_session,
    lot_size,
)

from ._fixtures import DEFAULT_TS, make_bar, make_symbol, make_tick


def test_vn_tz_offset():
    offset = VN_TZ.utcoffset(None)
    assert offset is not None
    assert offset.total_seconds() == 7 * 3600


def test_daily_band_bps_per_exchange():
    assert daily_band_bps(Exchange.HOSE) == 700
    assert daily_band_bps(Exchange.HNX) == 1000
    assert daily_band_bps(Exchange.UPCOM) == 1500


def test_lot_size_uniform_100():
    for exch in Exchange:
        assert lot_size(exch) == 100


def test_ceiling_and_floor_round_trip():
    # 10_000 + 7% = 10_700; 10_000 − 7% = 9_300
    assert ceiling_price(10_000, Exchange.HOSE) == 10_700
    assert floor_price(10_000, Exchange.HOSE) == 9_300


def test_ceiling_wider_for_upcom():
    # UPCOM is ±15% so the band is wider than HOSE
    assert ceiling_price(10_000, Exchange.UPCOM) == 11_500
    assert floor_price(10_000, Exchange.UPCOM) == 8_500


def test_is_in_session_morning():
    assert is_in_session(DEFAULT_TS)


def test_is_in_session_outside_hours():
    naive = datetime(2026, 5, 4, 8, 30, tzinfo=VN_TZ)
    assert not is_in_session(naive)


def test_is_in_session_lunch_break():
    """12:00 — 13:00 is the lunch break; not a trading session."""
    lunch = datetime(2026, 5, 4, 12, 30, tzinfo=VN_TZ)
    assert not is_in_session(lunch)


def test_is_in_session_afternoon():
    pm = datetime(2026, 5, 4, 13, 30, tzinfo=VN_TZ)
    assert is_in_session(pm)


def test_is_in_session_after_close():
    closed = datetime(2026, 5, 4, 15, 0, tzinfo=VN_TZ)
    assert not is_in_session(closed)


def test_is_in_session_requires_tz():
    with pytest.raises(ValueError):
        is_in_session(datetime(2026, 5, 4, 10, 0))


def test_is_in_session_accepts_utc():
    """09:00 VN = 02:00 UTC — must convert before checking."""
    utc = datetime(2026, 5, 4, 2, 30, tzinfo=timezone.utc)
    assert is_in_session(utc)


def test_symbol_rejects_lowercase_code():
    with pytest.raises(ValueError, match="ASCII uppercase"):
        make_symbol(code="vcb")


def test_symbol_rejects_non_ascii_code():
    with pytest.raises(ValueError):
        make_symbol(code="VCB✓")


def test_symbol_rejects_zero_listed_shares():
    with pytest.raises(ValueError):
        make_symbol(listed_shares=0)


def test_tick_rejects_zero_price():
    with pytest.raises(ValueError):
        make_tick(price_vnd=0)


def test_tick_rejects_zero_volume():
    with pytest.raises(ValueError):
        make_tick(volume=0)


def test_tick_rejects_naive_datetime():
    with pytest.raises(ValueError):
        make_tick(occurred_at=datetime(2026, 5, 4, 10, 0))


def test_tick_rejects_invalid_side():
    with pytest.raises(ValueError, match="side"):
        make_tick(side="X")


def test_bar_rejects_inconsistent_low():
    """low > min(open, close) must raise."""
    with pytest.raises(ValueError, match="low"):
        make_bar(low_vnd=89_000, open_vnd=88_500, close_vnd=88_800)


def test_bar_rejects_inconsistent_high():
    with pytest.raises(ValueError, match="high"):
        make_bar(high_vnd=88_500, open_vnd=88_500, close_vnd=89_000)


def test_bar_accepts_degenerate_doji():
    """Single-tick bar where OHLC all equal — perfectly legal."""
    b = make_bar(open_vnd=100_000, high_vnd=100_000, low_vnd=100_000, close_vnd=100_000)
    assert b.open_vnd == b.close_vnd == 100_000


def test_bar_rejects_zero_price():
    with pytest.raises(ValueError):
        make_bar(open_vnd=0, low_vnd=0)
