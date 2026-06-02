"""partitioner-toolkit — range / hash / consistent / round-robin partitioners."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY = {
        "HashModPartitioner": ("partitioner.hash_mod", "HashModPartitioner"),
        "RangePartitioner": ("partitioner.range_part", "RangePartitioner"),
        "ConsistentHashRing": ("partitioner.consistent", "ConsistentHashRing"),
        "RoundRobinPartitioner": ("partitioner.round_robin", "RoundRobinPartitioner"),
        "generate_keys": ("partitioner.simulator", "generate_keys"),
    }

    if name in _LAZY:
        from importlib import import_module

        module_name, attr = _LAZY[name]
        return getattr(import_module(module_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ConsistentHashRing",
    "HashModPartitioner",
    "RangePartitioner",
    "RoundRobinPartitioner",
    "__version__",
    "generate_keys",
]
