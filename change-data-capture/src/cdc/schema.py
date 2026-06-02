"""CDC schema — Debezium-style change events.

A **change-data-capture** (CDC) event represents a single row-level
mutation on a source database. Every modern streaming-CDC pipeline
(Debezium, Maxwell, Airbyte CDC, ksqlDB, etc.) uses essentially the
same envelope shape:

.. code:: json

    {
      "op": "u",
      "ts_ms": 1715251200000,
      "source": {"db": "shop", "table": "orders"},
      "pk": "42",
      "before": {"id": 42, "status": "pending", "total_vnd": 100000},
      "after":  {"id": 42, "status": "paid", "total_vnd": 100000},
      "position": "binlog.000123:4567"
    }

We model this with strict per-operation invariants:

| Op            | ``before``     | ``after``      |
| ------------- | -------------- | -------------- |
| ``INSERT (c)``| empty          | row state      |
| ``UPDATE (u)``| previous state | new state      |
| ``DELETE (d)``| previous state | empty          |
| ``READ (r)``  | empty          | snapshot state |

``READ`` (op=``r``) events come from an *initial snapshot* (e.g.
Debezium's `snapshot.mode = initial`). They're treated identically to
``INSERT`` by ``replay`` but carry a distinct op for audit purposes.

Column values are typed as ``str | int | float | bool | None`` — the
JSON-native scalars. Larger structures (nested JSON, blobs) should be
serialized by the producer to a JSON-string field at the source.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

# JSON-native scalar union (None included for SQL NULL).
ColumnValue = str | int | float | bool | None
RowState = dict[str, ColumnValue]


class Op(str, Enum):
    """Four event kinds — the canonical Debezium ``op`` field values."""

    CREATE = "c"  # INSERT
    UPDATE = "u"  # UPDATE
    DELETE = "d"  # DELETE
    READ = "r"  # initial-snapshot READ (treated as INSERT by replay)


@dataclass(frozen=True, slots=True)
class EventPosition:
    """Source-side total ordering — used to resolve out-of-order events.

    Real-world examples: MySQL binlog file + offset, Postgres LSN,
    MongoDB resume token. We model it as ``(log_file, offset)`` so
    every CDC source can map onto a strict lexicographic ordering.
    """

    log_file: str
    offset: int

    def __post_init__(self) -> None:
        if self.offset < 0:
            raise ValueError(f"offset must be >= 0, got {self.offset}")

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, EventPosition):
            return NotImplemented
        return (self.log_file, self.offset) < (other.log_file, other.offset)

    def __le__(self, other: object) -> bool:
        if not isinstance(other, EventPosition):
            return NotImplemented
        return (self.log_file, self.offset) <= (other.log_file, other.offset)


@dataclass(frozen=True, slots=True)
class CDCEvent:
    """One row-level change event.

    The ``pk`` field is the **string-serialized primary key** of the
    row — for composite keys, callers should join with a separator
    (e.g. ``"42|tenant-7"``). Using a string keeps every PK uniform
    across tables for codec + index purposes.
    """

    op: Op
    table: str  # e.g. "orders"
    pk: str
    ts_ms: int  # source-side timestamp, ms since epoch
    position: EventPosition
    before: RowState = field(default_factory=dict)
    after: RowState = field(default_factory=dict)
    db: str = ""  # source database, optional

    def __post_init__(self) -> None:
        if not self.table:
            raise ValueError("table must be non-empty")
        if not self.pk:
            raise ValueError("pk must be non-empty")
        if self.ts_ms < 0:
            raise ValueError(f"ts_ms must be >= 0, got {self.ts_ms}")

        # Per-op invariants.
        if self.op in {Op.CREATE, Op.READ}:
            if self.before:
                raise ValueError(
                    f"{self.op.name} event must have empty before, " f"got {self.before!r}",
                )
            if not self.after:
                raise ValueError(f"{self.op.name} event must have non-empty after")
        elif self.op is Op.UPDATE:
            if not self.before:
                raise ValueError("UPDATE event must have non-empty before")
            if not self.after:
                raise ValueError("UPDATE event must have non-empty after")
        elif self.op is Op.DELETE:
            if not self.before:
                raise ValueError("DELETE event must have non-empty before")
            if self.after:
                raise ValueError(
                    f"DELETE event must have empty after, got {self.after!r}",
                )


@dataclass(frozen=True, slots=True)
class ChangeVector:
    """The set of columns that changed in an UPDATE — keyed by column name.

    ``before_values`` and ``after_values`` map the changed columns
    only; unchanged columns are not included (a no-op UPDATE produces
    an empty ChangeVector).
    """

    table: str
    pk: str
    before_values: RowState
    after_values: RowState

    def __post_init__(self) -> None:
        if not self.table:
            raise ValueError("table must be non-empty")
        if not self.pk:
            raise ValueError("pk must be non-empty")
        if set(self.before_values.keys()) != set(self.after_values.keys()):
            raise ValueError(
                "before_values and after_values must share the same column set",
            )

    @property
    def changed_columns(self) -> tuple[str, ...]:
        """Names of columns whose value changed, sorted ascending."""
        return tuple(sorted(self.before_values.keys()))

    @property
    def is_no_op(self) -> bool:
        """``True`` if the change vector is empty (no-op UPDATE)."""
        return not self.before_values


@dataclass(frozen=True, slots=True)
class RowLineage:
    """Per-row history aggregated from a stream of CDC events."""

    table: str
    pk: str
    created_at_ms: int  # ts of the first INSERT / READ
    last_modified_at_ms: int  # ts of the most recent event
    n_updates: int  # count of UPDATE events seen
    is_deleted: bool  # has a DELETE been observed?

    def __post_init__(self) -> None:
        if self.created_at_ms < 0 or self.last_modified_at_ms < 0:
            raise ValueError("timestamps must be >= 0")
        if self.last_modified_at_ms < self.created_at_ms:
            raise ValueError(
                f"last_modified_at_ms ({self.last_modified_at_ms}) "
                f"must be >= created_at_ms ({self.created_at_ms})",
            )
        if self.n_updates < 0:
            raise ValueError(f"n_updates must be >= 0, got {self.n_updates}")


__all__ = [
    "CDCEvent",
    "ChangeVector",
    "ColumnValue",
    "EventPosition",
    "Op",
    "RowLineage",
    "RowState",
]
