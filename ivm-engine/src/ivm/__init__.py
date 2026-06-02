"""Incremental View Maintenance Engine.

Quick start
-----------
    from ivm import IVMEngine
    import ivm.aggregates as agg
"""

from __future__ import annotations

from ivm import aggregates as agg
from ivm.engine import IVMEngine
from ivm.operators import (
    PartitionWindow,
    SlidingWindow,
    TumblingWindow,
)

__all__ = [
    "IVMEngine",
    "agg",
    "TumblingWindow",
    "SlidingWindow",
    "PartitionWindow",
]

__version__ = "0.1.0"
