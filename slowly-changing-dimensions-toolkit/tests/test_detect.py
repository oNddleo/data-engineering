"""Snapshot diff → DimensionChange events."""

from __future__ import annotations

from datetime import datetime

import pytest

from scdkit.detect import detect, n_changes_by_kind
from scdkit.schema import ChangeKind

from ._fixtures import DEFAULT_TS


def test_detect_validates_as_of_tz():
    with pytest.raises(ValueError):
        detect({}, {}, as_of=datetime(2026, 5, 17))


def test_pure_insert():
    before: dict[str, dict[str, str]] = {}
    after = {"S-1": {"name": "New Shop", "tier": "STANDARD"}}
    [change] = detect(before, after, as_of=DEFAULT_TS)
    assert change.kind is ChangeKind.INSERT
    assert change.natural_key == "S-1"
    assert change.before is None
    assert change.after == {"name": "New Shop", "tier": "STANDARD"}


def test_pure_delete():
    before = {"S-1": {"name": "Gone Shop"}}
    after: dict[str, dict[str, str]] = {}
    [change] = detect(before, after, as_of=DEFAULT_TS)
    assert change.kind is ChangeKind.DELETE
    assert change.before == {"name": "Gone Shop"}
    assert change.after is None


def test_update_lists_changed_attrs():
    before = {"S-1": {"name": "Old", "tier": "STANDARD"}}
    after = {"S-1": {"name": "New", "tier": "STANDARD"}}
    [change] = detect(before, after, as_of=DEFAULT_TS)
    assert change.kind is ChangeKind.UPDATE
    assert change.changed_attrs == ("name",)


def test_update_multiple_attrs_sorted():
    before = {"S-1": {"name": "Old", "tier": "BASIC"}}
    after = {"S-1": {"name": "New", "tier": "MALL"}}
    [change] = detect(before, after, as_of=DEFAULT_TS)
    assert change.changed_attrs == ("name", "tier")


def test_no_change_silent_skip():
    before = {"S-1": {"name": "Same"}}
    after = {"S-1": {"name": "Same"}}
    assert detect(before, after, as_of=DEFAULT_TS) == []


def test_tracked_attrs_filters_emissions():
    """Change to non-tracked attr → no UPDATE event."""
    before = {"S-1": {"name": "Same", "last_load_ts": "1"}}
    after = {"S-1": {"name": "Same", "last_load_ts": "2"}}
    assert detect(before, after, as_of=DEFAULT_TS, tracked_attrs=["name"]) == []


def test_tracked_attrs_includes_only_tracked_changes():
    before = {"S-1": {"name": "Old", "address": "A"}}
    after = {"S-1": {"name": "New", "address": "B"}}
    [change] = detect(before, after, as_of=DEFAULT_TS, tracked_attrs=["name"])
    assert change.changed_attrs == ("name",)


def test_output_sorted_by_kind_then_key():
    before = {"S-2": {"x": "1"}, "S-3": {"x": "1"}}
    after = {"S-1": {"x": "new"}, "S-2": {"x": "1"}, "S-3": {"x": "2"}}
    changes = detect(before, after, as_of=DEFAULT_TS)
    kinds_keys = [(c.kind.value, c.natural_key) for c in changes]
    assert kinds_keys == sorted(kinds_keys)


def test_mixed_batch():
    before = {"S-1": {"name": "Old"}, "S-2": {"name": "ToDelete"}}
    after = {"S-1": {"name": "New"}, "S-3": {"name": "Brand New"}}
    changes = detect(before, after, as_of=DEFAULT_TS)
    counts = n_changes_by_kind(changes)
    assert counts[ChangeKind.INSERT] == 1
    assert counts[ChangeKind.UPDATE] == 1
    assert counts[ChangeKind.DELETE] == 1


def test_n_changes_by_kind_zero_fills():
    counts = n_changes_by_kind([])
    assert counts == {ChangeKind.INSERT: 0, ChangeKind.UPDATE: 0, ChangeKind.DELETE: 0}


def test_added_attribute_counts_as_change():
    """An attribute present in `after` but missing from `before` is a change."""
    before = {"S-1": {"name": "Same"}}
    after = {"S-1": {"name": "Same", "tier": "MALL"}}
    [change] = detect(before, after, as_of=DEFAULT_TS)
    assert change.kind is ChangeKind.UPDATE
    assert "tier" in change.changed_attrs


def test_removed_attribute_counts_as_change():
    """An attribute removed from `after` is also a change."""
    before = {"S-1": {"name": "Same", "tier": "MALL"}}
    after = {"S-1": {"name": "Same"}}
    [change] = detect(before, after, as_of=DEFAULT_TS)
    assert change.kind is ChangeKind.UPDATE
    assert "tier" in change.changed_attrs
