"""Core types for the IVM engine.

Every piece of data flowing through the system is an Update triple:
  (record, timestamp, diff)

diff = +1 means "this record was inserted"
diff = -1 means "this record was retracted (corrected)"
diff >  1 or < -1 is valid (multiplicities, e.g. after a join).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

# A record is an immutable-friendly dict of column -> value.
Record = dict[str, Any]

# Logical or wall-clock timestamp (milliseconds).
Timestamp = int

# Signed multiplicity: +1 insertion, -1 retraction.
Diff = int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def record_key(record: Record, columns: list[str]) -> tuple[Any, ...]:
    """Extract a hashable key from selected columns of a record."""
    return tuple(record[col] for col in columns)


def freeze_record(record: Record) -> tuple[tuple[str, Any], ...]:
    """Convert a record dict to a sorted, hashable tuple."""
    return tuple(sorted(record.items()))


def unfreeze_record(frozen: tuple[tuple[str, Any], ...]) -> Record:
    """Convert a frozen record back to a dict."""
    return dict(frozen)


def merge_records(left: Record, right: Record, prefix_conflict: bool = True) -> Record:
    """Merge two records for join output. Right columns shadow left on conflict."""
    result = dict(left)
    result.update(right)
    return result


def now_ms() -> int:
    """Return the current wall-clock time in milliseconds."""
    return int(time.time() * 1_000)


# ---------------------------------------------------------------------------
# Update — the fundamental unit of differential dataflow
# ---------------------------------------------------------------------------


@dataclass
class Update:
    """A single differential update: record appeared or was retracted at a time."""

    record: Record
    timestamp: Timestamp
    diff: Diff

    def retract(self) -> Update:
        """Return a copy of this update with negated diff."""
        return Update(dict(self.record), self.timestamp, -self.diff)

    def __repr__(self) -> str:  # pragma: no cover
        sign = "+" if self.diff > 0 else ""
        return f"Update({sign}{self.diff} {self.record} @t={self.timestamp})"
