"""partitioner-toolkit — range / hash / consistent / round-robin partitioners."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

_LAZY: dict[str, tuple[str, str]] = {
    "HashModPartitioner": ("partitioner.hash_mod", "HashModPartitioner"),
    "RangePartitioner": ("partitioner.range_part", "RangePartitioner"),
    "ConsistentHashRing": ("partitioner.consistent", "ConsistentHashRing"),
    "RoundRobinPartitioner": ("partitioner.round_robin", "RoundRobinPartitioner"),
    "generate_keys": ("partitioner.simulator", "generate_keys"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        module_name, attr = _LAZY[name]
        return getattr(import_module(module_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:
    from partitioner.consistent import ConsistentHashRing
    from partitioner.hash_mod import HashModPartitioner
    from partitioner.range_part import RangePartitioner
    from partitioner.round_robin import RoundRobinPartitioner
    from partitioner.simulator import generate_keys

__all__ = [
    "ConsistentHashRing",
    "HashModPartitioner",
    "RangePartitioner",
    "RoundRobinPartitioner",
    "__version__",
    "generate_keys",
]
