"""The five SCD-type appliers — each takes a starting state + a list
of changes and returns the new state.

Every applier is a **pure function** — no in-place mutation of the
input, no global state. The outputs are sorted deterministically so
diffs are stable.

Type-2 / Type-4 / Type-6 all assign monotonically-increasing
``surrogate_key`` values. The initial value is supplied by the
caller so multiple batches can be chained.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from scdkit.schema import HIGH_DATE, ChangeKind, DimensionRow

if TYPE_CHECKING:
    from scdkit.schema import DimensionChange


# ---------- TYPE 1: overwrite ----------------------------------------------


def apply_type_1(
    current: dict[str, DimensionRow],
    changes: list[DimensionChange],
) -> dict[str, DimensionRow]:
    """Overwrite — no history.

    INSERT adds a row, UPDATE overwrites attributes in place, DELETE
    removes the row. Reports always show the latest state with zero
    historical context.
    """
    out = {k: v for k, v in current.items()}
    for ch in changes:
        if ch.kind is ChangeKind.INSERT:
            assert ch.after is not None
            out[ch.natural_key] = DimensionRow(
                natural_key=ch.natural_key,
                attributes=dict(ch.after),
            )
        elif ch.kind is ChangeKind.UPDATE:
            assert ch.after is not None
            existing = out.get(ch.natural_key)
            out[ch.natural_key] = DimensionRow(
                natural_key=ch.natural_key,
                attributes=dict(ch.after),
                surrogate_key=existing.surrogate_key if existing else None,
            )
        elif ch.kind is ChangeKind.DELETE:
            out.pop(ch.natural_key, None)
    return out


# ---------- TYPE 2: new row per change -------------------------------------


@dataclass(frozen=True, slots=True)
class Type2State:
    """All Type-2 rows seen so far, keyed by surrogate_key.

    Also caches the **current** (open-ended) row per natural_key for
    O(1) close-out on the next update.
    """

    rows: dict[int, DimensionRow]
    current_by_natural: dict[str, int]  # natural_key → surrogate_key
    next_surrogate: int


def type_2_empty(start_surrogate: int = 1) -> Type2State:
    """Fresh empty state. ``start_surrogate`` lets you chain batches."""
    return Type2State(rows={}, current_by_natural={}, next_surrogate=start_surrogate)


def apply_type_2(
    state: Type2State,
    changes: list[DimensionChange],
) -> Type2State:
    """Append a new row per UPDATE/INSERT; close out the prior current row.

    DELETE closes the current row (``effective_to = detected_at``,
    ``is_current = False``) but does **not** insert a new tombstone.
    """
    rows = dict(state.rows)
    current_by_natural = dict(state.current_by_natural)
    next_surrogate = state.next_surrogate

    for ch in changes:
        if ch.kind is ChangeKind.INSERT:
            assert ch.after is not None
            sk = next_surrogate
            rows[sk] = DimensionRow(
                natural_key=ch.natural_key,
                attributes=dict(ch.after),
                surrogate_key=sk,
                effective_from=ch.detected_at,
                effective_to=HIGH_DATE,
                is_current=True,
            )
            current_by_natural[ch.natural_key] = sk
            next_surrogate += 1
        elif ch.kind is ChangeKind.UPDATE:
            assert ch.after is not None
            # Close the prior current row.
            prior_sk = current_by_natural.get(ch.natural_key)
            if prior_sk is not None:
                prior = rows[prior_sk]
                rows[prior_sk] = replace(prior, effective_to=ch.detected_at, is_current=False)
            # Open a new row.
            sk = next_surrogate
            rows[sk] = DimensionRow(
                natural_key=ch.natural_key,
                attributes=dict(ch.after),
                surrogate_key=sk,
                effective_from=ch.detected_at,
                effective_to=HIGH_DATE,
                is_current=True,
            )
            current_by_natural[ch.natural_key] = sk
            next_surrogate += 1
        elif ch.kind is ChangeKind.DELETE:
            prior_sk = current_by_natural.pop(ch.natural_key, None)
            if prior_sk is not None:
                prior = rows[prior_sk]
                rows[prior_sk] = replace(prior, effective_to=ch.detected_at, is_current=False)

    return Type2State(
        rows=rows,
        current_by_natural=current_by_natural,
        next_surrogate=next_surrogate,
    )


def type_2_current(state: Type2State) -> dict[str, DimensionRow]:
    """``{natural_key: current_row}`` view."""
    return {nk: state.rows[sk] for nk, sk in state.current_by_natural.items()}


def type_2_history_for(state: Type2State, natural_key: str) -> list[DimensionRow]:
    """All historical versions of one entity, sorted by ``effective_from``."""
    rows = [r for r in state.rows.values() if r.natural_key == natural_key]
    rows.sort(key=lambda r: r.effective_from or HIGH_DATE)
    return rows


# ---------- TYPE 3: previous-value column ----------------------------------


def apply_type_3(
    current: dict[str, DimensionRow],
    changes: list[DimensionChange],
    tracked_attrs: list[str],
) -> dict[str, DimensionRow]:
    """Track the *previous* value of each tracked attribute on the same row.

    On UPDATE, the new value goes into ``attributes`` and the old value
    is stashed in ``previous_attributes`` (overwriting any prior
    previous — Type 3 keeps **one** prior version, no more).
    """
    out = {k: v for k, v in current.items()}
    for ch in changes:
        if ch.kind is ChangeKind.INSERT:
            assert ch.after is not None
            out[ch.natural_key] = DimensionRow(
                natural_key=ch.natural_key,
                attributes=dict(ch.after),
            )
        elif ch.kind is ChangeKind.UPDATE:
            assert ch.before is not None
            assert ch.after is not None
            prev = {a: ch.before.get(a, "") for a in tracked_attrs}
            out[ch.natural_key] = DimensionRow(
                natural_key=ch.natural_key,
                attributes=dict(ch.after),
                previous_attributes=prev,
            )
        elif ch.kind is ChangeKind.DELETE:
            out.pop(ch.natural_key, None)
    return out


# ---------- TYPE 4: separate history table ---------------------------------


@dataclass(frozen=True, slots=True)
class Type4State:
    """Current rows in the main table + every change recorded in history."""

    current: dict[str, DimensionRow]  # main table: one row per natural_key
    history: list[DimensionRow]  # one row per past version


def type_4_empty() -> Type4State:
    return Type4State(current={}, history=[])


def apply_type_4(
    state: Type4State,
    changes: list[DimensionChange],
) -> Type4State:
    """Update main table in place + append every prior version to history."""
    current = {k: v for k, v in state.current.items()}
    history = list(state.history)
    for ch in changes:
        if ch.kind is ChangeKind.INSERT:
            assert ch.after is not None
            current[ch.natural_key] = DimensionRow(
                natural_key=ch.natural_key,
                attributes=dict(ch.after),
                effective_from=ch.detected_at,
            )
        elif ch.kind is ChangeKind.UPDATE:
            assert ch.after is not None
            # Archive the prior version with its end timestamp.
            prior = current.get(ch.natural_key)
            if prior is not None:
                history.append(replace(prior, effective_to=ch.detected_at, is_current=False))
            current[ch.natural_key] = DimensionRow(
                natural_key=ch.natural_key,
                attributes=dict(ch.after),
                effective_from=ch.detected_at,
            )
        elif ch.kind is ChangeKind.DELETE:
            prior = current.pop(ch.natural_key, None)
            if prior is not None:
                history.append(replace(prior, effective_to=ch.detected_at, is_current=False))
    return Type4State(current=current, history=history)


# ---------- TYPE 6: hybrid (1 + 2 + 3) -------------------------------------


@dataclass(frozen=True, slots=True)
class Type6State:
    """Hybrid state.

    ``current`` is the Type-1 view (one row per natural_key, latest
    attributes plus a Type-3 ``previous_attributes`` map). ``history``
    is the Type-2 row set (every version, with effective dates +
    is_current). ``next_surrogate`` is shared with the Type-2 layer.
    """

    current: dict[str, DimensionRow]
    history: dict[int, DimensionRow]
    current_by_natural: dict[str, int]
    next_surrogate: int


def type_6_empty(start_surrogate: int = 1) -> Type6State:
    return Type6State(
        current={},
        history={},
        current_by_natural={},
        next_surrogate=start_surrogate,
    )


def apply_type_6(
    state: Type6State,
    changes: list[DimensionChange],
    tracked_attrs: list[str],
) -> Type6State:
    """Maintain all three views simultaneously."""
    current = {k: v for k, v in state.current.items()}
    history = dict(state.history)
    current_by_natural = dict(state.current_by_natural)
    next_surrogate = state.next_surrogate

    for ch in changes:
        if ch.kind is ChangeKind.INSERT:
            assert ch.after is not None
            sk = next_surrogate
            history[sk] = DimensionRow(
                natural_key=ch.natural_key,
                attributes=dict(ch.after),
                surrogate_key=sk,
                effective_from=ch.detected_at,
                effective_to=HIGH_DATE,
                is_current=True,
            )
            current[ch.natural_key] = DimensionRow(
                natural_key=ch.natural_key,
                attributes=dict(ch.after),
                surrogate_key=sk,
            )
            current_by_natural[ch.natural_key] = sk
            next_surrogate += 1
        elif ch.kind is ChangeKind.UPDATE:
            assert ch.before is not None
            assert ch.after is not None
            # Close the prior Type-2 row.
            prior_sk = current_by_natural.get(ch.natural_key)
            if prior_sk is not None:
                prior = history[prior_sk]
                history[prior_sk] = replace(prior, effective_to=ch.detected_at, is_current=False)
            # Open a new Type-2 row.
            sk = next_surrogate
            history[sk] = DimensionRow(
                natural_key=ch.natural_key,
                attributes=dict(ch.after),
                surrogate_key=sk,
                effective_from=ch.detected_at,
                effective_to=HIGH_DATE,
                is_current=True,
            )
            # Update Type-1 current row + Type-3 previous attrs.
            prev = {a: ch.before.get(a, "") for a in tracked_attrs}
            current[ch.natural_key] = DimensionRow(
                natural_key=ch.natural_key,
                attributes=dict(ch.after),
                surrogate_key=sk,
                previous_attributes=prev,
            )
            current_by_natural[ch.natural_key] = sk
            next_surrogate += 1
        elif ch.kind is ChangeKind.DELETE:
            prior_sk = current_by_natural.pop(ch.natural_key, None)
            if prior_sk is not None:
                prior = history[prior_sk]
                history[prior_sk] = replace(prior, effective_to=ch.detected_at, is_current=False)
            current.pop(ch.natural_key, None)

    return Type6State(
        current=current,
        history=history,
        current_by_natural=current_by_natural,
        next_surrogate=next_surrogate,
    )


__all__ = [
    "Type2State",
    "Type4State",
    "Type6State",
    "apply_type_1",
    "apply_type_2",
    "apply_type_3",
    "apply_type_4",
    "apply_type_6",
    "type_2_current",
    "type_2_empty",
    "type_2_history_for",
    "type_4_empty",
    "type_6_empty",
]
