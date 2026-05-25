"""CRDT composition algebra — semilattice-based CRDTs with delta-state sync."""

from __future__ import annotations


def __getattr__(name: str) -> object:
    _LAZY: dict[str, str] = {
        "GCounter": "crdt.crdts",
        "PNCounter": "crdt.crdts",
        "LWWRegister": "crdt.crdts",
        "GSet": "crdt.crdts",
        "TwoPSet": "crdt.crdts",
        "ORSet": "crdt.crdts",
        "MVRegister": "crdt.crdts",
        "merge": "crdt.lattice",
        "Lattice": "crdt.lattice",
    }
    mod = _LAZY.get(name)
    if mod is None:
        raise AttributeError(f"module 'crdt' has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(mod), name)
