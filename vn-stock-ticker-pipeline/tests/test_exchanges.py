"""Exchange + ticker directory tests."""

from __future__ import annotations

from vnstock.exchanges import all_exchanges, profile_for
from vnstock.schema import Exchange
from vnstock.tickers import (
    all_tickers,
    hnx_leaders,
    ticker_for,
    tickers_on,
    upcom_leaders,
    vn30,
)


def test_three_exchanges_bundled() -> None:
    assert len(all_exchanges()) == 3


def test_hose_band_7_percent() -> None:
    p = profile_for(Exchange.HOSE)
    assert p.price_band_bps == 700


def test_hnx_band_10_percent() -> None:
    p = profile_for(Exchange.HNX)
    assert p.price_band_bps == 1_000


def test_upcom_band_15_percent() -> None:
    p = profile_for(Exchange.UPCOM)
    assert p.price_band_bps == 1_500


def test_hose_ipo_band_20_percent() -> None:
    p = profile_for(Exchange.HOSE)
    assert p.ipo_band_bps == 2_000


def test_all_lot_sizes_100() -> None:
    """Since 2017 standardisation, all 3 exchanges use lot=100."""
    for p in all_exchanges():
        assert p.lot_size == 100


def test_hose_tiered_tick() -> None:
    """HOSE uses tiered tick (flat_tick_vnd == 0 sentinel)."""
    assert profile_for(Exchange.HOSE).flat_tick_vnd == 0


def test_hnx_flat_tick_100() -> None:
    assert profile_for(Exchange.HNX).flat_tick_vnd == 100


# ---------- Tickers --------------------------------------------------------


def test_vn30_has_30_constituents() -> None:
    assert len(vn30()) == 30


def test_all_vn30_on_hose() -> None:
    for t in vn30():
        assert t.exchange is Exchange.HOSE


def test_hnx_leaders_nonempty() -> None:
    assert len(hnx_leaders()) > 0
    for t in hnx_leaders():
        assert t.exchange is Exchange.HNX


def test_upcom_leaders_nonempty() -> None:
    assert len(upcom_leaders()) > 0
    for t in upcom_leaders():
        assert t.exchange is Exchange.UPCOM


def test_ticker_for_known_symbol() -> None:
    t = ticker_for("VIC")
    assert t is not None
    assert t.exchange is Exchange.HOSE


def test_ticker_for_case_insensitive() -> None:
    assert ticker_for("vic") is not None
    assert ticker_for("Vic") is not None


def test_ticker_for_unknown() -> None:
    assert ticker_for("XYZ123") is None


def test_tickers_on_hose() -> None:
    on_hose = tickers_on(Exchange.HOSE)
    assert len(on_hose) == 30  # VN30 only in our bundle


def test_tickers_on_hnx_count() -> None:
    on_hnx = tickers_on(Exchange.HNX)
    assert len(on_hnx) == len(hnx_leaders())


def test_all_tickers_count() -> None:
    """Total = VN30 + HNX leaders + UPCoM leaders."""
    total = len(vn30()) + len(hnx_leaders()) + len(upcom_leaders())
    assert len(all_tickers()) == total


def test_symbols_unique() -> None:
    """No two bundled tickers share a symbol."""
    symbols = [t.symbol for t in all_tickers()]
    assert len(symbols) == len(set(symbols))
