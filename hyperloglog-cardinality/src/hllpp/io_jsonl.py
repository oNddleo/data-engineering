"""JSONL codec for HLLSketch / SketchStats.

Sketch register arrays are stored as base64-encoded bytes for
compactness — each register fits in a byte (max ρ = 65 for q = 64,
but in practice ≤ 50 even for trillion-cardinality streams).
"""

from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING

from hllpp.schema import HLLSketch, SketchStats

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


# ---------- HLLSketch --------------------------------------------------------


def sketch_to_dict(s: HLLSketch) -> dict[str, object]:
    """Serialise a sketch to a JSON-friendly dict.

    The register array is encoded as base64-of-raw-bytes — one byte
    per register since values are bounded by ``q + 1 ≤ 61``.
    """
    raw = bytes(s.registers)
    return {
        "precision": s.precision,
        "registers_b64": base64.b64encode(raw).decode("ascii"),
    }


def sketch_from_dict(d: dict[str, object]) -> HLLSketch:
    """Deserialise a sketch from a dict."""
    b64 = _require_str(d, "registers_b64")
    raw = base64.b64decode(b64.encode("ascii"))
    return HLLSketch(
        precision=_require_int(d, "precision"),
        registers=list(raw),
    )


# ---------- SketchStats ------------------------------------------------------


def stats_to_dict(s: SketchStats) -> dict[str, object]:
    return {
        "precision": s.precision,
        "m": s.m,
        "n_zero_registers": s.n_zero_registers,
        "max_register": s.max_register,
        "estimated_cardinality": s.estimated_cardinality,
        "standard_error_pct": s.standard_error_pct,
    }


def stats_from_dict(d: dict[str, object]) -> SketchStats:
    return SketchStats(
        precision=_require_int(d, "precision"),
        m=_require_int(d, "m"),
        n_zero_registers=_require_int(d, "n_zero_registers"),
        max_register=_require_int(d, "max_register"),
        estimated_cardinality=_require_int(d, "estimated_cardinality"),
        standard_error_pct=_require_number(d, "standard_error_pct"),
    )


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_sketches(items: Iterable[HLLSketch]) -> str:
    return _dump(sketch_to_dict(s) for s in items)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_sketches(text: str) -> list[HLLSketch]:
    return [sketch_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "dump_sketches",
    "load_sketches",
    "sketch_from_dict",
    "sketch_to_dict",
    "stats_from_dict",
    "stats_to_dict",
]
