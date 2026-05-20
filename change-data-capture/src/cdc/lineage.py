"""Row lineage — per-row history aggregated from a CDC stream.

For audit trails and SCD-style dimension tracking we surface one
``RowLineage`` per ``(table, pk)`` with:

* ``created_at_ms`` — timestamp of the first INSERT / READ
* ``last_modified_at_ms`` — timestamp of the most recent event
* ``n_updates`` — count of UPDATE events
* ``is_deleted`` — has a DELETE been observed?

Events that fail invariants (e.g. an UPDATE for a row we've never
seen create) are *silently skipped* in lineage tracking — the goal
is to summarise the actual observed history, not enforce strict
state-machine semantics. Use ``cdc.replay`` for that.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from cdc.schema import Op, RowLineage

if TYPE_CHECKING:
    from cdc.schema import CDCEvent


@dataclass(slots=True)
class _LineageState:
    """Mutable per-row scratch buffer used while walking the event log."""

    created_at_ms: int
    last_modified_at_ms: int
    n_updates: int
    is_deleted: bool


def build_lineage(events: list[CDCEvent]) -> list[RowLineage]:
    """Aggregate events into per-row lineage records.

    Output sorted by ``(table, pk)`` ascending.
    """
    # Walk events in position order so created_at_ms reflects the earliest event.
    ordered = sorted(events, key=lambda e: (e.position.log_file, e.position.offset))
    per_row: dict[tuple[str, str], _LineageState] = {}

    for event in ordered:
        key = (event.table, event.pk)
        if key not in per_row:
            # First sighting — the event must be a creation.
            if event.op in {Op.CREATE, Op.READ}:
                per_row[key] = _LineageState(
                    created_at_ms=event.ts_ms,
                    last_modified_at_ms=event.ts_ms,
                    n_updates=0,
                    is_deleted=False,
                )
            # First-sight UPDATE/DELETE without prior CREATE → skipped.
            continue
        state = per_row[key]
        # Keep monotonic semantics for last_modified_at_ms: an out-of-order
        # event with a smaller ts_ms shouldn't push the timestamp backward
        # (which would violate the schema invariant last_modified >= created).
        if event.ts_ms > state.last_modified_at_ms:
            state.last_modified_at_ms = event.ts_ms
        if event.op is Op.UPDATE:
            state.n_updates += 1
        elif event.op is Op.DELETE:
            state.is_deleted = True

    out: list[RowLineage] = []
    for (table, pk), state in per_row.items():
        out.append(
            RowLineage(
                table=table,
                pk=pk,
                created_at_ms=state.created_at_ms,
                last_modified_at_ms=state.last_modified_at_ms,
                n_updates=state.n_updates,
                is_deleted=state.is_deleted,
            )
        )
    out.sort(key=lambda r: (r.table, r.pk))
    return out


__all__ = ["build_lineage"]
