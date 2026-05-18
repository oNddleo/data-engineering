"""JSONL codec for ColumnProfile and its sub-records."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from colstats.schema import (
    Bin,
    ColumnKind,
    ColumnProfile,
    Histogram,
    HistogramKind,
    NumericStats,
    StringStats,
    TopKEntry,
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


def _require_bool(d: dict[str, object], key: str) -> bool:
    v = d[key]
    if not isinstance(v, bool):
        raise TypeError(f"{key} must be bool, got {type(v).__name__}")
    return v


def _require_number(d: dict[str, object], key: str) -> float:
    v = d[key]
    if not isinstance(v, int | float) or isinstance(v, bool):
        raise TypeError(f"{key} must be number, got {type(v).__name__}")
    return float(v)


# ---------- sub-records ------------------------------------------------------


def bin_to_dict(b: Bin) -> dict[str, object]:
    return {"lower": b.lower, "upper": b.upper, "count": b.count}


def bin_from_dict(d: dict[str, object]) -> Bin:
    return Bin(
        lower=_require_number(d, "lower"),
        upper=_require_number(d, "upper"),
        count=_require_int(d, "count"),
    )


def histogram_to_dict(h: Histogram) -> dict[str, object]:
    return {
        "kind": h.kind.value,
        "bins": [bin_to_dict(b) for b in h.bins],
        "total_count": h.total_count,
    }


def histogram_from_dict(d: dict[str, object]) -> Histogram:
    bins_raw = d.get("bins", [])
    if not isinstance(bins_raw, list):
        raise TypeError("bins must be list")
    bins: list[Bin] = []
    for b in bins_raw:
        if not isinstance(b, dict):
            raise TypeError(f"bin must be dict, got {type(b).__name__}")
        bins.append(bin_from_dict(b))
    return Histogram(
        kind=HistogramKind(_require_str(d, "kind")),
        bins=tuple(bins),
        total_count=_require_int(d, "total_count"),
    )


def topk_to_dict(t: TopKEntry) -> dict[str, object]:
    return {"value": t.value, "count": t.count, "epsilon": t.epsilon}


def topk_from_dict(d: dict[str, object]) -> TopKEntry:
    return TopKEntry(
        value=_require_str(d, "value"),
        count=_require_int(d, "count"),
        epsilon=_require_int(d, "epsilon") if "epsilon" in d else 0,
    )


def numeric_to_dict(n: NumericStats) -> dict[str, object]:
    return {
        "min": n.min,
        "max": n.max,
        "mean": n.mean,
        "std": n.std,
        "p25": n.p25,
        "p50": n.p50,
        "p75": n.p75,
        "p95": n.p95,
        "p99": n.p99,
    }


def numeric_from_dict(d: dict[str, object]) -> NumericStats:
    return NumericStats(
        min=_require_number(d, "min"),
        max=_require_number(d, "max"),
        mean=_require_number(d, "mean"),
        std=_require_number(d, "std"),
        p25=_require_number(d, "p25"),
        p50=_require_number(d, "p50"),
        p75=_require_number(d, "p75"),
        p95=_require_number(d, "p95"),
        p99=_require_number(d, "p99"),
    )


def strings_to_dict(s: StringStats) -> dict[str, object]:
    return {
        "min_length": s.min_length,
        "max_length": s.max_length,
        "mean_length": s.mean_length,
    }


def strings_from_dict(d: dict[str, object]) -> StringStats:
    return StringStats(
        min_length=_require_int(d, "min_length"),
        max_length=_require_int(d, "max_length"),
        mean_length=_require_number(d, "mean_length"),
    )


# ---------- ColumnProfile ----------------------------------------------------


def profile_to_dict(p: ColumnProfile) -> dict[str, object]:
    return {
        "name": p.name,
        "kind": p.kind.value,
        "n_rows": p.n_rows,
        "n_non_null": p.n_non_null,
        "cardinality": p.cardinality,
        "cardinality_capped": p.cardinality_capped,
        "numeric": numeric_to_dict(p.numeric) if p.numeric is not None else None,
        "strings": strings_to_dict(p.strings) if p.strings is not None else None,
        "top_k": [topk_to_dict(t) for t in p.top_k],
        "histogram": histogram_to_dict(p.histogram) if p.histogram is not None else None,
    }


def profile_from_dict(d: dict[str, object]) -> ColumnProfile:
    numeric_raw = d.get("numeric")
    numeric = numeric_from_dict(numeric_raw) if isinstance(numeric_raw, dict) else None
    strings_raw = d.get("strings")
    strings = strings_from_dict(strings_raw) if isinstance(strings_raw, dict) else None
    histogram_raw = d.get("histogram")
    histogram = histogram_from_dict(histogram_raw) if isinstance(histogram_raw, dict) else None
    top_k_raw = d.get("top_k", [])
    if not isinstance(top_k_raw, list):
        raise TypeError("top_k must be list")
    top_k_list: list[TopKEntry] = []
    for t in top_k_raw:
        if not isinstance(t, dict):
            raise TypeError(f"top_k entry must be dict, got {type(t).__name__}")
        top_k_list.append(topk_from_dict(t))
    return ColumnProfile(
        name=_require_str(d, "name"),
        kind=ColumnKind(_require_str(d, "kind")),
        n_rows=_require_int(d, "n_rows"),
        n_non_null=_require_int(d, "n_non_null"),
        cardinality=_require_int(d, "cardinality"),
        cardinality_capped=_require_bool(d, "cardinality_capped"),
        numeric=numeric,
        strings=strings,
        top_k=tuple(top_k_list),
        histogram=histogram,
    )


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_profiles(items: Iterable[ColumnProfile]) -> str:
    return _dump(profile_to_dict(p) for p in items)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise TypeError(f"expected JSON object per line, got {type(parsed).__name__}")
        yield parsed


def load_profiles(text: str) -> list[ColumnProfile]:
    return [profile_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "dump_profiles",
    "load_profiles",
    "profile_from_dict",
    "profile_to_dict",
]
