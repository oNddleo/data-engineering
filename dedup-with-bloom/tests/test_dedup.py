"""dedup_stream / dedup_iter behaviour."""

from __future__ import annotations

from bloomdedup.dedup import dedup_iter, dedup_stream


def test_dedup_stream_basic() -> None:
    keys = ["a", "b", "a", "c", "b", "d"]
    kept, stats = dedup_stream(keys, capacity=100, fpr=0.001)
    assert kept == ["a", "b", "c", "d"]
    assert stats.seen == 6
    assert stats.kept == 4
    assert stats.suppressed == 2


def test_dedup_stream_no_duplicates() -> None:
    keys = [f"k{i}" for i in range(50)]
    kept, stats = dedup_stream(keys, capacity=1000, fpr=0.001)
    assert kept == keys
    assert stats.suppressed == 0


def test_dedup_stream_all_duplicates() -> None:
    keys = ["a"] * 100
    kept, stats = dedup_stream(keys, capacity=100, fpr=0.001)
    assert kept == ["a"]
    assert stats.suppressed == 99


def test_dedup_stream_empty() -> None:
    kept, stats = dedup_stream([], capacity=100, fpr=0.001)
    assert kept == []
    assert stats.seen == 0
    assert stats.suppression_rate == 0.0


def test_dedup_iter_streams_lazily() -> None:
    keys = ["a", "b", "a", "c"]
    out = list(dedup_iter(keys, capacity=100, fpr=0.001))
    assert out == ["a", "b", "c"]


def test_dedup_stream_preserves_first_sighting_order() -> None:
    keys = ["zebra", "ant", "zebra", "bee", "ant"]
    kept, _ = dedup_stream(keys, capacity=100, fpr=0.001)
    assert kept == ["zebra", "ant", "bee"]


def test_suppression_rate() -> None:
    keys = ["a", "a", "a", "b"]
    _, stats = dedup_stream(keys, capacity=10, fpr=0.001)
    assert stats.suppression_rate == 0.5
