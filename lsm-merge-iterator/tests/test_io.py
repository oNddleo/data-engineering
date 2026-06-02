"""JSONL codec round-trip."""

from __future__ import annotations

import pytest

from lsmmerge.io_jsonl import (
    dump_records,
    load_records,
    record_from_dict,
    record_to_dict,
)
from lsmmerge.schema import Record


def test_record_roundtrip() -> None:
    r = Record(key="a", seq=5, value="hello")
    assert record_from_dict(record_to_dict(r)) == r


def test_tombstone_roundtrip() -> None:
    r = Record(key="a", seq=5, tombstone=True)
    assert record_from_dict(record_to_dict(r)) == r


def test_dump_load_roundtrip() -> None:
    rs = [
        Record(key="a", seq=1, value="A"),
        Record(key="b", seq=2, value="B"),
        Record(key="c", seq=3, tombstone=True),
    ]
    assert load_records(dump_records(rs)) == rs


def test_load_blank_lines_ignored() -> None:
    text = '{"key":"a","seq":1,"value":"A","tombstone":false}\n\n'
    rs = load_records(text)
    assert rs == [Record(key="a", seq=1, value="A")]


def test_load_rejects_non_object() -> None:
    with pytest.raises(TypeError):
        load_records("[1,2,3]\n")


def test_load_rejects_wrong_field_type() -> None:
    with pytest.raises(TypeError):
        load_records('{"key":"a","seq":"x"}\n')
