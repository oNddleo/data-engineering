"""BFT stream — Byzantine Fault-Tolerant streaming with PBFT watermark consensus."""

from __future__ import annotations


def __getattr__(name: str) -> object:
    _LAZY: dict[str, str] = {
        "StreamRecord": "bftstream.schema",
        "WindowAggregate": "bftstream.schema",
        "WatermarkProposal": "bftstream.schema",
        "MessageType": "bftstream.schema",
        "BFTMessage": "bftstream.schema",
        "ReplicaState": "bftstream.schema",
        "PBFTConsensus": "bftstream.pbft",
        "BFTReplica": "bftstream.replica",
        "BFTCluster": "bftstream.cluster",
    }
    mod = _LAZY.get(name)
    if mod is None:
        raise AttributeError(f"module 'bftstream' has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(mod), name)
