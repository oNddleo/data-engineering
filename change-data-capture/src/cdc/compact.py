"""Log compaction — keep only the *latest* event per primary key.

Kafka-style log compaction: many real CDC consumers don't care about
the full history of a row, only its current state. We provide:

* ``compact(events)`` — collapse to one event per ``(table, pk)``,
  picking the one with the latest ``position``. INSERTs followed by
  DELETEs collapse to a single DELETE; DELETEs followed by re-INSERTs
  collapse to the INSERT. The end-state matches a full ``replay``.

* ``compact_to_inserts(events)`` — like ``compact``, but rewrites the
  final UPDATE for each row to an INSERT carrying just the ``after``
  state. Useful when you're materialising a fresh sink table from a
  history of changes and don't want to deal with UPDATE semantics.

A *no-op DELETE* (DELETE for a row that never appeared) is dropped
silently; the compacted stream contains only events the downstream
sink can meaningfully apply.
"""

from __future__ import annotations

from cdc.schema import CDCEvent, Op


def compact(events: list[CDCEvent]) -> list[CDCEvent]:
    """Return the minimum event set per ``(table, pk)``.

    Output preserves the input ordering of the surviving events
    (after sorting by ``position``).
    """
    ordered = sorted(events, key=lambda e: (e.position.log_file, e.position.offset))
    # Walk forward keeping per-PK state; record what to emit.
    latest_per_key: dict[tuple[str, str], CDCEvent] = {}
    deleted: set[tuple[str, str]] = set()  # rows where we've seen a DELETE

    for event in ordered:
        key = (event.table, event.pk)
        if event.op is Op.DELETE:
            if key in latest_per_key:
                # The row had a CREATE/UPDATE before — collapse to the DELETE.
                latest_per_key[key] = event
                deleted.add(key)
            else:
                # DELETE for a row we never saw — drop entirely.
                continue
        else:
            # CREATE / READ / UPDATE — overwrite any prior state.
            latest_per_key[key] = event
            deleted.discard(key)  # re-creation after delete

    # Emit in position order.
    return sorted(
        latest_per_key.values(),
        key=lambda e: (e.position.log_file, e.position.offset),
    )


def compact_to_inserts(events: list[CDCEvent]) -> list[CDCEvent]:
    """Compact and rewrite every surviving UPDATE to an INSERT.

    DELETEs pass through unchanged. The output is safe to apply to a
    fresh target table that doesn't track UPDATE semantics.
    """
    compacted = compact(events)
    out: list[CDCEvent] = []
    for event in compacted:
        if event.op is Op.UPDATE:
            out.append(
                CDCEvent(
                    op=Op.CREATE,
                    table=event.table,
                    pk=event.pk,
                    ts_ms=event.ts_ms,
                    position=event.position,
                    after=dict(event.after),
                    db=event.db,
                )
            )
        else:
            out.append(event)
    return out


__all__ = ["compact", "compact_to_inserts"]
