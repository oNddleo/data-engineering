"""JSONL round-trip tests."""

from __future__ import annotations

import pytest

from schemreg.io_jsonl import dump, entry_from_dict, entry_to_dict, load
from schemreg.registry import SchemaEntry


def _sample() -> SchemaEntry:
    return SchemaEntry(
        subject="orders",
        version=1,
        schema={"id": "int", "amount": "float"},
        created_at_ms=1_700_000_000_000,
    )


def test_roundtrip() -> None:
    e = _sample()
    assert entry_from_dict(entry_to_dict(e)) == e


def test_dump_load() -> None:
    entries = [_sample()]
    assert load(dump(entries)) == entries


def test_load_non_object_raises() -> None:
    with pytest.raises(TypeError):
        load("[1,2,3]\n")


def test_multiple_entries() -> None:
    e1 = _sample()
    e2 = SchemaEntry(subject="orders", version=2, schema={"id": "int"}, created_at_ms=2000)
    text = dump([e1, e2])
    loaded = load(text)
    assert len(loaded) == 2
    assert loaded[1].version == 2
