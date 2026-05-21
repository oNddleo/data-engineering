"""ConsistentHashRing."""

from __future__ import annotations

import pytest

from partitioner.consistent import ConsistentHashRing


def test_empty_ring_lookup_raises() -> None:
    ring = ConsistentHashRing()
    with pytest.raises(RuntimeError):
        ring.node_for("k")


def test_single_node_owns_everything() -> None:
    ring = ConsistentHashRing(["n1"])
    for i in range(100):
        assert ring.node_for(f"k{i}") == "n1"


def test_stable_lookup() -> None:
    ring = ConsistentHashRing(["a", "b", "c"], replicas=64)
    a = ring.node_for("alpha")
    b = ring.node_for("alpha")
    assert a == b


def test_n_virtual_count() -> None:
    ring = ConsistentHashRing(["a", "b", "c"], replicas=128)
    assert ring.n_virtual == 3 * 128


def test_add_node_minimal_reshuffle() -> None:
    """Adding a node should move only ~1/N of keys, not all of them."""
    ring = ConsistentHashRing(["a", "b", "c", "d"], replicas=200)
    keys = [f"k{i:05d}" for i in range(2000)]
    before = {k: ring.node_for(k) for k in keys}
    ring.add_node("e")
    after = {k: ring.node_for(k) for k in keys}
    moved = sum(1 for k in keys if before[k] != after[k])
    # Expected ~1/5 = 20%; allow wide band (15–35%).
    rate = moved / len(keys)
    assert 0.10 < rate < 0.40, f"moved {rate:.2%}"


def test_remove_node_only_orphans_move() -> None:
    """Removing a node should only re-home its keys."""
    ring = ConsistentHashRing(["a", "b", "c"], replicas=200)
    keys = [f"k{i:05d}" for i in range(2000)]
    before = {k: ring.node_for(k) for k in keys}
    ring.remove_node("a")
    after = {k: ring.node_for(k) for k in keys}
    for k in keys:
        if before[k] != "a":
            assert before[k] == after[k], f"non-a key {k!r} moved"


def test_balance_with_replicas() -> None:
    """More replicas = better balance."""
    ring = ConsistentHashRing(["a", "b", "c", "d"], replicas=200)
    counts = {"a": 0, "b": 0, "c": 0, "d": 0}
    for i in range(20_000):
        counts[ring.node_for(f"k{i}")] += 1
    # Expected mean 5000, allow ±25%.
    assert all(3500 <= c <= 6500 for c in counts.values()), counts


def test_idempotent_add() -> None:
    ring = ConsistentHashRing(["a"], replicas=64)
    n_before = ring.n_virtual
    ring.add_node("a")
    assert ring.n_virtual == n_before


def test_remove_nonexistent_noop() -> None:
    ring = ConsistentHashRing(["a"], replicas=64)
    ring.remove_node("nonesuch")
    assert ring.nodes == {"a"}


def test_rejects_bad_replicas() -> None:
    with pytest.raises(ValueError):
        ConsistentHashRing(replicas=0)


def test_rejects_empty_node_id() -> None:
    ring = ConsistentHashRing()
    with pytest.raises(ValueError):
        ring.add_node("")
