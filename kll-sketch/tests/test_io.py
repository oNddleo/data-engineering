"""JSONL round-trip tests."""

from __future__ import annotations

import pytest

from kllsketch.io_jsonl import dump, load, sketch_from_dict, sketch_to_dict
from kllsketch.sketch import KLLSketch


def _sketch() -> KLLSketch:
    s = KLLSketch(k=50)
    for i in range(500):
        s.update(float(i))
    return s


def test_roundtrip() -> None:
    s = _sketch()
    s2 = sketch_from_dict(sketch_to_dict(s))
    assert s2.n == s.n
    assert abs(s2.quantile(0.5) - s.quantile(0.5)) < 1.0


def test_dump_load() -> None:
    s = _sketch()
    text = dump([s])
    loaded = load(text)
    assert len(loaded) == 1
    assert loaded[0].n == s.n


def test_load_non_object_raises() -> None:
    with pytest.raises(TypeError):
        load("[1,2,3]\n")
