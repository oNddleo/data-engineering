"""Schema validation: Exchange, Ticker, OHLCBar, Order."""

from __future__ import annotations

import pytest

from vnstock.schema import (
    AnomalyKind,
    Exchange,
    OrderKind,
    OrderSide,
    Ticker,
)

from ._fixtures import make_bar, make_order

# ---------- Exchange + enums -----------------------------------------------


def test_exchanges_complete() -> None:
    assert {e.value for e in Exchange} == {"HOSE", "HNX", "UPCOM"}


def test_order_kinds_complete() -> None:
    assert {k.value for k in OrderKind} == {"LO", "MP", "ATO", "ATC"}


def test_order_sides_complete() -> None:
    assert {s.value for s in OrderSide} == {"BUY", "SELL"}


def test_anomaly_kinds_complete() -> None:
    assert {k.value for k in AnomalyKind} == {
        "PRICE_BAND_BREACH",
        "VOLUME_SPIKE",
        "PRICE_GAP",
    }


# ---------- Ticker ---------------------------------------------------------


def test_ticker_basic() -> None:
    t = Ticker(
        symbol="VIC",
        exchange=Exchange.HOSE,
        name_vi="Vingroup",
        name_en="Vingroup",
    )
    assert t.symbol == "VIC"


def test_ticker_rejects_bad_symbol() -> None:
    """Symbol must be 2-5 uppercase ASCII letters."""
    for bad in ("vic", "VI", "VIC123", "V", "vic ", ""):
        with pytest.raises(ValueError, match="symbol"):
            Ticker(symbol=bad, exchange=Exchange.HOSE, name_vi="x", name_en="x")


def test_ticker_rejects_empty_name() -> None:
    with pytest.raises(ValueError, match="name_vi"):
        Ticker(symbol="VIC", exchange=Exchange.HOSE, name_vi="", name_en="x")


# ---------- OHLCBar --------------------------------------------------------


def test_bar_basic() -> None:
    b = make_bar()
    assert b.symbol == "VIC"
    assert b.daily_change_vnd == 1_500  # close 61500 vs ref 60000


def test_bar_daily_change_bps() -> None:
    """1500/60000 = 0.025 = 250 bps."""
    b = make_bar()
    assert b.daily_change_bps == 250


def test_bar_rejects_high_below_open() -> None:
    with pytest.raises(ValueError, match="high"):
        make_bar(high_vnd=59_000)


def test_bar_rejects_low_above_close() -> None:
    with pytest.raises(ValueError, match="low"):
        make_bar(low_vnd=62_500)


@pytest.mark.parametrize(
    "field",
    ["open_vnd", "high_vnd", "low_vnd", "close_vnd", "reference_price_vnd"],
)
def test_bar_rejects_zero_prices(field: str) -> None:
    """Each price field must be strictly positive.

    Pass all four prices explicitly so the fixture's auto-scaling
    doesn't paper over the field we're trying to set to zero.
    """
    overrides: dict[str, int] = {
        "open_vnd": 60_000,
        "high_vnd": 62_000,
        "low_vnd": 59_500,
        "close_vnd": 61_500,
        "reference_price_vnd": 60_000,
    }
    overrides[field] = 0
    with pytest.raises(ValueError, match=field):
        make_bar(**overrides)


def test_bar_zero_volume_allowed() -> None:
    """A zero-volume bar is valid (illiquid ticker, no trades)."""
    b = make_bar(volume=0)
    assert b.volume == 0


def test_bar_rejects_negative_volume() -> None:
    with pytest.raises(ValueError, match="volume"):
        make_bar(volume=-1)


# ---------- Order ----------------------------------------------------------


def test_order_lo_basic() -> None:
    o = make_order()
    assert o.kind is OrderKind.LO
    assert o.limit_price_vnd == 60_000


def test_order_mp_requires_zero_price() -> None:
    with pytest.raises(ValueError, match="MP"):
        make_order(kind=OrderKind.MP, limit_price_vnd=60_000)


def test_order_lo_requires_nonzero_price() -> None:
    with pytest.raises(ValueError, match="LO"):
        make_order(kind=OrderKind.LO, limit_price_vnd=0)


def test_order_ato_zero_price() -> None:
    o = make_order(kind=OrderKind.ATO, limit_price_vnd=0)
    assert o.kind is OrderKind.ATO


def test_order_atc_zero_price() -> None:
    o = make_order(kind=OrderKind.ATC, limit_price_vnd=0)
    assert o.kind is OrderKind.ATC


def test_order_rejects_zero_quantity() -> None:
    with pytest.raises(ValueError, match="quantity"):
        make_order(quantity=0)


def test_order_rejects_negative_price() -> None:
    with pytest.raises(ValueError, match="limit_price_vnd"):
        make_order(limit_price_vnd=-1)
