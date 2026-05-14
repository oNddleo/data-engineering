"""Merkle tree tests."""

from __future__ import annotations

import hashlib

import pytest

from sbv2345.merkle import EMPTY_ROOT, hash_pair, merkle_root


def _h(seed: int) -> str:
    return hashlib.sha256(str(seed).encode()).hexdigest()


def test_empty_leaves_yields_empty_root():
    assert merkle_root([]) == EMPTY_ROOT


def test_single_leaf_is_root():
    leaf = _h(0)
    assert merkle_root([leaf]) == leaf


def test_two_leaves():
    a, b = _h(0), _h(1)
    expected = hash_pair(a, b)
    assert merkle_root([a, b]) == expected


def test_three_leaves_duplicates_last():
    a, b, c = _h(0), _h(1), _h(2)
    # Level 0: [a, b, c] → duplicate c → [a, b, c, c]
    # Level 1: [hash(a,b), hash(c,c)]
    # Level 2: hash(hash(a,b), hash(c,c))
    level1 = [hash_pair(a, b), hash_pair(c, c)]
    expected = hash_pair(level1[0], level1[1])
    assert merkle_root([a, b, c]) == expected


def test_four_leaves_even():
    leaves = [_h(i) for i in range(4)]
    level1 = [hash_pair(leaves[0], leaves[1]), hash_pair(leaves[2], leaves[3])]
    expected = hash_pair(level1[0], level1[1])
    assert merkle_root(leaves) == expected


def test_rejects_non_hex_leaf():
    with pytest.raises(ValueError):
        merkle_root(["not-a-hash"])


def test_rejects_wrong_length_leaf():
    with pytest.raises(ValueError):
        merkle_root(["a" * 63])


def test_hash_pair_is_deterministic():
    a, b = _h(0), _h(1)
    assert hash_pair(a, b) == hash_pair(a, b)


def test_hash_pair_is_order_sensitive():
    a, b = _h(0), _h(1)
    assert hash_pair(a, b) != hash_pair(b, a)


def test_merkle_root_changes_with_leaf_change():
    leaves = [_h(i) for i in range(5)]
    root_before = merkle_root(leaves)
    leaves[2] = _h(999)
    root_after = merkle_root(leaves)
    assert root_before != root_after


def test_merkle_root_is_deterministic():
    leaves = [_h(i) for i in range(10)]
    assert merkle_root(leaves) == merkle_root(leaves)
