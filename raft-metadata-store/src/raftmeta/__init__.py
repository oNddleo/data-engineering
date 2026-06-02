"""Raft Metadata Store — stdlib-only Raft consensus simulation."""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY: dict[str, str] = {
        "NodeState": "raftmeta.schema",
        "LogEntry": "raftmeta.schema",
        "RaftMessage": "raftmeta.schema",
        "MessageType": "raftmeta.schema",
        "RaftNode": "raftmeta.node",
        "RaftCluster": "raftmeta.cluster",
        "MetadataStore": "raftmeta.store",
    }
    mod = _LAZY.get(name)
    if mod is None:
        raise AttributeError(f"module 'raftmeta' has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(mod), name)


__all__ = [
    "LogEntry",
    "MessageType",
    "MetadataStore",
    "NodeState",
    "RaftCluster",
    "RaftMessage",
    "RaftNode",
]
