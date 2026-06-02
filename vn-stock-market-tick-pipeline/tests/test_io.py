"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from vntick.io_jsonl import (
    dump_bars,
    dump_symbols,
    dump_ticks,
    load_bars,
    load_symbols,
    load_ticks,
    symbol_from_dict,
    tick_from_dict,
)

from ._fixtures import make_bar, make_symbol, make_tick


def test_symbol_roundtrip():
    s = make_symbol()
    [back] = list(load_symbols(dump_symbols([s])))
    assert back == s


def test_tick_roundtrip():
    t = make_tick()
    [back] = list(load_ticks(dump_ticks([t])))
    assert back == t


def test_bar_roundtrip():
    b = make_bar()
    [back] = list(load_bars(dump_bars([b])))
    assert back == b


def test_symbol_decoder_rejects_unknown_exchange():
    bad = {"code": "VCB", "exchange": "NYSE", "name": "x", "sector": "y", "listed_shares": 1}
    with pytest.raises(ValueError):
        symbol_from_dict(bad)


def test_tick_decoder_rejects_bool_for_int():
    """``bool`` is a subclass of ``int`` — must be rejected explicitly."""
    bad = {
        "code": "VCB",
        "price_vnd": True,
        "volume": 100,
        "occurred_at": "2026-05-04T09:30:00+07:00",
        "side": "B",
    }
    with pytest.raises(TypeError, match="price_vnd"):
        tick_from_dict(bad)


def test_tick_decoder_rejects_wrong_string_field():
    bad = {
        "code": 5,
        "price_vnd": 100,
        "volume": 100,
        "occurred_at": "2026-05-04T09:30:00+07:00",
        "side": "B",
    }
    with pytest.raises(TypeError, match="code"):
        tick_from_dict(bad)


def test_blank_lines_skipped():
    text = dump_ticks([make_tick()])
    padded = "\n\n" + text + "\n\n"
    assert len(list(load_ticks(padded))) == 1


def test_multi_record_roundtrip():
    ticks = [make_tick(code=f"S{i:02d}", volume=100 * (i + 1)) for i in range(5)]
    text = dump_ticks(ticks)
    assert list(load_ticks(text)) == ticks


def test_bar_decoder_preserves_volume_and_n_trades():
    b = make_bar(volume=12_345, n_trades=42)
    [back] = list(load_bars(dump_bars([b])))
    assert back.volume == 12_345
    assert back.n_trades == 42
