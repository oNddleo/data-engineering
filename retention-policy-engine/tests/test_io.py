"""JSONL round-trip tests."""

from __future__ import annotations

import pytest

from retention.io_jsonl import dump, load, record_from_dict, record_to_dict
from retention.schema import Record


def _sample() -> Record:
    return Record(
        key="rec-001",
        created_at_ms=1_700_000_000_000,
        size_bytes=4096,
        tags=frozenset({"hot", "raw"}),
    )


def test_roundtrip() -> None:
    r = _sample()
    assert record_from_dict(record_to_dict(r)) == r


def test_dump_load() -> None:
    records = [_sample()]
    assert load(dump(records)) == records


def test_load_non_object_raises() -> None:
    with pytest.raises(TypeError):
        load("[1,2,3]\n")


def test_tags_empty() -> None:
    r = Record(key="k", created_at_ms=0, size_bytes=0)
    d = record_to_dict(r)
    assert d["tags"] == []
    r2 = record_from_dict(d)
    assert r2.tags == frozenset()
