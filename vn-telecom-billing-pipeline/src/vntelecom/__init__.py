"""Vietnam telecom CDR billing pipeline."""

from __future__ import annotations


def __getattr__(name: str) -> object:
    _LAZY = {
        "Operator": ("vntelecom.schema", "Operator"),
        "CallType": ("vntelecom.schema", "CallType"),
        "ServiceType": ("vntelecom.schema", "ServiceType"),
        "CDR": ("vntelecom.schema", "CDR"),
        "BilledCDR": ("vntelecom.billing", "BilledCDR"),
        "bill": ("vntelecom.billing", "bill"),
    }
    if name in _LAZY:
        mod_name, attr = _LAZY[name]
        import importlib

        mod = importlib.import_module(mod_name)
        return getattr(mod, attr)
    raise AttributeError(name)


__all__ = ["Operator", "CallType", "ServiceType", "CDR", "BilledCDR", "bill"]
