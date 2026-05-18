"""Diff two dimension snapshots → DimensionChange events.

The detector is a pure function over ``(old, new, as_of, tracked_attrs)``:

* Natural keys in ``new`` but not ``old`` → ``INSERT``.
* Natural keys in ``old`` but not ``new`` → ``DELETE``.
* Natural keys in both with **any tracked attribute different** →
  ``UPDATE`` (with the list of changed attrs).
* Natural keys in both with no tracked-attribute changes → silently
  skipped (no change event).

``tracked_attrs`` lets callers pin which attributes drive Type-2 row
creation. A change to a *non-tracked* attribute (e.g. a timestamp
that updates on every load) doesn't emit an UPDATE event — that
distinction is what prevents the common SCD-2 mistake of creating
a new history row on every batch load.

When ``tracked_attrs=None``, all attributes are tracked.

Output is sorted by ``(kind, natural_key)`` for stable diffs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from scdkit.schema import ChangeKind, DimensionChange

if TYPE_CHECKING:
    from datetime import datetime


def detect(
    old: dict[str, dict[str, str]],
    new: dict[str, dict[str, str]],
    *,
    as_of: datetime,
    tracked_attrs: list[str] | None = None,
) -> list[DimensionChange]:
    """Compute the diff between two snapshots.

    ``old`` and ``new`` map ``natural_key → attribute_dict``.
    """
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone-aware")
    out: list[DimensionChange] = []

    old_keys = set(old)
    new_keys = set(new)

    # INSERTs
    for k in new_keys - old_keys:
        out.append(
            DimensionChange(
                natural_key=k,
                kind=ChangeKind.INSERT,
                detected_at=as_of,
                before=None,
                after=dict(new[k]),
            )
        )

    # DELETEs
    for k in old_keys - new_keys:
        out.append(
            DimensionChange(
                natural_key=k,
                kind=ChangeKind.DELETE,
                detected_at=as_of,
                before=dict(old[k]),
                after=None,
            )
        )

    # UPDATEs (and silent no-ops)
    for k in old_keys & new_keys:
        before = old[k]
        after = new[k]
        attrs_to_check = set(before) | set(after) if tracked_attrs is None else set(tracked_attrs)
        changed = sorted(a for a in attrs_to_check if before.get(a) != after.get(a))
        if not changed:
            continue
        out.append(
            DimensionChange(
                natural_key=k,
                kind=ChangeKind.UPDATE,
                detected_at=as_of,
                before=dict(before),
                after=dict(after),
                changed_attrs=tuple(changed),
            )
        )

    out.sort(key=lambda c: (c.kind.value, c.natural_key))
    return out


def n_changes_by_kind(changes: list[DimensionChange]) -> dict[ChangeKind, int]:
    """Roll up counts per change kind — for dashboards."""
    counts: dict[ChangeKind, int] = {k: 0 for k in ChangeKind}
    for c in changes:
        counts[c.kind] += 1
    return counts


__all__ = ["detect", "n_changes_by_kind"]
