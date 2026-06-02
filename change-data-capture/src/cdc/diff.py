"""Column-level diff for UPDATE events.

CDC envelopes typically ship the *full* before+after row, even when a
single column changed. For downstream sinks that only need the delta
(e.g. dimension-table SCD2, audit logs), this module exposes:

* ``change_vector(event)`` — strip an UPDATE down to the columns that
  actually changed. Returns a ``ChangeVector`` whose ``changed_columns``
  property gives the diff column-set.

* ``columns_changed(event)`` — convenience: just the changed-column
  names, sorted.

* ``is_no_op_update(event)`` — ``True`` when before == after on every
  column (a *touch* with no real change; common in CDC streams from
  trigger-based capture).

For non-UPDATE events the helpers raise ``ValueError`` — diff is only
meaningful when both ``before`` and ``after`` are populated.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cdc.schema import ChangeVector, Op

if TYPE_CHECKING:
    from cdc.schema import CDCEvent


def change_vector(event: CDCEvent) -> ChangeVector:
    """Return the per-column diff for an UPDATE event.

    The result's ``before_values`` and ``after_values`` contain only
    the columns whose value actually changed.
    """
    if event.op is not Op.UPDATE:
        raise ValueError(
            f"change_vector is only defined for UPDATE events, got {event.op.name}",
        )
    # Compare every column appearing in either side.
    keys = set(event.before.keys()) | set(event.after.keys())
    before_diff = {}
    after_diff = {}
    for k in keys:
        b = event.before.get(k)
        a = event.after.get(k)
        if b != a:
            before_diff[k] = b
            after_diff[k] = a
    return ChangeVector(
        table=event.table,
        pk=event.pk,
        before_values=before_diff,
        after_values=after_diff,
    )


def columns_changed(event: CDCEvent) -> tuple[str, ...]:
    """Names of columns that changed in an UPDATE, sorted ascending."""
    return change_vector(event).changed_columns


def is_no_op_update(event: CDCEvent) -> bool:
    """``True`` if the UPDATE event has identical before and after rows."""
    if event.op is not Op.UPDATE:
        raise ValueError(
            f"is_no_op_update only applies to UPDATE events, got {event.op.name}",
        )
    return event.before == event.after


__all__ = ["change_vector", "columns_changed", "is_no_op_update"]
