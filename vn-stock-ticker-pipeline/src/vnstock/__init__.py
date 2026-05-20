"""vn-stock-ticker-pipeline — HOSE/HNX/UPCoM equity data toolkit."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

if TYPE_CHECKING:
    from vnstock.aggregator import (
        TickerStats,
        aggregate_ticker_stats,
        moving_average_close,
        volume_weighted_avg_price,
    )
    from vnstock.anomaly import (
        find_band_breaches,
        find_price_gaps,
        find_volume_spikes,
    )
    from vnstock.bars import Trade, aggregate_bar
    from vnstock.exchanges import (
        ExchangeProfile,
        all_exchanges,
        profile_for,
    )
    from vnstock.io_jsonl import (
        anomaly_from_dict,
        anomaly_to_dict,
        bar_from_dict,
        bar_to_dict,
        dump_anomalies,
        dump_bars,
        dump_orders,
        dump_stats,
        load_anomalies,
        load_bars,
        load_orders,
        load_stats,
        order_from_dict,
        order_to_dict,
        stats_from_dict,
        stats_to_dict,
    )
    from vnstock.pricing import (
        ceiling_floor,
        is_valid_lot,
        is_valid_tick,
        is_within_band,
        round_to_tick,
        tick_size,
    )
    from vnstock.schema import (
        AnomalyFinding,
        AnomalyKind,
        Exchange,
        OHLCBar,
        Order,
        OrderKind,
        OrderSide,
        Ticker,
    )
    from vnstock.simulator import generate
    from vnstock.tickers import (
        all_tickers,
        hnx_leaders,
        ticker_for,
        tickers_on,
        upcom_leaders,
        vn30,
    )


_LAZY: dict[str, tuple[str, str]] = {
    "AnomalyFinding": ("vnstock.schema", "AnomalyFinding"),
    "AnomalyKind": ("vnstock.schema", "AnomalyKind"),
    "Exchange": ("vnstock.schema", "Exchange"),
    "ExchangeProfile": ("vnstock.exchanges", "ExchangeProfile"),
    "OHLCBar": ("vnstock.schema", "OHLCBar"),
    "Order": ("vnstock.schema", "Order"),
    "OrderKind": ("vnstock.schema", "OrderKind"),
    "OrderSide": ("vnstock.schema", "OrderSide"),
    "Ticker": ("vnstock.schema", "Ticker"),
    "TickerStats": ("vnstock.aggregator", "TickerStats"),
    "Trade": ("vnstock.bars", "Trade"),
    "aggregate_bar": ("vnstock.bars", "aggregate_bar"),
    "aggregate_ticker_stats": ("vnstock.aggregator", "aggregate_ticker_stats"),
    "all_exchanges": ("vnstock.exchanges", "all_exchanges"),
    "all_tickers": ("vnstock.tickers", "all_tickers"),
    "anomaly_from_dict": ("vnstock.io_jsonl", "anomaly_from_dict"),
    "anomaly_to_dict": ("vnstock.io_jsonl", "anomaly_to_dict"),
    "bar_from_dict": ("vnstock.io_jsonl", "bar_from_dict"),
    "bar_to_dict": ("vnstock.io_jsonl", "bar_to_dict"),
    "ceiling_floor": ("vnstock.pricing", "ceiling_floor"),
    "dump_anomalies": ("vnstock.io_jsonl", "dump_anomalies"),
    "dump_bars": ("vnstock.io_jsonl", "dump_bars"),
    "dump_orders": ("vnstock.io_jsonl", "dump_orders"),
    "dump_stats": ("vnstock.io_jsonl", "dump_stats"),
    "find_band_breaches": ("vnstock.anomaly", "find_band_breaches"),
    "find_price_gaps": ("vnstock.anomaly", "find_price_gaps"),
    "find_volume_spikes": ("vnstock.anomaly", "find_volume_spikes"),
    "generate": ("vnstock.simulator", "generate"),
    "hnx_leaders": ("vnstock.tickers", "hnx_leaders"),
    "is_valid_lot": ("vnstock.pricing", "is_valid_lot"),
    "is_valid_tick": ("vnstock.pricing", "is_valid_tick"),
    "is_within_band": ("vnstock.pricing", "is_within_band"),
    "load_anomalies": ("vnstock.io_jsonl", "load_anomalies"),
    "load_bars": ("vnstock.io_jsonl", "load_bars"),
    "load_orders": ("vnstock.io_jsonl", "load_orders"),
    "load_stats": ("vnstock.io_jsonl", "load_stats"),
    "moving_average_close": ("vnstock.aggregator", "moving_average_close"),
    "order_from_dict": ("vnstock.io_jsonl", "order_from_dict"),
    "order_to_dict": ("vnstock.io_jsonl", "order_to_dict"),
    "profile_for": ("vnstock.exchanges", "profile_for"),
    "round_to_tick": ("vnstock.pricing", "round_to_tick"),
    "stats_from_dict": ("vnstock.io_jsonl", "stats_from_dict"),
    "stats_to_dict": ("vnstock.io_jsonl", "stats_to_dict"),
    "tick_size": ("vnstock.pricing", "tick_size"),
    "ticker_for": ("vnstock.tickers", "ticker_for"),
    "tickers_on": ("vnstock.tickers", "tickers_on"),
    "upcom_leaders": ("vnstock.tickers", "upcom_leaders"),
    "vn30": ("vnstock.tickers", "vn30"),
    "volume_weighted_avg_price": (
        "vnstock.aggregator",
        "volume_weighted_avg_price",
    ),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "AnomalyFinding",
    "AnomalyKind",
    "Exchange",
    "ExchangeProfile",
    "OHLCBar",
    "Order",
    "OrderKind",
    "OrderSide",
    "Ticker",
    "TickerStats",
    "Trade",
    "__version__",
    "aggregate_bar",
    "aggregate_ticker_stats",
    "all_exchanges",
    "all_tickers",
    "anomaly_from_dict",
    "anomaly_to_dict",
    "bar_from_dict",
    "bar_to_dict",
    "ceiling_floor",
    "dump_anomalies",
    "dump_bars",
    "dump_orders",
    "dump_stats",
    "find_band_breaches",
    "find_price_gaps",
    "find_volume_spikes",
    "generate",
    "hnx_leaders",
    "is_valid_lot",
    "is_valid_tick",
    "is_within_band",
    "load_anomalies",
    "load_bars",
    "load_orders",
    "load_stats",
    "moving_average_close",
    "order_from_dict",
    "order_to_dict",
    "profile_for",
    "round_to_tick",
    "stats_from_dict",
    "stats_to_dict",
    "tick_size",
    "ticker_for",
    "tickers_on",
    "upcom_leaders",
    "vn30",
    "volume_weighted_avg_price",
]
