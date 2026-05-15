"""vn-stock-market-tick-pipeline — tick → OHLCV → indicators / anomalies / index."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

if TYPE_CHECKING:
    from vntick.anomaly import (
        Anomaly,
        AnomalyKind,
        find_circuit_breaker_hits,
        find_unusual_volume,
    )
    from vntick.index import compute_index, hnx_index, vn30_index, vn_index
    from vntick.indicators import BollingerBand, MACDPoint, bollinger, ema, macd, rsi, sma
    from vntick.io_jsonl import (
        bar_from_dict,
        bar_to_dict,
        dump_bars,
        dump_symbols,
        dump_ticks,
        load_bars,
        load_symbols,
        load_ticks,
        symbol_from_dict,
        symbol_to_dict,
        tick_from_dict,
        tick_to_dict,
    )
    from vntick.resampler import INTERVAL_SECONDS, parse_interval, resample
    from vntick.schema import (
        VN_TZ,
        Exchange,
        OHLCVBar,
        Symbol,
        Tick,
        ceiling_price,
        daily_band_bps,
        floor_price,
        is_in_session,
        lot_size,
    )
    from vntick.simulator import default_reference_prices, default_symbols, generate


_LAZY: dict[str, tuple[str, str]] = {
    "Anomaly": ("vntick.anomaly", "Anomaly"),
    "AnomalyKind": ("vntick.anomaly", "AnomalyKind"),
    "BollingerBand": ("vntick.indicators", "BollingerBand"),
    "Exchange": ("vntick.schema", "Exchange"),
    "INTERVAL_SECONDS": ("vntick.resampler", "INTERVAL_SECONDS"),
    "MACDPoint": ("vntick.indicators", "MACDPoint"),
    "OHLCVBar": ("vntick.schema", "OHLCVBar"),
    "Symbol": ("vntick.schema", "Symbol"),
    "Tick": ("vntick.schema", "Tick"),
    "VN_TZ": ("vntick.schema", "VN_TZ"),
    "bar_from_dict": ("vntick.io_jsonl", "bar_from_dict"),
    "bar_to_dict": ("vntick.io_jsonl", "bar_to_dict"),
    "bollinger": ("vntick.indicators", "bollinger"),
    "ceiling_price": ("vntick.schema", "ceiling_price"),
    "compute_index": ("vntick.index", "compute_index"),
    "daily_band_bps": ("vntick.schema", "daily_band_bps"),
    "default_reference_prices": ("vntick.simulator", "default_reference_prices"),
    "default_symbols": ("vntick.simulator", "default_symbols"),
    "dump_bars": ("vntick.io_jsonl", "dump_bars"),
    "dump_symbols": ("vntick.io_jsonl", "dump_symbols"),
    "dump_ticks": ("vntick.io_jsonl", "dump_ticks"),
    "ema": ("vntick.indicators", "ema"),
    "find_circuit_breaker_hits": ("vntick.anomaly", "find_circuit_breaker_hits"),
    "find_unusual_volume": ("vntick.anomaly", "find_unusual_volume"),
    "floor_price": ("vntick.schema", "floor_price"),
    "generate": ("vntick.simulator", "generate"),
    "hnx_index": ("vntick.index", "hnx_index"),
    "is_in_session": ("vntick.schema", "is_in_session"),
    "load_bars": ("vntick.io_jsonl", "load_bars"),
    "load_symbols": ("vntick.io_jsonl", "load_symbols"),
    "load_ticks": ("vntick.io_jsonl", "load_ticks"),
    "lot_size": ("vntick.schema", "lot_size"),
    "macd": ("vntick.indicators", "macd"),
    "parse_interval": ("vntick.resampler", "parse_interval"),
    "resample": ("vntick.resampler", "resample"),
    "rsi": ("vntick.indicators", "rsi"),
    "sma": ("vntick.indicators", "sma"),
    "symbol_from_dict": ("vntick.io_jsonl", "symbol_from_dict"),
    "symbol_to_dict": ("vntick.io_jsonl", "symbol_to_dict"),
    "tick_from_dict": ("vntick.io_jsonl", "tick_from_dict"),
    "tick_to_dict": ("vntick.io_jsonl", "tick_to_dict"),
    "vn30_index": ("vntick.index", "vn30_index"),
    "vn_index": ("vntick.index", "vn_index"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "INTERVAL_SECONDS",
    "VN_TZ",
    "Anomaly",
    "AnomalyKind",
    "BollingerBand",
    "Exchange",
    "MACDPoint",
    "OHLCVBar",
    "Symbol",
    "Tick",
    "__version__",
    "bar_from_dict",
    "bar_to_dict",
    "bollinger",
    "ceiling_price",
    "compute_index",
    "daily_band_bps",
    "default_reference_prices",
    "default_symbols",
    "dump_bars",
    "dump_symbols",
    "dump_ticks",
    "ema",
    "find_circuit_breaker_hits",
    "find_unusual_volume",
    "floor_price",
    "generate",
    "hnx_index",
    "is_in_session",
    "load_bars",
    "load_symbols",
    "load_ticks",
    "lot_size",
    "macd",
    "parse_interval",
    "resample",
    "rsi",
    "sma",
    "symbol_from_dict",
    "symbol_to_dict",
    "tick_from_dict",
    "tick_to_dict",
    "vn30_index",
    "vn_index",
]
