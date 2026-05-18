"""Compute the list of ``FieldChange``s between two schemas.

Implements alias-aware matching: a field with `aliases=("old_name",)`
in the new schema is matched to a field literally named `old_name`
in the old schema (i.e. it's a rename, not a removal + addition).

The diff is a pure function — no I/O, no side effects. Output is
sorted by ``(kind, field_name)`` for stable diffs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from schemaev.schema import FieldChange

if TYPE_CHECKING:
    from schemaev.schema import Schema


def _match_pairs(
    old: Schema, new: Schema
) -> tuple[
    dict[str, tuple[str | None, str | None]],
    set[str],
    set[str],
]:
    """Return ``(pairs, old_unmatched, new_unmatched)`` where ``pairs``
    maps canonical name → (old_field_name, new_field_name).

    Alias matching: if a new field has an alias that names an old field,
    we treat them as the same field (rename).
    """
    old_by_name = {f.name: f for f in old.fields}
    new_by_name = {f.name: f for f in new.fields}

    pairs: dict[str, tuple[str | None, str | None]] = {}
    matched_old: set[str] = set()
    matched_new: set[str] = set()

    # 1. Exact-name matches first.
    for name in old_by_name.keys() & new_by_name.keys():
        pairs[name] = (name, name)
        matched_old.add(name)
        matched_new.add(name)

    # 2. Alias-based matches (new field's alias names an old field).
    for new_name, new_field in new_by_name.items():
        if new_name in matched_new:
            continue
        for alias in new_field.aliases:
            if alias in old_by_name and alias not in matched_old:
                pairs[new_name] = (alias, new_name)
                matched_old.add(alias)
                matched_new.add(new_name)
                break

    unmatched_old = set(old_by_name) - matched_old
    unmatched_new = set(new_by_name) - matched_new
    return pairs, unmatched_old, unmatched_new


def diff(old: Schema, new: Schema) -> list[FieldChange]:
    """Compute the diff old → new as a list of FieldChanges."""
    old_by_name = {f.name: f for f in old.fields}
    new_by_name = {f.name: f for f in new.fields}

    pairs, unmatched_old, unmatched_new = _match_pairs(old, new)
    out: list[FieldChange] = []

    # Matched pairs — check for changes.
    for new_name, (old_name, _) in pairs.items():
        assert old_name is not None
        old_f = old_by_name[old_name]
        new_f = new_by_name[new_name]
        if old_f.type != new_f.type:
            out.append(
                FieldChange(
                    kind="TYPE_CHANGED",
                    field_name=new_name,
                    old=old_f,
                    new=new_f,
                    detail=f"{old_f.type.value} → {new_f.type.value}",
                )
            )
        if old_f.required != new_f.required:
            out.append(
                FieldChange(
                    kind="REQUIRED_CHANGED",
                    field_name=new_name,
                    old=old_f,
                    new=new_f,
                    detail=f"required {old_f.required} → {new_f.required}",
                )
            )
        if old_f.default != new_f.default:
            out.append(
                FieldChange(
                    kind="DEFAULT_CHANGED",
                    field_name=new_name,
                    old=old_f,
                    new=new_f,
                    detail=f"default {old_f.default!r} → {new_f.default!r}",
                )
            )
        added_aliases = set(new_f.aliases) - set(old_f.aliases)
        if added_aliases:
            out.append(
                FieldChange(
                    kind="ALIAS_ADDED",
                    field_name=new_name,
                    old=old_f,
                    new=new_f,
                    detail=f"aliases added: {sorted(added_aliases)}",
                )
            )

    # Unmatched old → REMOVED.
    for name in unmatched_old:
        out.append(
            FieldChange(
                kind="REMOVED",
                field_name=name,
                old=old_by_name[name],
                new=None,
                detail=f"field {name!r} removed",
            )
        )

    # Unmatched new → ADDED.
    for name in unmatched_new:
        out.append(
            FieldChange(
                kind="ADDED",
                field_name=name,
                old=None,
                new=new_by_name[name],
                detail=f"field {name!r} added",
            )
        )

    out.sort(key=lambda c: (c.kind, c.field_name))
    return out


__all__ = ["diff"]
