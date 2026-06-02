"""Adaptive Radix Tree + MVCC.

Top-level facade:
    from art_mvcc import ART, MVCCArt, Snapshot
"""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY: dict[str, str] = {
        "ART": "art_mvcc.art.tree",
        "MVCCArt": "art_mvcc.mvcc.store",
        "Snapshot": "art_mvcc.mvcc.store",
    }
    mod = _LAZY.get(name)
    if mod is None:
        raise AttributeError(f"module 'art_mvcc' has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(mod), name)


__all__ = ["ART", "MVCCArt", "Snapshot"]
