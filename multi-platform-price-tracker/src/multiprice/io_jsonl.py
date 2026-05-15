"""JSONL codec for SkuMapping + ProductObservation."""

from __future__ import annotations

import json
from datetime import datetime
from typing import TYPE_CHECKING

from multiprice.schema import Platform, ProductObservation, SkuMapping

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


def mapping_to_dict(m: SkuMapping) -> dict[str, object]:
    return {
        "canonical_sku": m.canonical_sku,
        "platform": m.platform.value,
        "platform_item_id": m.platform_item_id,
    }


def mapping_from_dict(d: dict[str, object]) -> SkuMapping:
    return SkuMapping(
        canonical_sku=_require_str(d, "canonical_sku"),
        platform=Platform(_require_str(d, "platform")),
        platform_item_id=_require_str(d, "platform_item_id"),
    )


def obs_to_dict(o: ProductObservation) -> dict[str, object]:
    return {
        "canonical_sku": o.canonical_sku,
        "platform": o.platform.value,
        "platform_item_id": o.platform_item_id,
        "name": o.name,
        "price_vnd": o.price_vnd,
        "original_price_vnd": o.original_price_vnd,
        "stock": o.stock,
        "observed_at": o.observed_at.isoformat(),
    }


def obs_from_dict(d: dict[str, object]) -> ProductObservation:
    return ProductObservation(
        canonical_sku=_require_str(d, "canonical_sku"),
        platform=Platform(_require_str(d, "platform")),
        platform_item_id=_require_str(d, "platform_item_id"),
        name=_require_str(d, "name"),
        price_vnd=_require_int(d, "price_vnd"),
        original_price_vnd=_require_int(d, "original_price_vnd"),
        stock=_require_int(d, "stock"),
        observed_at=datetime.fromisoformat(_require_str(d, "observed_at")),
    )


def dump_mappings(ms: Iterable[SkuMapping]) -> str:
    return "\n".join(json.dumps(mapping_to_dict(m), ensure_ascii=False) for m in ms) + "\n"


def load_mappings(text: str) -> Iterator[SkuMapping]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        yield mapping_from_dict(json.loads(line))


def dump_observations(os: Iterable[ProductObservation]) -> str:
    return "\n".join(json.dumps(obs_to_dict(o), ensure_ascii=False) for o in os) + "\n"


def load_observations(text: str) -> Iterator[ProductObservation]:
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        yield obs_from_dict(json.loads(line))


__all__ = [
    "dump_mappings",
    "dump_observations",
    "load_mappings",
    "load_observations",
    "mapping_from_dict",
    "mapping_to_dict",
    "obs_from_dict",
    "obs_to_dict",
]
