"""vn-property-listing-normalizer — parse VN real-estate listings."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

if TYPE_CHECKING:
    from vnprop.area import parse_area_m2
    from vnprop.io_jsonl import (
        dump_listings,
        dump_raw,
        listing_from_dict,
        listing_to_dict,
        load_listings,
        load_raw,
        raw_from_dict,
        raw_to_dict,
    )
    from vnprop.location import parse_district, parse_province, parse_ward
    from vnprop.normalizer import RawListing, normalize
    from vnprop.price import format_price_vnd, parse_price_vnd
    from vnprop.schema import Listing, PropertyKind
    from vnprop.simulator import generate


_LAZY: dict[str, tuple[str, str]] = {
    "Listing": ("vnprop.schema", "Listing"),
    "PropertyKind": ("vnprop.schema", "PropertyKind"),
    "RawListing": ("vnprop.normalizer", "RawListing"),
    "dump_listings": ("vnprop.io_jsonl", "dump_listings"),
    "dump_raw": ("vnprop.io_jsonl", "dump_raw"),
    "format_price_vnd": ("vnprop.price", "format_price_vnd"),
    "generate": ("vnprop.simulator", "generate"),
    "listing_from_dict": ("vnprop.io_jsonl", "listing_from_dict"),
    "listing_to_dict": ("vnprop.io_jsonl", "listing_to_dict"),
    "load_listings": ("vnprop.io_jsonl", "load_listings"),
    "load_raw": ("vnprop.io_jsonl", "load_raw"),
    "normalize": ("vnprop.normalizer", "normalize"),
    "parse_area_m2": ("vnprop.area", "parse_area_m2"),
    "parse_district": ("vnprop.location", "parse_district"),
    "parse_price_vnd": ("vnprop.price", "parse_price_vnd"),
    "parse_province": ("vnprop.location", "parse_province"),
    "parse_ward": ("vnprop.location", "parse_ward"),
    "raw_from_dict": ("vnprop.io_jsonl", "raw_from_dict"),
    "raw_to_dict": ("vnprop.io_jsonl", "raw_to_dict"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "Listing",
    "PropertyKind",
    "RawListing",
    "__version__",
    "dump_listings",
    "dump_raw",
    "format_price_vnd",
    "generate",
    "listing_from_dict",
    "listing_to_dict",
    "load_listings",
    "load_raw",
    "normalize",
    "parse_area_m2",
    "parse_district",
    "parse_price_vnd",
    "parse_province",
    "parse_ward",
    "raw_from_dict",
    "raw_to_dict",
]
