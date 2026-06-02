"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from partitioner.io_jsonl import (
    dump_assignments,
    dump_keys,
    load_assignments,
    load_keys,
)


def test_assignment_roundtrip() -> None:
    pairs = [("a", 0), ("b", 1), ("c", 2)]
    assert load_assignments(dump_assignments(pairs)) == pairs


def test_keys_roundtrip() -> None:
    keys = ["a", "b", "c"]
    assert load_keys(dump_keys(keys)) == keys


def test_load_rejects_non_object() -> None:
    with pytest.raises(TypeError):
        load_keys("[1,2,3]\n")
