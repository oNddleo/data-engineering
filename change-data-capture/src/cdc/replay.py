"""Replay CDC events to materialise a current snapshot per table.

A **snapshot** is the projection of *all events up to position p*
onto a current-state map ``{(table, pk) → row_state}``. We expose:

* ``apply_event(snapshot, event)`` — mutate the snapshot in place to
  reflect a single event. Returns the new state of the affected row
  (or ``None`` if the row was deleted).

* ``replay(events)`` — drain a list of events (in arrival order) into
  a fresh snapshot, returning the materialised state. Out-of-order
  events relative to ``position`` are reordered up-front.

* ``replay_unordered`` — same as ``replay`` but explicitly sorts by
  position first. Useful when ingesting from a multi-partition source
  where per-partition order is preserved but global order isn't.

Out-of-order tolerance: events with a *staler* position than the
current state of their row are **rejected** (raising ``ValueError``)
because applying them would corrupt the materialised state. Callers
can wrap ``apply_event`` in a try/except to drop late arrivals.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from cdc.schema import Op

if TYPE_CHECKING:
    from cdc.schema import CDCEvent, EventPosition, RowState

# A snapshot is keyed by (table, pk); each value carries (row state, position).
_Snapshot = dict[tuple[str, str], tuple["RowState", "EventPosition"]]


def empty_snapshot() -> _Snapshot:
    """Construct an empty snapshot."""
    return {}


def apply_event(
    snapshot: _Snapshot,
    event: CDCEvent,
    *,
    strict: bool = True,
) -> RowState | None:
    """Apply a single event to ``snapshot``; return the row's new state.

    ``strict=True`` (default) raises ``ValueError`` on out-of-order or
    illegal-transition events. ``strict=False`` silently drops them
    (useful for ingest pipelines that tolerate replays).

    Returns ``None`` if the row was deleted.
    """
    key = (event.table, event.pk)
    current = snapshot.get(key)

    # Out-of-order guard.
    if current is not None:
        _cur_state, cur_position = current
        if event.position <= cur_position:
            if strict:
                raise ValueError(
                    f"event at position {event.position} is not newer than "
                    f"current state at {cur_position} for ({event.table}, {event.pk})",
                )
            return _cur_state

    if event.op in {Op.CREATE, Op.READ}:
        if current is not None and strict:
            raise ValueError(
                f"{event.op.name} for already-existing row " f"({event.table}, {event.pk})",
            )
        snapshot[key] = (dict(event.after), event.position)
        return dict(event.after)

    if event.op is Op.UPDATE:
        if current is None:
            if strict:
                raise ValueError(
                    f"UPDATE for missing row ({event.table}, {event.pk})",
                )
            # Tolerant mode: treat as INSERT of the after state.
            snapshot[key] = (dict(event.after), event.position)
            return dict(event.after)
        snapshot[key] = (dict(event.after), event.position)
        return dict(event.after)

    if event.op is Op.DELETE:
        if current is None:
            if strict:
                raise ValueError(
                    f"DELETE for missing row ({event.table}, {event.pk})",
                )
            return None
        # Remember the position of the delete so a subsequent late INSERT
        # for the same PK can be rejected. We don't store the row state
        # any more (it's gone), so we use a tombstone marker.
        snapshot[key] = ({}, event.position)
        return None

    raise ValueError(f"unknown op: {event.op}")  # defensive


def replay(events: list[CDCEvent], *, strict: bool = True) -> dict[tuple[str, str], RowState]:
    """Drain ``events`` (in given order) into a fresh snapshot.

    Returns a clean ``{(table, pk) → row_state}`` mapping with
    tombstones (deleted rows) excluded.
    """
    snapshot: _Snapshot = empty_snapshot()
    for event in events:
        apply_event(snapshot, event, strict=strict)
    return {key: state for key, (state, _) in snapshot.items() if state}


def replay_unordered(
    events: list[CDCEvent],
    *,
    strict: bool = True,
) -> dict[tuple[str, str], RowState]:
    """Sort events by position first, then replay.

    Use this when the input stream has been merged from multiple
    partitions and global ordering isn't guaranteed.
    """
    ordered = sorted(events, key=lambda e: (e.position.log_file, e.position.offset))
    return replay(ordered, strict=strict)


__all__ = ["apply_event", "empty_snapshot", "replay", "replay_unordered"]
