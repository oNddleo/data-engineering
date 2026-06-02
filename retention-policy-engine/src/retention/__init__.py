"""Data retention policy engine."""

from __future__ import annotations


def __getattr__(name: str) -> object:
    _LAZY = {
        "Policy": ("retention.policy", "Policy"),
        "PolicyKind": ("retention.policy", "PolicyKind"),
        "Record": ("retention.schema", "Record"),
        "EvictionResult": ("retention.engine", "EvictionResult"),
        "apply_policy": ("retention.engine", "apply_policy"),
    }
    if name in _LAZY:
        mod_name, attr = _LAZY[name]
        import importlib

        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(name)


__all__ = ["Policy", "PolicyKind", "Record", "EvictionResult", "apply_policy"]
