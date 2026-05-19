"""JSONL codec for Bloom-filter snapshots.

We serialize the bit array as a hex string — JSON has no native
binary type, and hex stays human-skimmable. For very large filters
(>10MB raw) the on-disk size is 2× hex overhead; acceptable trade-off
for a single-line, ``cat``-able format.

CountingBloom counters are base64-encoded (more compact than hex for
byte arrays).
"""

from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING

from bloom.schema import (
    BloomFilter,
    BuildableBloom,
    CountingBloom,
    ScalableBloom,
)

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


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


# ---------- BloomFilter -----------------------------------------------------


def filter_to_dict(bf: BloomFilter) -> dict[str, object]:
    n_bytes = (bf.size_bits + 7) // 8
    return {
        "size_bits": bf.size_bits,
        "n_hashes": bf.n_hashes,
        "n_items": bf.n_items,
        "bits_hex": bf.bits.to_bytes(n_bytes, byteorder="little").hex(),
    }


def filter_from_dict(d: dict[str, object]) -> BloomFilter:
    raw = bytes.fromhex(_require_str(d, "bits_hex"))
    return BloomFilter(
        size_bits=_require_int(d, "size_bits"),
        n_hashes=_require_int(d, "n_hashes"),
        n_items=_require_int(d, "n_items"),
        bits=int.from_bytes(raw, byteorder="little"),
    )


# ---------- BuildableBloom --------------------------------------------------


def buildable_to_dict(bf: BuildableBloom) -> dict[str, object]:
    return {
        "size_bits": bf.size_bits,
        "n_hashes": bf.n_hashes,
        "capacity": bf.capacity,
        "target_fpr": bf.target_fpr,
        "n_items": bf.n_items,
        "bits_b64": base64.b64encode(bytes(bf._bits)).decode("ascii"),
    }


def buildable_from_dict(d: dict[str, object]) -> BuildableBloom:
    return BuildableBloom(
        size_bits=_require_int(d, "size_bits"),
        n_hashes=_require_int(d, "n_hashes"),
        capacity=_require_int(d, "capacity"),
        target_fpr=_require_float(d, "target_fpr"),
        n_items=_require_int(d, "n_items"),
        _bits=bytearray(base64.b64decode(_require_str(d, "bits_b64"))),
    )


# ---------- CountingBloom ---------------------------------------------------


def counting_to_dict(cb: CountingBloom) -> dict[str, object]:
    return {
        "size_buckets": cb.size_buckets,
        "n_hashes": cb.n_hashes,
        "capacity": cb.capacity,
        "target_fpr": cb.target_fpr,
        "n_items": cb.n_items,
        "counters_b64": base64.b64encode(bytes(cb._counters)).decode("ascii"),
    }


def counting_from_dict(d: dict[str, object]) -> CountingBloom:
    return CountingBloom(
        size_buckets=_require_int(d, "size_buckets"),
        n_hashes=_require_int(d, "n_hashes"),
        capacity=_require_int(d, "capacity"),
        target_fpr=_require_float(d, "target_fpr"),
        n_items=_require_int(d, "n_items"),
        _counters=bytearray(base64.b64decode(_require_str(d, "counters_b64"))),
    )


# ---------- ScalableBloom ---------------------------------------------------


def scalable_to_dict(sb: ScalableBloom) -> dict[str, object]:
    return {
        "initial_capacity": sb.initial_capacity,
        "target_fpr": sb.target_fpr,
        "growth_factor": sb.growth_factor,
        "tightening_ratio": sb.tightening_ratio,
        "slices": [buildable_to_dict(s) for s in sb.slices],
    }


def scalable_from_dict(d: dict[str, object]) -> ScalableBloom:
    raw_slices = d["slices"]
    if not isinstance(raw_slices, list):
        raise TypeError("slices must be list")
    slices: list[BuildableBloom] = []
    for raw in raw_slices:
        if not isinstance(raw, dict):
            raise TypeError("each slice must be dict")
        slices.append(buildable_from_dict(raw))
    return ScalableBloom(
        initial_capacity=_require_int(d, "initial_capacity"),
        target_fpr=_require_float(d, "target_fpr"),
        growth_factor=_require_int(d, "growth_factor"),
        tightening_ratio=_require_float(d, "tightening_ratio"),
        slices=slices,
    )


# ---------- Dump / load -----------------------------------------------------


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_filters(items: Iterable[BloomFilter]) -> str:
    return _dump(filter_to_dict(b) for b in items)


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


def load_filters(text: str) -> list[BloomFilter]:
    return [filter_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "buildable_from_dict",
    "buildable_to_dict",
    "counting_from_dict",
    "counting_to_dict",
    "dump_filters",
    "filter_from_dict",
    "filter_to_dict",
    "load_filters",
    "scalable_from_dict",
    "scalable_to_dict",
]
