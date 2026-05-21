"""Schema for sorted-run records and merge results.

A *run* is a sorted sequence of ``(key, seq, value, tombstone)`` records.
Within a run, keys are non-decreasing. Across runs, the same key may
appear multiple times — the merge picks the record with the **highest
sequence number** (last-write-wins).

Tombstone semantics:

* ``tombstone=True`` means "delete this key".
* When a tombstone wins a key during merge, the record is dropped from
  the output (unless ``keep_tombstones=True``, useful for non-final
  compaction levels that still need to shadow lower levels).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Record:
    """One LSM record: ``(key, seq, value, tombstone)``.

    Ordering is by ``key`` ascending, then ``seq`` descending so the
    newest version of a duplicate key sorts first.
    """

    key: str
    seq: int
    value: str = ""
    tombstone: bool = False

    def __post_init__(self) -> None:
        if self.seq < 0:
            raise ValueError("seq must be >= 0")
        if self.tombstone and self.value:
            raise ValueError("tombstone records must have empty value")


__all__ = ["Record"]
