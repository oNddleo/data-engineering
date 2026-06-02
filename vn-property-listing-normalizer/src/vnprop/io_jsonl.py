"""JSONL codec for Listing + RawListing."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from vnprop.normalizer import RawListing
from vnprop.schema import Listing, PropertyKind

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


def _opt_str(d: dict[str, object], key: str) -> str:
    v = d.get(key, "")
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def listing_to_dict(item: Listing) -> dict[str, object]:
    return {
        "listing_id": item.listing_id,
        "kind": item.kind.value,
        "area_m2": item.area_m2,
        "price_vnd": item.price_vnd,
        "province": item.province,
        "district": item.district,
        "ward": item.ward,
        "bedrooms": item.bedrooms,
        "bathrooms": item.bathrooms,
    }


def listing_from_dict(d: dict[str, object]) -> Listing:
    return Listing(
        listing_id=_require_str(d, "listing_id"),
        kind=PropertyKind(_require_str(d, "kind")),
        area_m2=_require_int(d, "area_m2"),
        price_vnd=_require_int(d, "price_vnd"),
        province=_require_str(d, "province"),
        district=_opt_str(d, "district"),
        ward=_opt_str(d, "ward"),
        bedrooms=_require_int(d, "bedrooms") if "bedrooms" in d else 0,
        bathrooms=_require_int(d, "bathrooms") if "bathrooms" in d else 0,
    )


def raw_to_dict(r: RawListing) -> dict[str, object]:
    return {
        "listing_id": r.listing_id,
        "title": r.title,
        "description": r.description,
        "price_text": r.price_text,
        "area_text": r.area_text,
    }


def raw_from_dict(d: dict[str, object]) -> RawListing:
    return RawListing(
        listing_id=_require_str(d, "listing_id"),
        title=_require_str(d, "title"),
        description=_require_str(d, "description"),
        price_text=_require_str(d, "price_text"),
        area_text=_require_str(d, "area_text"),
    )


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_listings(items: Iterable[Listing]) -> str:
    return _dump(listing_to_dict(item) for item in items)


def dump_raw(items: Iterable[RawListing]) -> str:
    return _dump(raw_to_dict(r) for r in items)


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


def load_listings(text: str) -> list[Listing]:
    return [listing_from_dict(d) for d in _iter_lines(text)]


def load_raw(text: str) -> list[RawListing]:
    return [raw_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "dump_listings",
    "dump_raw",
    "listing_from_dict",
    "listing_to_dict",
    "load_listings",
    "load_raw",
    "raw_from_dict",
    "raw_to_dict",
]
