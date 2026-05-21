"""causal-feature-store — per-entity vector-clock causal-consistency."""

from __future__ import annotations

__version__ = "0.1.0"

def __getattr__(name: str) -> object:
    _LAZY = {
        "VectorClock": ("cfs.clock.vector_clock", "VectorClock"),
        "bump": ("cfs.clock.vector_clock", "bump"),
        "dominates": ("cfs.clock.vector_clock", "dominates"),
        "equal": ("cfs.clock.vector_clock", "equal"),
        "lt": ("cfs.clock.vector_clock", "lt"),
        "concurrent": ("cfs.clock.vector_clock", "concurrent"),
        "pointwise_max": ("cfs.clock.vector_clock", "pointwise_max"),
        "Version": ("cfs.store.version", "Version"),
        "HotStore": ("cfs.store.hot", "HotStore"),
        "ColdStore": ("cfs.store.cold", "ColdStore"),
        "Writer": ("cfs.writer", "Writer"),
        "Resolver": ("cfs.serving.resolver", "Resolver"),
        "ResolvedVector": ("cfs.serving.resolver", "ResolvedVector"),
        "PartitionScenario": ("cfs.partition", "PartitionScenario"),
    }

    if name in _LAZY:
        from importlib import import_module

        module, attr = _LAZY[name]
        return getattr(import_module(module), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "ColdStore",
    "HotStore",
    "PartitionScenario",
    "ResolvedVector",
    "Resolver",
    "VectorClock",
    "Version",
    "Writer",
    "__version__",
    "bump",
    "concurrent",
    "dominates",
    "equal",
    "lt",
    "pointwise_max",
]
