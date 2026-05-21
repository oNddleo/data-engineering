"""dedup-with-bloom — probabilistic streaming deduplication."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

_LAZY: dict[str, tuple[str, str]] = {
    "BloomFilter": ("bloomdedup.bloom", "BloomFilter"),
    "BloomParams": ("bloomdedup.schema", "BloomParams"),
    "DedupStats": ("bloomdedup.dedup", "DedupStats"),
    "dedup_iter": ("bloomdedup.dedup", "dedup_iter"),
    "dedup_stream": ("bloomdedup.dedup", "dedup_stream"),
    "generate": ("bloomdedup.simulator", "generate"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        module_name, attr = _LAZY[name]
        return getattr(import_module(module_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:
    from bloomdedup.bloom import BloomFilter
    from bloomdedup.dedup import DedupStats, dedup_iter, dedup_stream
    from bloomdedup.schema import BloomParams
    from bloomdedup.simulator import generate

__all__ = [
    "BloomFilter",
    "BloomParams",
    "DedupStats",
    "__version__",
    "dedup_iter",
    "dedup_stream",
    "generate",
]
