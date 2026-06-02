"""Algorithm R, Algorithm L, and weighted A-Res."""

from __future__ import annotations

import random
from collections import Counter

import pytest

from reservoir.algorithms import (
    add_r,
    add_weighted,
    build_r,
    build_weighted,
    freeze,
    sample_l,
    sample_r,
    sample_weighted,
    thaw,
)

# ---------- Algorithm R basics ---------------------------------------------


def test_r_fills_up_to_capacity() -> None:
    res = sample_r(["a", "b", "c"], capacity=5)
    assert sorted(res.items) == ["a", "b", "c"]
    assert res.n_seen == 3


def test_r_capacity_exactly() -> None:
    res = sample_r(["a", "b", "c"], capacity=3)
    assert sorted(res.items) == ["a", "b", "c"]


def test_r_oversized_stream() -> None:
    """Algorithm R reduces 100 items to a reservoir of size 10."""
    stream = [f"v-{i}" for i in range(100)]
    res = sample_r(stream, capacity=10, rng=random.Random(0))
    assert res.n_kept == 10
    assert res.n_seen == 100


def test_r_empty_stream() -> None:
    res = sample_r([], capacity=5)
    assert res.n_kept == 0
    assert res.n_seen == 0


def test_r_rejects_zero_capacity() -> None:
    with pytest.raises(ValueError, match="capacity"):
        build_r(0)


def test_r_uniformity() -> None:
    """Across many trials each item should be picked ~k/N of the time."""
    n, k = 100, 20
    trials = 2_000
    counts: Counter[str] = Counter()
    for t in range(trials):
        stream = [f"v-{i}" for i in range(n)]
        res = sample_r(stream, capacity=k, rng=random.Random(t))
        counts.update(res.items)
    expected = trials * k / n
    # Every item should be within 3σ ≈ 3·sqrt(expected(1-k/n)) of expectation.
    sigma = (expected * (1 - k / n)) ** 0.5
    for v in (f"v-{i}" for i in range(n)):
        assert (
            abs(counts[v] - expected) < 5 * sigma
        ), f"item {v} count {counts[v]} not within 5σ of {expected:.1f}"


def test_r_deterministic_with_seed() -> None:
    stream = [f"v-{i}" for i in range(100)]
    a = sample_r(stream, capacity=10, rng=random.Random(42))
    b = sample_r(stream, capacity=10, rng=random.Random(42))
    assert a.items == b.items


# ---------- Algorithm L basics ---------------------------------------------


def test_l_fills_up_to_capacity() -> None:
    res = sample_l(["a", "b", "c"], capacity=5, rng=random.Random(0))
    assert sorted(res.items) == ["a", "b", "c"]


def test_l_capacity_exactly() -> None:
    res = sample_l(["a", "b", "c"], capacity=3, rng=random.Random(0))
    assert sorted(res.items) == ["a", "b", "c"]


def test_l_oversized_stream() -> None:
    stream = [f"v-{i}" for i in range(100)]
    res = sample_l(stream, capacity=10, rng=random.Random(0))
    assert res.n_kept == 10
    assert res.n_seen == 100


def test_l_deterministic_with_seed() -> None:
    stream = [f"v-{i}" for i in range(100)]
    a = sample_l(stream, capacity=10, rng=random.Random(42))
    b = sample_l(stream, capacity=10, rng=random.Random(42))
    assert a.items == b.items


def test_l_uniformity() -> None:
    """Algorithm L should match Algorithm R's uniformity guarantee."""
    n, k = 100, 20
    trials = 2_000
    counts: Counter[str] = Counter()
    for t in range(trials):
        stream = [f"v-{i}" for i in range(n)]
        res = sample_l(stream, capacity=k, rng=random.Random(t))
        counts.update(res.items)
    expected = trials * k / n
    sigma = (expected * (1 - k / n)) ** 0.5
    for v in (f"v-{i}" for i in range(n)):
        assert abs(counts[v] - expected) < 5 * sigma


# ---------- A-Res weighted basics ------------------------------------------


def test_weighted_fills() -> None:
    pairs = [("a", 1.0), ("b", 2.0), ("c", 3.0)]
    res = sample_weighted(pairs, capacity=5, rng=random.Random(0))
    assert {w.value for w in res.items} == {"a", "b", "c"}


def test_weighted_capacity_enforced() -> None:
    pairs = [(f"v-{i}", 1.0) for i in range(20)]
    res = sample_weighted(pairs, capacity=5, rng=random.Random(0))
    assert len(res.items) == 5


def test_weighted_heavy_items_more_likely() -> None:
    """Items with weight 100 should appear far more often than weight-1 items."""
    counts: Counter[str] = Counter()
    trials = 500
    for t in range(trials):
        # 1 heavy + 99 light items.
        pairs = [("HEAVY", 100.0)] + [(f"light-{i}", 1.0) for i in range(99)]
        res = sample_weighted(pairs, capacity=10, rng=random.Random(t))
        counts.update(w.value for w in res.items)
    heavy_count = counts["HEAVY"]
    light_avg = sum(counts[f"light-{i}"] for i in range(99)) / 99
    assert heavy_count > light_avg * 5, f"heavy={heavy_count}, light_avg={light_avg:.1f}"


def test_weighted_rejects_zero_weight() -> None:
    res = build_weighted(5)
    with pytest.raises(ValueError, match="weight"):
        add_weighted(res, "x", 0.0)


def test_weighted_rejects_infinite_weight() -> None:
    res = build_weighted(5)
    with pytest.raises(ValueError, match="finite"):
        add_weighted(res, "x", float("inf"))


def test_weighted_sorted_by_key_ascending() -> None:
    pairs = [(f"v-{i}", float(i + 1)) for i in range(20)]
    res = sample_weighted(pairs, capacity=10, rng=random.Random(0))
    for i in range(1, len(res.items)):
        assert res.items[i - 1].key <= res.items[i].key


# ---------- freeze / thaw --------------------------------------------------


def test_freeze_thaw_preserves_items() -> None:
    res = build_r(5)
    for v in ["a", "b", "c"]:
        add_r(res, v)
    snap = freeze(res)
    rehydrated = thaw(snap)
    assert rehydrated.items == res.items
    assert rehydrated.n_seen == res.n_seen


def test_thaw_supports_continued_sampling() -> None:
    """After thaw, we can keep streaming into the reservoir."""
    res = build_r(5)
    for v in ["a", "b", "c", "d", "e"]:
        add_r(res, v)
    snap = freeze(res)
    res2 = thaw(snap)
    # Add more items — should not error.
    add_r(res2, "f", rng=random.Random(0))
    assert res2.n_seen == 6


# ---------- edge cases -----------------------------------------------------


def test_r_capacity_one() -> None:
    """k=1 reservoir keeps exactly one item from the stream."""
    res = sample_r([f"v-{i}" for i in range(100)], capacity=1, rng=random.Random(0))
    assert res.n_kept == 1


def test_l_capacity_one() -> None:
    res = sample_l([f"v-{i}" for i in range(100)], capacity=1, rng=random.Random(0))
    assert res.n_kept == 1
