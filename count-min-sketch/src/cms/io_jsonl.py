"""JSONL codec for CountMinSketch + sub-records.

Sketch rows are stored as base64-encoded **4-byte big-endian uints**
since counters are bounded by ``2^32 - 1``. This gives the most
compact representation that's still language-agnostic.
"""

from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING

from cms.schema import (
    CountMinSketch,
    HeavyHitter,
    SketchConfig,
    SketchStats,
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


def _require_number(d: dict[str, object], key: str) -> float:
    v = d[key]
    if not isinstance(v, int | float) or isinstance(v, bool):
        raise TypeError(f"{key} must be number, got {type(v).__name__}")
    return float(v)


# ---------- CountMinSketch --------------------------------------------------


def _encode_row(row: list[int]) -> str:
    raw = b"".join(int(c).to_bytes(4, byteorder="big", signed=False) for c in row)
    return base64.b64encode(raw).decode("ascii")


def _decode_row(b64: str, width: int) -> list[int]:
    raw = base64.b64decode(b64.encode("ascii"))
    if len(raw) != width * 4:
        raise ValueError(
            f"row payload size {len(raw)} != {width * 4} expected",
        )
    return [
        int.from_bytes(raw[i * 4 : (i + 1) * 4], byteorder="big", signed=False)
        for i in range(width)
    ]


def sketch_to_dict(s: CountMinSketch) -> dict[str, object]:
    return {
        "epsilon": s.config.epsilon,
        "delta": s.config.delta,
        "total_count": s.total_count,
        "rows_b64": [_encode_row(r) for r in s.rows],
    }


def sketch_from_dict(d: dict[str, object]) -> CountMinSketch:
    config = SketchConfig(
        epsilon=_require_number(d, "epsilon"),
        delta=_require_number(d, "delta"),
    )
    rows_raw = d.get("rows_b64", [])
    if not isinstance(rows_raw, list):
        raise TypeError("rows_b64 must be list")
    if len(rows_raw) != config.depth:
        raise ValueError(
            f"row count {len(rows_raw)} != depth {config.depth}",
        )
    rows: list[list[int]] = []
    for r in rows_raw:
        if not isinstance(r, str):
            raise TypeError("each row entry must be a base64 string")
        rows.append(_decode_row(r, config.width))
    return CountMinSketch(
        config=config,
        rows=rows,
        total_count=_require_int(d, "total_count"),
    )


# ---------- Sub-records -----------------------------------------------------


def stats_to_dict(s: SketchStats) -> dict[str, object]:
    return {
        "width": s.width,
        "depth": s.depth,
        "n_cells": s.n_cells,
        "total_count": s.total_count,
        "max_counter": s.max_counter,
        "epsilon": s.epsilon,
        "delta": s.delta,
        "standard_error_bound": s.standard_error_bound,
    }


def stats_from_dict(d: dict[str, object]) -> SketchStats:
    return SketchStats(
        width=_require_int(d, "width"),
        depth=_require_int(d, "depth"),
        n_cells=_require_int(d, "n_cells"),
        total_count=_require_int(d, "total_count"),
        max_counter=_require_int(d, "max_counter"),
        epsilon=_require_number(d, "epsilon"),
        delta=_require_number(d, "delta"),
        standard_error_bound=_require_int(d, "standard_error_bound"),
    )


def heavy_hitter_to_dict(h: HeavyHitter) -> dict[str, object]:
    return {
        "value": h.value,
        "estimated_count": h.estimated_count,
        "fraction_of_total": h.fraction_of_total,
    }


def heavy_hitter_from_dict(d: dict[str, object]) -> HeavyHitter:
    return HeavyHitter(
        value=_require_str(d, "value"),
        estimated_count=_require_int(d, "estimated_count"),
        fraction_of_total=_require_number(d, "fraction_of_total"),
    )


# ---------- dump / load ----------------------------------------------------


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_sketches(items: Iterable[CountMinSketch]) -> str:
    return _dump(sketch_to_dict(s) for s in items)


def dump_heavy_hitters(items: Iterable[HeavyHitter]) -> str:
    return _dump(heavy_hitter_to_dict(h) for h in items)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_sketches(text: str) -> list[CountMinSketch]:
    return [sketch_from_dict(d) for d in _iter_lines(text)]


def load_heavy_hitters(text: str) -> list[HeavyHitter]:
    return [heavy_hitter_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "dump_heavy_hitters",
    "dump_sketches",
    "heavy_hitter_from_dict",
    "heavy_hitter_to_dict",
    "load_heavy_hitters",
    "load_sketches",
    "sketch_from_dict",
    "sketch_to_dict",
    "stats_from_dict",
    "stats_to_dict",
]
