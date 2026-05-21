"""dedup-with-bloom — probabilistic streaming deduplication."""

from __future__ import annotations

__version__ = "0.1.0"

def __getattr__(name: str) -> object:
    _LAZY = {
        "BloomFilter": ("bloomdedup.bloom", "BloomFilter"),
        "BloomParams": ("bloomdedup.schema", "BloomParams"),
        "DedupStats": ("bloomdedup.dedup", "DedupStats"),
        "dedup_iter": ("bloomdedup.dedup", "dedup_iter"),
        "dedup_stream": ("bloomdedup.dedup", "dedup_stream"),
        "generate": ("bloomdedup.simulator", "generate"),
    }

    if name in _LAZY:
        from importlib import import_module

        module_name, attr = _LAZY[name]
        return getattr(import_module(module_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "BloomFilter",
    "BloomParams",
    "DedupStats",
    "__version__",
    "dedup_iter",
    "dedup_stream",
    "generate",
]
