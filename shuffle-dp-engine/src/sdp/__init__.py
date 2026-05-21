"""Shuffle-model differential privacy.

A protocol family that combines local randomization (LDP) at each user
with a cryptographic shuffler before aggregation. The shuffle amplifies
local ε₀ to a tighter central ε via Balle et al.'s bound.
"""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY: dict[str, str] = {
        "LocalConfig": "sdp.local.randomizers",
        "MixNode": "sdp.shuffler.mix",
        "shuffle": "sdp.shuffler.mix",
        "ShuffleBound": "sdp.analyzer.balle",
        "shuffle_amplification": "sdp.analyzer.balle",
        "composed_bound": "sdp.analyzer.composition",
        "private_histogram": "sdp.queries.histogram",
    }
    mod = _LAZY.get(name)
    if mod is None:
        raise AttributeError(f"module 'sdp' has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(mod), name)


__all__ = [
    "LocalConfig",
    "MixNode",
    "ShuffleBound",
    "composed_bound",
    "private_histogram",
    "shuffle",
    "shuffle_amplification",
]
