"""
Logical and physical expression nodes for the query plan tree.

In the Cascades framework, every node in the memo table is an Expression
referencing child *groups* (by ID) rather than child expressions directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto


class JoinType(Enum):
    INNER = auto()
    LEFT = auto()


class PhysicalOp(Enum):
    HASH_JOIN = "HashJoin"
    MERGE_JOIN = "MergeJoin"
    NESTED_LOOP = "NestedLoop"
    SEQ_SCAN = "SeqScan"


@dataclass(frozen=True)
class Predicate:
    """Equi-join predicate: left_table.col = right_table.col"""

    left_table: str
    left_col: str
    right_table: str
    right_col: str

    def __str__(self) -> str:
        return f"{self.left_table}.{self.left_col} = {self.right_table}.{self.right_col}"

    def involves(self, tables: frozenset[str]) -> bool:
        return self.left_table in tables and self.right_table in tables

    def flipped(self) -> Predicate:
        return Predicate(self.right_table, self.right_col, self.left_table, self.left_col)


# ---------------------------------------------------------------------------
# Logical expressions
# ---------------------------------------------------------------------------


class LogicalExpr:
    """Base class for logical (algebraic) expressions."""

    def children(self) -> list[int]:  # returns group IDs
        return []

    def tables(self) -> frozenset[str]:
        raise NotImplementedError


@dataclass(frozen=True)
class Scan(LogicalExpr):
    """Leaf: full sequential scan of a base table."""

    table: str

    def children(self) -> list[int]:
        return []

    def tables(self) -> frozenset[str]:
        return frozenset([self.table])

    def __str__(self) -> str:
        return f"Scan({self.table})"


@dataclass(frozen=True)
class LogicalJoin(LogicalExpr):
    """Inner join of two groups, identified by group IDs."""

    left_group: int
    right_group: int
    predicates: tuple[Predicate, ...] = field(default_factory=tuple)
    join_type: JoinType = JoinType.INNER

    def children(self) -> list[int]:
        return [self.left_group, self.right_group]

    def tables(self) -> frozenset[str]:
        # Resolved via memo; used when tables are embedded (not normally here)
        return frozenset()

    def __str__(self) -> str:
        preds = ", ".join(str(p) for p in self.predicates)
        return f"LogicalJoin({self.left_group} ⋈ {self.right_group} ON [{preds}])"


# ---------------------------------------------------------------------------
# Physical expressions
# ---------------------------------------------------------------------------


class PhysicalExpr:
    """Base class for physical (executable) expressions."""

    def children(self) -> list[int]:
        return []

    @property
    def op(self) -> PhysicalOp:
        raise NotImplementedError


@dataclass(frozen=True)
class PhysicalScan(PhysicalExpr):
    table: str

    @property
    def op(self) -> PhysicalOp:
        return PhysicalOp.SEQ_SCAN

    def children(self) -> list[int]:
        return []

    def __str__(self) -> str:
        return f"SeqScan({self.table})"


@dataclass(frozen=True)
class PhysicalJoin(PhysicalExpr):
    left_group: int
    right_group: int
    algorithm: PhysicalOp
    predicates: tuple[Predicate, ...] = field(default_factory=tuple)

    @property
    def op(self) -> PhysicalOp:
        return self.algorithm

    def children(self) -> list[int]:
        return [self.left_group, self.right_group]

    def __str__(self) -> str:
        preds = ", ".join(str(p) for p in self.predicates)
        return f"{self.algorithm.value}({self.left_group} ⋈ {self.right_group} ON [{preds}])"
