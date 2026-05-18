"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from scdkit.io_jsonl import (
    change_from_dict,
    dump_changes,
    dump_rows,
    load_changes,
    load_rows,
    row_from_dict,
    snapshot_from_text,
    snapshot_to_lines,
)
from scdkit.schema import HIGH_DATE

from ._fixtures import DEFAULT_TS, make_change, make_delete_change, make_row, make_update_change


def test_row_roundtrip_simple():
    r = make_row()
    [back] = list(load_rows(dump_rows([r])))
    assert back == r


def test_row_roundtrip_with_effective_dates():
    r = make_row(
        surrogate_key=42,
        effective_from=DEFAULT_TS,
        effective_to=HIGH_DATE,
        is_current=True,
    )
    [back] = list(load_rows(dump_rows([r])))
    assert back == r


def test_row_roundtrip_with_previous_attrs():
    r = make_row(previous_attributes={"shop_name": "Old"})
    [back] = list(load_rows(dump_rows([r])))
    assert back.previous_attributes["shop_name"] == "Old"


def test_change_insert_roundtrip():
    c = make_change()
    [back] = list(load_changes(dump_changes([c])))
    assert back == c


def test_change_update_roundtrip():
    c = make_update_change()
    [back] = list(load_changes(dump_changes([c])))
    assert back == c


def test_change_delete_roundtrip():
    c = make_delete_change()
    [back] = list(load_changes(dump_changes([c])))
    assert back == c


def test_snapshot_roundtrip():
    snap: dict[str, dict[str, str]] = {
        "S-1": {"shop_name": "A", "tier": "BASIC"},
        "S-2": {"shop_name": "B", "tier": "MALL"},
    }
    back = snapshot_from_text(snapshot_to_lines(snap))
    assert back == snap


def test_snapshot_sorted_emission():
    snap = {"S-Z": {"x": "z"}, "S-A": {"x": "a"}}
    text = snapshot_to_lines(snap)
    first_line = text.splitlines()[0]
    assert "S-A" in first_line


def test_blank_lines_skipped_snapshot():
    snap = {"S-1": {"x": "1"}}
    padded = "\n\n" + snapshot_to_lines(snap) + "\n\n"
    assert snapshot_from_text(padded) == snap


def test_row_decoder_rejects_wrong_string_field():
    bad = {
        "natural_key": 5,
        "attributes": {},
        "surrogate_key": None,
        "effective_from": None,
        "effective_to": None,
        "is_current": True,
        "previous_attributes": {},
    }
    with pytest.raises(TypeError, match="natural_key"):
        row_from_dict(bad)


def test_row_decoder_rejects_bool_for_int():
    bad = {
        "natural_key": "S",
        "attributes": {},
        "surrogate_key": True,  # bool, not int
        "effective_from": None,
        "effective_to": None,
        "is_current": True,
        "previous_attributes": {},
    }
    with pytest.raises(TypeError, match="surrogate_key"):
        row_from_dict(bad)


def test_change_decoder_rejects_unknown_kind():
    bad = {
        "natural_key": "S",
        "kind": "MUTATE",
        "detected_at": "2026-05-17T09:00:00+07:00",
        "before": None,
        "after": {"x": "y"},
        "changed_attrs": [],
    }
    with pytest.raises(ValueError):
        change_from_dict(bad)


def test_change_decoder_strips_non_string_attrs():
    """Non-string entries in changed_attrs are silently dropped."""
    payload = {
        "natural_key": "S",
        "kind": "UPDATE",
        "detected_at": "2026-05-17T09:00:00+07:00",
        "before": {"x": "1"},
        "after": {"x": "2"},
        "changed_attrs": ["x", 42, "y"],  # 42 dropped
    }
    c = change_from_dict(payload)
    assert c.changed_attrs == ("x", "y")


def test_multi_row_roundtrip():
    rows = [make_row(natural_key=f"S-{i:03d}") for i in range(5)]
    assert list(load_rows(dump_rows(rows))) == rows


def test_snapshot_rejects_non_string_attr_value():
    """Snapshot attribute values must be strings."""
    import json

    bad_line = json.dumps({"natural_key": "S", "attributes": {"x": 5}})
    with pytest.raises(TypeError):
        snapshot_from_text(bad_line)
