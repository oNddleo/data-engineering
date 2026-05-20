"""JSONL codec for OHLCBar / TickerStats / AnomalyFinding / Order."""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING

from vnstock.aggregator import TickerStats
from vnstock.schema import (
    AnomalyFinding,
    AnomalyKind,
    Exchange,
    OHLCBar,
    Order,
    OrderKind,
    OrderSide,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def _require_int(d: dict[str, object], key: str) -> int:
    v = d[key]
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int, got {type(v).__name__}")
    return v


# ---------- OHLCBar --------------------------------------------------------


def bar_to_dict(b: OHLCBar) -> dict[str, object]:
    return {
        "symbol": b.symbol,
        "exchange": b.exchange.value,
        "date": b.date.isoformat(),
        "open_vnd": b.open_vnd,
        "high_vnd": b.high_vnd,
        "low_vnd": b.low_vnd,
        "close_vnd": b.close_vnd,
        "volume": b.volume,
        "reference_price_vnd": b.reference_price_vnd,
    }


def bar_from_dict(d: dict[str, object]) -> OHLCBar:
    return OHLCBar(
        symbol=_require_str(d, "symbol"),
        exchange=Exchange(_require_str(d, "exchange")),
        date=date.fromisoformat(_require_str(d, "date")),
        open_vnd=_require_int(d, "open_vnd"),
        high_vnd=_require_int(d, "high_vnd"),
        low_vnd=_require_int(d, "low_vnd"),
        close_vnd=_require_int(d, "close_vnd"),
        volume=_require_int(d, "volume"),
        reference_price_vnd=_require_int(d, "reference_price_vnd"),
    )


# ---------- TickerStats ----------------------------------------------------


def stats_to_dict(s: TickerStats) -> dict[str, object]:
    return {
        "symbol": s.symbol,
        "exchange": s.exchange.value,
        "n_bars": s.n_bars,
        "high_water_mark_vnd": s.high_water_mark_vnd,
        "low_water_mark_vnd": s.low_water_mark_vnd,
        "total_volume": s.total_volume,
        "avg_close_vnd": s.avg_close_vnd,
        "avg_volume": s.avg_volume,
        "first_close_vnd": s.first_close_vnd,
        "last_close_vnd": s.last_close_vnd,
    }


def stats_from_dict(d: dict[str, object]) -> TickerStats:
    return TickerStats(
        symbol=_require_str(d, "symbol"),
        exchange=Exchange(_require_str(d, "exchange")),
        n_bars=_require_int(d, "n_bars"),
        high_water_mark_vnd=_require_int(d, "high_water_mark_vnd"),
        low_water_mark_vnd=_require_int(d, "low_water_mark_vnd"),
        total_volume=_require_int(d, "total_volume"),
        avg_close_vnd=_require_int(d, "avg_close_vnd"),
        avg_volume=_require_int(d, "avg_volume"),
        first_close_vnd=_require_int(d, "first_close_vnd"),
        last_close_vnd=_require_int(d, "last_close_vnd"),
    )


# ---------- AnomalyFinding -------------------------------------------------


def anomaly_to_dict(f: AnomalyFinding) -> dict[str, object]:
    return {
        "kind": f.kind.value,
        "symbol": f.symbol,
        "exchange": f.exchange.value,
        "date": f.date.isoformat(),
        "detail": f.detail,
        "metric": f.metric,
    }


def anomaly_from_dict(d: dict[str, object]) -> AnomalyFinding:
    return AnomalyFinding(
        kind=AnomalyKind(_require_str(d, "kind")),
        symbol=_require_str(d, "symbol"),
        exchange=Exchange(_require_str(d, "exchange")),
        date=date.fromisoformat(_require_str(d, "date")),
        detail=_require_str(d, "detail"),
        metric=_require_int(d, "metric"),
    )


# ---------- Order ----------------------------------------------------------


def order_to_dict(o: Order) -> dict[str, object]:
    return {
        "order_id": o.order_id,
        "symbol": o.symbol,
        "exchange": o.exchange.value,
        "side": o.side.value,
        "kind": o.kind.value,
        "quantity": o.quantity,
        "limit_price_vnd": o.limit_price_vnd,
    }


def order_from_dict(d: dict[str, object]) -> Order:
    return Order(
        order_id=_require_str(d, "order_id"),
        symbol=_require_str(d, "symbol"),
        exchange=Exchange(_require_str(d, "exchange")),
        side=OrderSide(_require_str(d, "side")),
        kind=OrderKind(_require_str(d, "kind")),
        quantity=_require_int(d, "quantity"),
        limit_price_vnd=_require_int(d, "limit_price_vnd"),
    )


# ---------- dump / load ----------------------------------------------------


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_bars(items: Iterable[OHLCBar]) -> str:
    return _dump(bar_to_dict(b) for b in items)


def dump_stats(items: Iterable[TickerStats]) -> str:
    return _dump(stats_to_dict(s) for s in items)


def dump_anomalies(items: Iterable[AnomalyFinding]) -> str:
    return _dump(anomaly_to_dict(f) for f in items)


def dump_orders(items: Iterable[Order]) -> str:
    return _dump(order_to_dict(o) for o in items)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise TypeError(
                f"expected JSON object per line, got {type(parsed).__name__}",
            )
        yield parsed


def load_bars(text: str) -> list[OHLCBar]:
    return [bar_from_dict(d) for d in _iter_lines(text)]


def load_stats(text: str) -> list[TickerStats]:
    return [stats_from_dict(d) for d in _iter_lines(text)]


def load_anomalies(text: str) -> list[AnomalyFinding]:
    return [anomaly_from_dict(d) for d in _iter_lines(text)]


def load_orders(text: str) -> list[Order]:
    return [order_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "anomaly_from_dict",
    "anomaly_to_dict",
    "bar_from_dict",
    "bar_to_dict",
    "dump_anomalies",
    "dump_bars",
    "dump_orders",
    "dump_stats",
    "load_anomalies",
    "load_bars",
    "load_orders",
    "load_stats",
    "order_from_dict",
    "order_to_dict",
    "stats_from_dict",
    "stats_to_dict",
]
