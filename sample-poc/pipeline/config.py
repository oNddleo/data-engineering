"""Per-table ingestion spec: source table -> bronze, with PK + watermark column."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableSpec:
    name: str
    primary_key: str
    watermark_col: str


# Order matters for FK-friendly reads, though bronze is append-only and unconstrained.
TABLES: list[TableSpec] = [
    TableSpec("customers", "id", "updated_at"),
    TableSpec("products", "id", "updated_at"),
    TableSpec("orders", "id", "updated_at"),
    TableSpec("order_items", "id", "updated_at"),
]
