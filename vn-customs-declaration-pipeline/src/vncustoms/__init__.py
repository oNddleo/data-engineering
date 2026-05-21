"""vn-customs-declaration-pipeline — HS-code-aware tariff calculator."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__version__ = "0.1.0"

_LAZY: dict[str, tuple[str, str]] = {
    "Declaration": ("vncustoms.schema", "Declaration"),
    "DeclarationKind": ("vncustoms.schema", "DeclarationKind"),
    "HSCode": ("vncustoms.schema", "HSCode"),
    "Incoterm": ("vncustoms.schema", "Incoterm"),
    "LineItem": ("vncustoms.schema", "LineItem"),
    "DeclarationCalc": ("vncustoms.calc", "DeclarationCalc"),
    "LineCalc": ("vncustoms.calc", "LineCalc"),
    "compute": ("vncustoms.calc", "compute"),
    "duty_rate_for": ("vncustoms.tariff", "duty_rate_for"),
    "vat_rate_for": ("vncustoms.tariff", "vat_rate_for"),
    "generate": ("vncustoms.simulator", "generate"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY:
        from importlib import import_module

        module_name, attr = _LAZY[name]
        return getattr(import_module(module_name), attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:
    from vncustoms.calc import DeclarationCalc, LineCalc, compute
    from vncustoms.schema import (
        Declaration,
        DeclarationKind,
        HSCode,
        Incoterm,
        LineItem,
    )
    from vncustoms.simulator import generate
    from vncustoms.tariff import duty_rate_for, vat_rate_for

__all__ = [
    "Declaration",
    "DeclarationCalc",
    "DeclarationKind",
    "HSCode",
    "Incoterm",
    "LineCalc",
    "LineItem",
    "__version__",
    "compute",
    "duty_rate_for",
    "generate",
    "vat_rate_for",
]
