"""Record validation."""

from __future__ import annotations

import pytest

from lsmmerge.schema import Record


def test_record_basic() -> None:
    r = Record(key="a", seq=1, value="x")
    assert r.key == "a"
    assert r.seq == 1
    assert r.value == "x"
    assert r.tombstone is False


def test_record_tombstone() -> None:
    r = Record(key="a", seq=2, tombstone=True)
    assert r.tombstone
    assert r.value == ""


def test_record_negative_seq_rejected() -> None:
    with pytest.raises(ValueError):
        Record(key="a", seq=-1)


def test_record_tombstone_with_value_rejected() -> None:
    with pytest.raises(ValueError):
        Record(key="a", seq=1, value="x", tombstone=True)


def test_record_frozen() -> None:
    r = Record(key="a", seq=1)
    with pytest.raises(Exception):
        r.key = "b"  # type: ignore[misc]


def test_record_hashable() -> None:
    s = {Record(key="a", seq=1), Record(key="a", seq=1)}
    assert len(s) == 1
