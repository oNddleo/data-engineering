"""B^epsilon-tree: a write-optimized B-tree with message-buffered nodes.

Public API:
    from beps import BEpsilonTree, EpsilonTuner
"""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY: dict[str, str] = {
        "BEpsilonTree": "beps.tree.tree",
        "EpsilonTuner": "beps.tuner.epsilon",
        "WriteAmpStats": "beps.stats.amplification",
    }
    mod = _LAZY.get(name)
    if mod is None:
        raise AttributeError(f"module 'beps' has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(mod), name)


__all__ = ["BEpsilonTree", "EpsilonTuner", "WriteAmpStats"]
