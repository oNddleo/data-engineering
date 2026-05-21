"""Schema registry lite."""

from __future__ import annotations


def __getattr__(name: str) -> object:
    _LAZY = {
        "SchemaEntry": ("schemreg.registry", "SchemaEntry"),
        "CompatibilityMode": ("schemreg.registry", "CompatibilityMode"),
        "SchemaRegistry": ("schemreg.registry", "SchemaRegistry"),
        "CompatibilityError": ("schemreg.registry", "CompatibilityError"),
    }
    if name in _LAZY:
        mod_name, attr = _LAZY[name]
        import importlib

        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(name)


__all__ = ["SchemaEntry", "CompatibilityMode", "SchemaRegistry", "CompatibilityError"]
