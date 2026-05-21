"""Count-Min Sketch: sub-linear space frequency estimator."""

from __future__ import annotations


def __getattr__(name: str) -> object:
    _LAZY = {
        "CountMinSketch": ("cmsketch.sketch", "CountMinSketch"),
    }
    if name in _LAZY:
        mod_name, attr = _LAZY[name]
        import importlib

        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(name)


__all__ = ["CountMinSketch"]
