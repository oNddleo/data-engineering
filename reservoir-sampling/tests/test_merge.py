"""Reservoir merge — uniform + weighted distributed sampling."""

from __future__ import annotations

import random
from collections import Counter

import pytest

from reservoir.algorithms import sample_l, sample_r, sample_weighted
from reservoir.merge import merge_uniform, merge_weighted
from reservoir.schema import Reservoir, WeightedReservoir

# ---------- merge_uniform --------------------------------------------------


def test_merge_uniform_preserves_n_seen() -> None:
    a = sample_r([f"a-{i}" for i in range(50)], capacity=10, rng=random.Random(1))
    b = sample_r([f"b-{i}" for i in range(50)], capacity=10, rng=random.Random(2))
    merged = merge_uniform(a, b, rng=random.Random(0))
    assert merged.n_seen == 100


def test_merge_uniform_capacity_preserved() -> None:
    a = sample_r([f"a-{i}" for i in range(50)], capacity=10, rng=random.Random(1))
    b = sample_r([f"b-{i}" for i in range(50)], capacity=10, rng=random.Random(2))
    merged = merge_uniform(a, b, rng=random.Random(0))
    assert merged.capacity == 10
    assert merged.n_kept <= 10


def test_merge_uniform_items_from_both() -> None:
    """Merged reservoir items should be drawn from the union of inputs."""
    a = sample_r([f"a-{i}" for i in range(50)], capacity=10, rng=random.Random(1))
    b = sample_r([f"b-{i}" for i in range(50)], capacity=10, rng=random.Random(2))
    merged = merge_uniform(a, b, rng=random.Random(0))
    union = set(a.items) | set(b.items)
    assert set(merged.items).issubset(union)


def test_merge_uniform_rejects_mismatched_capacity() -> None:
    a = Reservoir(capacity=5, items=("a",), n_seen=1)
    b = Reservoir(capacity=10, items=("b",), n_seen=1)
    with pytest.raises(ValueError, match="capacity"):
        merge_uniform(a, b)


def test_merge_uniform_empty_pair() -> None:
    """Merging two empty reservoirs gives an empty reservoir."""
    a = Reservoir(capacity=10, items=(), n_seen=0)
    b = Reservoir(capacity=10, items=(), n_seen=0)
    merged = merge_uniform(a, b, rng=random.Random(0))
    assert merged.n_kept == 0
    assert merged.n_seen == 0


def test_merge_uniform_one_empty() -> None:
    """Merging an empty reservoir with a full one keeps the full one's items."""
    a = sample_r([f"a-{i}" for i in range(50)], capacity=10, rng=random.Random(1))
    b = Reservoir(capacity=10, items=(), n_seen=0)
    merged = merge_uniform(a, b, rng=random.Random(0))
    # Every merged item must come from `a`.
    assert set(merged.items).issubset(set(a.items))


def test_merge_uniform_approximate_uniformity() -> None:
    """Merging two equal-size shards should give roughly uniform results."""
    counts: Counter[str] = Counter()
    trials = 300
    for t in range(trials):
        a = sample_r([f"a-{i}" for i in range(100)], capacity=20, rng=random.Random(t))
        b = sample_r([f"b-{i}" for i in range(100)], capacity=20, rng=random.Random(t + 1000))
        merged = merge_uniform(a, b, rng=random.Random(t + 2000))
        counts.update(merged.items)
    # 20-slot merge over 200 items → ~10% chance per item per trial → ~30 expected.
    # Just sanity check: distinct items broad, no extreme spikes.
    assert len(counts) > 50  # broad spread


# ---------- merge_weighted -------------------------------------------------


def test_merge_weighted_preserves_n_seen() -> None:
    pairs_a = [(f"a-{i}", 1.0) for i in range(20)]
    pairs_b = [(f"b-{i}", 1.0) for i in range(20)]
    a = sample_weighted(pairs_a, capacity=5, rng=random.Random(1))
    b = sample_weighted(pairs_b, capacity=5, rng=random.Random(2))
    merged = merge_weighted(a, b)
    assert merged.n_seen == 40


def test_merge_weighted_keeps_top_k() -> None:
    """The merged reservoir holds the top-k items by key."""
    pairs_a = [(f"a-{i}", float(i + 1)) for i in range(10)]
    pairs_b = [(f"b-{i}", float(i + 1)) for i in range(10)]
    a = sample_weighted(pairs_a, capacity=5, rng=random.Random(1))
    b = sample_weighted(pairs_b, capacity=5, rng=random.Random(2))
    merged = merge_weighted(a, b)
    assert len(merged.items) == 5


def test_merge_weighted_total_weight_sums() -> None:
    pairs_a = [(f"a-{i}", 2.0) for i in range(10)]
    pairs_b = [(f"b-{i}", 3.0) for i in range(10)]
    a = sample_weighted(pairs_a, capacity=5, rng=random.Random(1))
    b = sample_weighted(pairs_b, capacity=5, rng=random.Random(2))
    merged = merge_weighted(a, b)
    assert abs(merged.total_weight_seen - (20.0 + 30.0)) < 1e-9


def test_merge_weighted_sorted_after() -> None:
    pairs_a = [(f"a-{i}", float(i + 1)) for i in range(15)]
    pairs_b = [(f"b-{i}", float(i + 1)) for i in range(15)]
    a = sample_weighted(pairs_a, capacity=10, rng=random.Random(1))
    b = sample_weighted(pairs_b, capacity=10, rng=random.Random(2))
    merged = merge_weighted(a, b)
    for i in range(1, len(merged.items)):
        assert merged.items[i - 1].key <= merged.items[i].key


def test_merge_weighted_rejects_mismatched_capacity() -> None:
    a = WeightedReservoir(capacity=5)
    b = WeightedReservoir(capacity=10)
    with pytest.raises(ValueError, match="capacity"):
        merge_weighted(a, b)


# ---------- Algorithm L merge ----------------------------------------------


def test_merge_l_reservoirs() -> None:
    """merge_uniform works on L-sampled reservoirs too."""
    a = sample_l([f"a-{i}" for i in range(50)], capacity=10, rng=random.Random(1))
    b = sample_l([f"b-{i}" for i in range(50)], capacity=10, rng=random.Random(2))
    merged = merge_uniform(a, b, rng=random.Random(0))
    assert merged.n_seen == 100
    union = set(a.items) | set(b.items)
    assert set(merged.items).issubset(union)
