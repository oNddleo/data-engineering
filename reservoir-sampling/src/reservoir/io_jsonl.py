"""JSONL codec for Reservoir + WeightedReservoir snapshots."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from reservoir.schema import Reservoir, WeightedItem, WeightedReservoir

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


def _require_int(d: dict[str, object], key: str) -> int:
    v = d[key]
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int, got {type(v).__name__}")
    return v


def _require_float(d: dict[str, object], key: str) -> float:
    v = d[key]
    if isinstance(v, bool) or not isinstance(v, int | float):
        raise TypeError(f"{key} must be number, got {type(v).__name__}")
    return float(v)


def _require_list(d: dict[str, object], key: str) -> list[object]:
    v = d[key]
    if not isinstance(v, list):
        raise TypeError(f"{key} must be list, got {type(v).__name__}")
    return v


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


# ---------- Reservoir -------------------------------------------------------


def reservoir_to_dict(r: Reservoir) -> dict[str, object]:
    return {
        "capacity": r.capacity,
        "items": list(r.items),
        "n_seen": r.n_seen,
    }


def reservoir_from_dict(d: dict[str, object]) -> Reservoir:
    raw_items = _require_list(d, "items")
    items: list[str] = []
    for entry in raw_items:
        if not isinstance(entry, str):
            raise TypeError(f"item must be str, got {type(entry).__name__}")
        items.append(entry)
    return Reservoir(
        capacity=_require_int(d, "capacity"),
        items=tuple(items),
        n_seen=_require_int(d, "n_seen"),
    )


# ---------- WeightedReservoir ----------------------------------------------


def weighted_to_dict(r: WeightedReservoir) -> dict[str, object]:
    return {
        "capacity": r.capacity,
        "items": [{"value": w.value, "weight": w.weight, "key": w.key} for w in r.items],
        "n_seen": r.n_seen,
        "total_weight_seen": r.total_weight_seen,
    }


def weighted_from_dict(d: dict[str, object]) -> WeightedReservoir:
    raw_items = _require_list(d, "items")
    items: list[WeightedItem] = []
    for entry in raw_items:
        if not isinstance(entry, dict):
            raise TypeError("weighted item must be dict")
        items.append(
            WeightedItem(
                value=_require_str(entry, "value"),
                weight=_require_float(entry, "weight"),
                key=_require_float(entry, "key"),
            )
        )
    return WeightedReservoir(
        capacity=_require_int(d, "capacity"),
        items=items,
        n_seen=_require_int(d, "n_seen"),
        total_weight_seen=_require_float(d, "total_weight_seen"),
    )


# ---------- dump / load -----------------------------------------------------


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_reservoirs(items: Iterable[Reservoir]) -> str:
    return _dump(reservoir_to_dict(r) for r in items)


def dump_weighted(items: Iterable[WeightedReservoir]) -> str:
    return _dump(weighted_to_dict(r) for r in items)


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


def load_reservoirs(text: str) -> list[Reservoir]:
    return [reservoir_from_dict(d) for d in _iter_lines(text)]


def load_weighted(text: str) -> list[WeightedReservoir]:
    return [weighted_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "dump_reservoirs",
    "dump_weighted",
    "load_reservoirs",
    "load_weighted",
    "reservoir_from_dict",
    "reservoir_to_dict",
    "weighted_from_dict",
    "weighted_to_dict",
]
