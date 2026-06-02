"""JSONL round-trip tests for CountMinSketch."""

from __future__ import annotations

from cmsketch.io_jsonl import dump, load
from cmsketch.sketch import CountMinSketch


def _make_sketch(
    items: list[str], width: int = 256, depth: int = 4, seed: int = 0
) -> CountMinSketch:
    s = CountMinSketch(width=width, depth=depth, seed=seed)
    for item in items:
        s.update(item)
    return s


def test_dump_load_roundtrip() -> None:
    s = _make_sketch(["a", "b", "a", "c", "a"], width=64, depth=3, seed=7)
    text = dump([s])
    loaded = load(text)
    assert len(loaded) == 1
    r = loaded[0]
    assert r.n == s.n
    assert r.width == s.width
    assert r.depth == s.depth
    # Queries should match exactly (same internal state restored)
    assert r.query("a") == s.query("a")
    assert r.query("b") == s.query("b")


def test_dump_load_multiple() -> None:
    s1 = _make_sketch(["x"] * 10, seed=0)
    s2 = _make_sketch(["y"] * 20, seed=0)
    text = dump([s1, s2])
    loaded = load(text)
    assert len(loaded) == 2
    assert loaded[0].n == 10
    assert loaded[1].n == 20


def test_empty_text_returns_empty_list() -> None:
    assert load("") == []
    assert load("   \n  ") == []


def test_dump_empty_list() -> None:
    assert dump([]) == ""


def test_load_preserves_query_accuracy() -> None:
    s = CountMinSketch(width=512, depth=5, seed=3)
    for i in range(1000):
        s.update(f"item_{i % 50}")
    text = dump([s])
    r = load(text)[0]
    for i in range(50):
        item = f"item_{i}"
        assert r.query(item) == s.query(item)
