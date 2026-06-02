"""Incremental view maintenance: hard cases.

Window functions, correlated subqueries, nested aggregates.
"""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY: dict[str, str] = {
        "RowNumberIVM": "ivm.window.row_number",
        "CorrelatedSubqueryIVM": "ivm.correlated.subquery",
        "MaxOfSum": "ivm.nested.max_of_sum",
        "StrategyController": "ivm.strategy.controller",
    }
    mod = _LAZY.get(name)
    if mod is None:
        raise AttributeError(f"module 'ivm' has no attribute {name!r}")
    import importlib

    return getattr(importlib.import_module(mod), name)


__all__ = ["CorrelatedSubqueryIVM", "MaxOfSum", "RowNumberIVM", "StrategyController"]
