"""Hypothesis property tests."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from partitioner.consistent import ConsistentHashRing
from partitioner.hash_mod import HashModPartitioner
from partitioner.range_part import RangePartitioner

_key = st.text(min_size=1, max_size=20)


@given(_key, st.integers(min_value=1, max_value=64))
@settings(max_examples=80)
def test_hash_mod_in_range(key: str, n: int) -> None:
    p = HashModPartitioner(n)
    assert 0 <= p.partition_for(key) < n


@given(_key, _key, st.integers(min_value=1, max_value=64))
@settings(max_examples=60)
def test_hash_mod_deterministic(k1: str, k2: str, n: int) -> None:
    """Equal keys produce equal partitions."""
    p = HashModPartitioner(n)
    if k1 == k2:
        assert p.partition_for(k1) == p.partition_for(k2)


@given(st.lists(st.integers(min_value=-1000, max_value=1000), unique=True, min_size=0, max_size=10))
@settings(max_examples=60)
def test_range_in_bounds(boundaries: list[int]) -> None:
    """Every key maps to a valid partition."""
    boundaries = sorted(boundaries)
    p = RangePartitioner(boundaries)
    for key in [-5000, -1, 0, 1, 5000]:
        part = p.partition_for(key)
        assert 0 <= part < p.n_partitions


@given(st.lists(st.integers(min_value=0, max_value=1000), unique=True, min_size=1, max_size=10))
@settings(max_examples=60)
def test_range_monotone(boundaries: list[int]) -> None:
    """Partition number is non-decreasing in the key."""
    boundaries = sorted(boundaries)
    p = RangePartitioner(boundaries)
    keys = sorted([-100, 0, 50, 100, 200, 500, 1500])
    parts = [p.partition_for(k) for k in keys]
    assert parts == sorted(parts)


@given(
    st.lists(st.text(min_size=1, max_size=5, alphabet="abc"), unique=True, min_size=1, max_size=5),
    st.text(min_size=1, max_size=10),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=40)
def test_consistent_node_in_set(nodes: list[str], key: str) -> None:
    """Looked-up node is always one of the configured nodes."""
    ring = ConsistentHashRing(nodes, replicas=32)
    assert ring.node_for(key) in set(nodes)


@given(
    st.lists(
        st.text(min_size=1, max_size=5, alphabet="abcdefg"), unique=True, min_size=2, max_size=5
    ),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=20)
def test_consistent_remove_only_moves_orphans(nodes: list[str]) -> None:
    """Removing a node never moves keys that didn't belong to it."""
    ring = ConsistentHashRing(nodes, replicas=64)
    keys = [f"k{i:04d}" for i in range(200)]
    before = {k: ring.node_for(k) for k in keys}
    victim = nodes[0]
    ring.remove_node(victim)
    after = {k: ring.node_for(k) for k in keys}
    for k in keys:
        if before[k] != victim:
            assert before[k] == after[k]
