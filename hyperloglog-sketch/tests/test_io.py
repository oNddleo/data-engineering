"""JSONL round-trip tests for HyperLogLog."""

from __future__ import annotations

from hllsketch.io_jsonl import dump, load
from hllsketch.sketch import HyperLogLog


def _make_hll(n: int, precision: int = 12) -> HyperLogLog:
    h = HyperLogLog(precision=precision)
    for i in range(n):
        h.add(f"item_{i}")
    return h


def test_roundtrip_single() -> None:
    h = _make_hll(1000)
    text = dump([h])
    loaded = load(text)
    assert len(loaded) == 1
    r = loaded[0]
    assert r.precision == h.precision
    assert r.num_registers == h.num_registers
    assert r.count() == h.count()


def test_roundtrip_multiple() -> None:
    h1 = _make_hll(500, precision=10)
    h2 = _make_hll(2000, precision=10)
    text = dump([h1, h2])
    loaded = load(text)
    assert len(loaded) == 2
    assert loaded[0].count() == h1.count()
    assert loaded[1].count() == h2.count()


def test_empty_text() -> None:
    assert load("") == []
    assert load("\n\n") == []


def test_dump_empty_list() -> None:
    assert dump([]) == ""


def test_roundtrip_preserves_registers() -> None:
    h = _make_hll(500, precision=10)
    text = dump([h])
    r = load(text)[0]
    assert r._registers == h._registers
