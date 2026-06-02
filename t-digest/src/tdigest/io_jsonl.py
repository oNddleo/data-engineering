"""JSONL codec for TDigest snapshots."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from tdigest.schema import Centroid, TDigest

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


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


def digest_to_dict(td: TDigest) -> dict[str, object]:
    return {
        "compression": td.compression,
        "centroids": [[c.mean, c.weight] for c in td.centroids],
        "total_weight": td.total_weight,
        "min_value": td.min_value,
        "max_value": td.max_value,
    }


def digest_from_dict(d: dict[str, object]) -> TDigest:
    raw_centroids = _require_list(d, "centroids")
    centroids: list[Centroid] = []
    for entry in raw_centroids:
        if not isinstance(entry, list) or len(entry) != 2:
            raise TypeError(f"centroid must be [mean, weight], got {entry!r}")
        mean_v, weight_v = entry
        if not isinstance(mean_v, int | float) or isinstance(mean_v, bool):
            raise TypeError(f"centroid mean must be number, got {type(mean_v).__name__}")
        if not isinstance(weight_v, int | float) or isinstance(weight_v, bool):
            raise TypeError(
                f"centroid weight must be number, got {type(weight_v).__name__}",
            )
        centroids.append(Centroid(mean=float(mean_v), weight=float(weight_v)))
    return TDigest(
        compression=_require_float(d, "compression"),
        centroids=tuple(centroids),
        total_weight=_require_float(d, "total_weight"),
        min_value=_require_float(d, "min_value"),
        max_value=_require_float(d, "max_value"),
    )


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_digests(items: Iterable[TDigest]) -> str:
    return _dump(digest_to_dict(t) for t in items)


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


def load_digests(text: str) -> list[TDigest]:
    return [digest_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "digest_from_dict",
    "digest_to_dict",
    "dump_digests",
    "load_digests",
]
