"""Physical Plan Compiler — Cascades-style cross-engine query optimizer.

Public API:
    from ppc import compile_sql, Optimizer
    compile_sql(sql, catalog) -> PhysicalPlan       # one-shot SQL → physical plan
    Optimizer(catalog).optimize(logical) -> PhysicalPlan
"""

from __future__ import annotations

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    _LAZY: dict[str, str] = {
        "Optimizer": "ppc.cascades.optimizer",
        "compile_sql": "ppc.frontend.sql",
        "PhysicalPlan": "ppc.ir.physical",
        "LogicalScan": "ppc.ir.logical",
        "LogicalFilter": "ppc.ir.logical",
        "LogicalAggregate": "ppc.ir.logical",
        "LogicalJoin": "ppc.ir.logical",
    }
    mod_path = _LAZY.get(name)
    if mod_path is None:
        raise AttributeError(f"module 'ppc' has no attribute {name!r}")
    import importlib

    mod = importlib.import_module(mod_path)
    return getattr(mod, name)


__all__ = [
    "LogicalAggregate",
    "LogicalFilter",
    "LogicalJoin",
    "LogicalScan",
    "Optimizer",
    "PhysicalPlan",
    "compile_sql",
]
