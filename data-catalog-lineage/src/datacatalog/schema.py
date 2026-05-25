"""Data types for the catalog and lineage graph."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field


class PIICategory(str, enum.Enum):
    EMAIL = "EMAIL"
    PHONE = "PHONE"
    SSN = "SSN"
    CREDIT_CARD = "CREDIT_CARD"
    NAME = "NAME"
    ADDRESS = "ADDRESS"
    DATE_OF_BIRTH = "DATE_OF_BIRTH"
    IP_ADDRESS = "IP_ADDRESS"
    PASSWORD = "PASSWORD"
    NATIONAL_ID = "NATIONAL_ID"
    PASSPORT = "PASSPORT"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    HEALTH = "HEALTH"
    BIOMETRIC = "BIOMETRIC"
    NONE = "NONE"


@dataclass
class Column:
    name: str
    dtype: str = ""
    nullable: bool = True
    pii: PIICategory = PIICategory.NONE
    sample_values: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class Table:
    name: str
    schema: str = "public"
    source_id: str = ""
    row_count: int = 0
    columns: list[Column] = field(default_factory=list)
    description: str = ""
    tags: list[str] = field(default_factory=list)

    @property
    def fqn(self) -> str:
        """Fully-qualified name: source.schema.table."""
        return f"{self.source_id}.{self.schema}.{self.name}"

    def pii_columns(self) -> list[Column]:
        return [c for c in self.columns if c.pii != PIICategory.NONE]


@dataclass
class DataSource:
    source_id: str
    name: str
    db_type: str = "sqlite"
    tables: list[Table] = field(default_factory=list)
    description: str = ""


@dataclass(frozen=True)
class ColumnRef:
    """Uniquely identifies a (source, schema, table, column)."""

    source_id: str
    schema: str
    table: str
    column: str

    def __str__(self) -> str:
        return f"{self.source_id}.{self.schema}.{self.table}.{self.column}"


@dataclass(frozen=True)
class LineageEdge:
    """Directed edge in the column-level lineage graph."""

    source: ColumnRef
    target: ColumnRef
    job_id: str
    transform: str = ""  # optional SQL snippet or description
