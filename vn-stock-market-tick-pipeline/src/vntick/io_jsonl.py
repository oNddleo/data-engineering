"""Type-checked JSONL codec for Symbol / Tick / OHLCVBar."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from vntick.schema import Exchange, OHLCVBar, Symbol, Tick

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


def symbol_to_dict(s: Symbol) -> dict[str, object]:
    return {
        "code": s.code,
        "exchange": s.exchange.value,
        "name": s.name,
        "sector": s.sector,
        "listed_shares": s.listed_shares,
    }


def symbol_from_dict(d: dict[str, object]) -> Symbol:
    return Symbol(
        code=_require_str(d, "code"),
        exchange=Exchange(_require_str(d, "exchange")),
        name=_require_str(d, "name"),
        sector=_require_str(d, "sector"),
        listed_shares=_require_int(d, "listed_shares"),
    )


def tick_to_dict(t: Tick) -> dict[str, object]:
    return {
        "code": t.code,
        "price_vnd": t.price_vnd,
        "volume": t.volume,
        "occurred_at": t.occurred_at.isoformat(),
        "side": t.side,
    }


def tick_from_dict(d: dict[str, object]) -> Tick:
    return Tick(
        code=_require_str(d, "code"),
        price_vnd=_require_int(d, "price_vnd"),
        volume=_require_int(d, "volume"),
        occurred_at=datetime.fromisoformat(_require_str(d, "occurred_at")),
        side=_require_str(d, "side"),
    )


def bar_to_dict(b: OHLCVBar) -> dict[str, object]:
    return {
        "code": b.code,
        "interval_seconds": b.interval_seconds,
        "bar_start": b.bar_start.isoformat(),
        "open_vnd": b.open_vnd,
        "high_vnd": b.high_vnd,
        "low_vnd": b.low_vnd,
        "close_vnd": b.close_vnd,
        "volume": b.volume,
        "n_trades": b.n_trades,
    }


def bar_from_dict(d: dict[str, object]) -> OHLCVBar:
    return OHLCVBar(
        code=_require_str(d, "code"),
        interval_seconds=_require_int(d, "interval_seconds"),
        bar_start=datetime.fromisoformat(_require_str(d, "bar_start")),
        open_vnd=_require_int(d, "open_vnd"),
        high_vnd=_require_int(d, "high_vnd"),
        low_vnd=_require_int(d, "low_vnd"),
        close_vnd=_require_int(d, "close_vnd"),
        volume=_require_int(d, "volume"),
        n_trades=_require_int(d, "n_trades"),
    )


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_symbols(symbols: Iterable[Symbol]) -> str:
    return _dump(symbol_to_dict(s) for s in symbols)


def dump_ticks(ticks: Iterable[Tick]) -> str:
    return _dump(tick_to_dict(t) for t in ticks)


def dump_bars(bars: Iterable[OHLCVBar]) -> str:
    return _dump(bar_to_dict(b) for b in bars)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parsed = json.loads(line)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_symbols(text: str) -> Iterator[Symbol]:
    for d in _iter_lines(text):
        yield symbol_from_dict(d)


def load_ticks(text: str) -> Iterator[Tick]:
    for d in _iter_lines(text):
        yield tick_from_dict(d)


def load_bars(text: str) -> Iterator[OHLCVBar]:
    for d in _iter_lines(text):
        yield bar_from_dict(d)


__all__ = [
    "bar_from_dict",
    "bar_to_dict",
    "dump_bars",
    "dump_symbols",
    "dump_ticks",
    "load_bars",
    "load_symbols",
    "load_ticks",
    "symbol_from_dict",
    "symbol_to_dict",
    "tick_from_dict",
    "tick_to_dict",
]
