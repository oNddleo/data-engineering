"""Hypothesis property tests for CDC invariants."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from cdc.compact import compact
from cdc.diff import change_vector
from cdc.io_jsonl import (
    event_from_dict,
    event_to_dict,
    lineage_from_dict,
    lineage_to_dict,
)
from cdc.lineage import build_lineage
from cdc.replay import replay, replay_unordered
from cdc.schema import CDCEvent, EventPosition, Op, RowState

_table_strategy = st.sampled_from(["users", "orders", "items"])
_pk_strategy = st.text(min_size=1, max_size=8, alphabet="0123456789ABC")

_value_strategy: st.SearchStrategy[str | int | float | bool | None] = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(min_value=-1_000_000, max_value=1_000_000),
    st.floats(allow_nan=False, allow_infinity=False, min_value=-1e6, max_value=1e6),
    st.text(min_size=0, max_size=20),
)


@st.composite
def row_state(draw: st.DrawFn, min_keys: int = 1) -> RowState:
    n = draw(st.integers(min_value=min_keys, max_value=5))
    keys = [f"col_{i}" for i in range(n)]
    values = [draw(_value_strategy) for _ in range(n)]
    return dict(zip(keys, values, strict=True))


@st.composite
def insert_event(draw: st.DrawFn) -> CDCEvent:
    return CDCEvent(
        op=Op.CREATE,
        table=draw(_table_strategy),
        pk=draw(_pk_strategy),
        ts_ms=draw(st.integers(min_value=0, max_value=10**12)),
        position=EventPosition(
            log_file=draw(st.sampled_from(["binlog.000001", "binlog.000002"])),
            offset=draw(st.integers(min_value=0, max_value=1_000_000)),
        ),
        after=draw(row_state()),
    )


# ---------- INSERT event invariants ----------------------------------------


@given(insert_event())
@settings(max_examples=80)
def test_insert_op_invariants(e: CDCEvent) -> None:
    assert e.before == {}
    assert e.after
    assert e.op is Op.CREATE


# ---------- JSONL round-trip ----------------------------------------------


@given(insert_event())
@settings(max_examples=60)
def test_event_jsonl_roundtrip(e: CDCEvent) -> None:
    assert event_from_dict(event_to_dict(e)) == e


# ---------- Replay invariants ---------------------------------------------


@given(st.lists(insert_event(), min_size=1, max_size=20))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_replay_unordered_handles_any_order(events: list[CDCEvent]) -> None:
    """Same set of INSERTs in any order materialises the same snapshot."""
    # Deduplicate by (table, pk) and (log_file, offset).
    seen_keys: set[tuple[str, str]] = set()
    seen_positions: set[tuple[str, int]] = set()
    unique: list[CDCEvent] = []
    for e in events:
        key = (e.table, e.pk)
        pos_key = (e.position.log_file, e.position.offset)
        if key in seen_keys or pos_key in seen_positions:
            continue
        seen_keys.add(key)
        seen_positions.add(pos_key)
        unique.append(e)
    snap1 = replay_unordered(unique, strict=False)
    snap2 = replay_unordered(list(reversed(unique)), strict=False)
    assert snap1 == snap2


# ---------- Compaction invariants -----------------------------------------


@given(st.lists(insert_event(), min_size=1, max_size=20))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_compact_idempotent(events: list[CDCEvent]) -> None:
    """compact(compact(x)) == compact(x)."""
    seen: set[tuple[str, str]] = set()
    seen_pos: set[tuple[str, int]] = set()
    unique: list[CDCEvent] = []
    for e in events:
        key = (e.table, e.pk)
        pkey = (e.position.log_file, e.position.offset)
        if key in seen or pkey in seen_pos:
            continue
        seen.add(key)
        seen_pos.add(pkey)
        unique.append(e)
    once = compact(unique)
    twice = compact(once)
    assert once == twice


@given(st.lists(insert_event(), min_size=1, max_size=20))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=30)
def test_compact_replay_equivalent(events: list[CDCEvent]) -> None:
    """Replaying the compacted stream gives the same state as the full stream."""
    # Deduplicate.
    seen_pos: set[tuple[str, int]] = set()
    seen_keys: set[tuple[str, str]] = set()
    unique: list[CDCEvent] = []
    for e in events:
        pkey = (e.position.log_file, e.position.offset)
        kkey = (e.table, e.pk)
        if pkey in seen_pos or kkey in seen_keys:
            continue
        seen_pos.add(pkey)
        seen_keys.add(kkey)
        unique.append(e)
    full = replay(unique, strict=False)
    compacted = replay(compact(unique), strict=False)
    assert full == compacted


# ---------- Lineage invariants --------------------------------------------


@given(st.lists(insert_event(), min_size=1, max_size=20))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=20)
def test_lineage_one_per_row(events: list[CDCEvent]) -> None:
    """Lineage output has exactly one row per unique (table, pk) creation."""
    seen: set[tuple[str, str]] = set()
    seen_pos: set[tuple[str, int]] = set()
    unique: list[CDCEvent] = []
    for e in events:
        kkey = (e.table, e.pk)
        pkey = (e.position.log_file, e.position.offset)
        if kkey in seen or pkey in seen_pos:
            continue
        seen.add(kkey)
        seen_pos.add(pkey)
        unique.append(e)
    rows = build_lineage(unique)
    distinct_keys = {(r.table, r.pk) for r in rows}
    assert len(distinct_keys) == len(rows)
    assert len(distinct_keys) == len(unique)


@given(insert_event())
@settings(max_examples=30)
def test_lineage_single_insert_no_updates(e: CDCEvent) -> None:
    rows = build_lineage([e])
    assert rows[0].n_updates == 0
    assert rows[0].is_deleted is False
    assert rows[0].created_at_ms == e.ts_ms


# ---------- Diff: changed columns are subset of column set ----------------


@given(insert_event())
@settings(max_examples=30)
def test_change_vector_columns_subset(insert: CDCEvent) -> None:
    """An UPDATE that mutates one column reports exactly that column."""
    # Manufacture an UPDATE from the insert.
    if not insert.after:
        return
    col = next(iter(insert.after.keys()))
    # Toggle the value (sentinel that's unequal to any plausible original).
    new_value: str | int | float | bool | None = "MUTATED_SENTINEL_VALUE_XYZ"
    if insert.after[col] == "MUTATED_SENTINEL_VALUE_XYZ":
        new_value = "DIFFERENT_SENTINEL_ABC"
    update = CDCEvent(
        op=Op.UPDATE,
        table=insert.table,
        pk=insert.pk,
        ts_ms=insert.ts_ms + 1,
        position=EventPosition(
            log_file=insert.position.log_file,
            offset=insert.position.offset + 1,
        ),
        before=dict(insert.after),
        after={**insert.after, col: new_value},
    )
    cv = change_vector(update)
    assert cv.changed_columns == (col,)


# ---------- Lineage JSONL round-trip --------------------------------------


@given(st.lists(insert_event(), min_size=1, max_size=10))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=20)
def test_lineage_jsonl_roundtrip(events: list[CDCEvent]) -> None:
    rows = build_lineage(events)
    for r in rows:
        assert lineage_from_dict(lineage_to_dict(r)) == r
