"""multi-platform-price-tracker — Shopee/Lazada/Tiki cross-platform price tracker."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

if TYPE_CHECKING:
    from multiprice.detectors import (
        detect_arbitrage,
        detect_below_map,
        detect_price_changes,
        detect_stockouts,
    )
    from multiprice.events import (
        ArbitrageEvent,
        BelowMapEvent,
        Direction,
        EventKind,
        PriceChangeEvent,
        StockoutEvent,
    )
    from multiprice.io_jsonl import (
        dump_mappings,
        dump_observations,
        load_mappings,
        load_observations,
        mapping_from_dict,
        mapping_to_dict,
        obs_from_dict,
        obs_to_dict,
    )
    from multiprice.mapping import SkuRegistry
    from multiprice.schema import VN_TZ, Platform, ProductObservation, SkuMapping
    from multiprice.simulator import generate
    from multiprice.store import ObservationStore


_LAZY: dict[str, tuple[str, str]] = {
    "ArbitrageEvent": ("multiprice.events", "ArbitrageEvent"),
    "BelowMapEvent": ("multiprice.events", "BelowMapEvent"),
    "Direction": ("multiprice.events", "Direction"),
    "EventKind": ("multiprice.events", "EventKind"),
    "ObservationStore": ("multiprice.store", "ObservationStore"),
    "Platform": ("multiprice.schema", "Platform"),
    "PriceChangeEvent": ("multiprice.events", "PriceChangeEvent"),
    "ProductObservation": ("multiprice.schema", "ProductObservation"),
    "SkuMapping": ("multiprice.schema", "SkuMapping"),
    "SkuRegistry": ("multiprice.mapping", "SkuRegistry"),
    "StockoutEvent": ("multiprice.events", "StockoutEvent"),
    "VN_TZ": ("multiprice.schema", "VN_TZ"),
    "detect_arbitrage": ("multiprice.detectors", "detect_arbitrage"),
    "detect_below_map": ("multiprice.detectors", "detect_below_map"),
    "detect_price_changes": ("multiprice.detectors", "detect_price_changes"),
    "detect_stockouts": ("multiprice.detectors", "detect_stockouts"),
    "dump_mappings": ("multiprice.io_jsonl", "dump_mappings"),
    "dump_observations": ("multiprice.io_jsonl", "dump_observations"),
    "generate": ("multiprice.simulator", "generate"),
    "load_mappings": ("multiprice.io_jsonl", "load_mappings"),
    "load_observations": ("multiprice.io_jsonl", "load_observations"),
    "mapping_from_dict": ("multiprice.io_jsonl", "mapping_from_dict"),
    "mapping_to_dict": ("multiprice.io_jsonl", "mapping_to_dict"),
    "obs_from_dict": ("multiprice.io_jsonl", "obs_from_dict"),
    "obs_to_dict": ("multiprice.io_jsonl", "obs_to_dict"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        m, attr = _LAZY[name]
        return getattr(import_module(m), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "VN_TZ",
    "ArbitrageEvent",
    "BelowMapEvent",
    "Direction",
    "EventKind",
    "ObservationStore",
    "Platform",
    "PriceChangeEvent",
    "ProductObservation",
    "SkuMapping",
    "SkuRegistry",
    "StockoutEvent",
    "__version__",
    "detect_arbitrage",
    "detect_below_map",
    "detect_price_changes",
    "detect_stockouts",
    "dump_mappings",
    "dump_observations",
    "generate",
    "load_mappings",
    "load_observations",
    "mapping_from_dict",
    "mapping_to_dict",
    "obs_from_dict",
    "obs_to_dict",
]
