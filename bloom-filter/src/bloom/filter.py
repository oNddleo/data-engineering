"""Core Bloom-filter operations — build, query, freeze, union.

Two complementary shapes coexist:

* ``BloomFilter`` (frozen) — for snapshots, serialization, set ops
  expressed as pure functions returning *new* filters.
* ``BuildableBloom`` (mutable) — for streaming inserts. Wraps a
  ``bytearray``; ``freeze()`` produces a ``BloomFilter`` snapshot.

Union is exact: ``bits(A ∪ B) = bits(A) | bits(B)``. Intersection
estimate is approximate (``bits(A) & bits(B)``); the resulting filter
contains every item in ``A ∩ B`` but may contain extras whose
positions happened to collide — typically larger than just the
union of false positives.
"""

from __future__ import annotations

from bloom.hash import positions
from bloom.schema import BloomFilter, BuildableBloom
from bloom.sizing import optimal_n_hashes, optimal_size_bits


def build(capacity: int, target_fpr: float = 0.01) -> BuildableBloom:
    """Construct an empty Bloom filter sized for ``capacity`` at ``target_fpr``."""
    m = optimal_size_bits(capacity, target_fpr)
    k = optimal_n_hashes(m, capacity)
    n_bytes = (m + 7) // 8
    return BuildableBloom(
        size_bits=m,
        n_hashes=k,
        capacity=capacity,
        target_fpr=target_fpr,
        _bits=bytearray(n_bytes),
    )


def add(bf: BuildableBloom, value: str | bytes | int | float) -> None:
    """Set each of ``value``'s k bit positions."""
    for pos in positions(value, bf.n_hashes, bf.size_bits):
        bf._bits[pos >> 3] |= 1 << (pos & 7)
    bf.n_items += 1


def contains(
    bf: BuildableBloom | BloomFilter,
    value: str | bytes | int | float,
) -> bool:
    """``True`` if **every** bit position for ``value`` is set.

    Returns ``False`` → definitely not added.
    Returns ``True`` → probably added (false-positive rate bounded).
    """
    if isinstance(bf, BuildableBloom):
        for pos in positions(value, bf.n_hashes, bf.size_bits):
            if not (bf._bits[pos >> 3] & (1 << (pos & 7))):
                return False
        return True
    # BloomFilter (immutable, int-bits)
    return all((bf.bits >> pos) & 1 for pos in positions(value, bf.n_hashes, bf.size_bits))


def freeze(bf: BuildableBloom) -> BloomFilter:
    """Snapshot a mutable filter into an immutable ``BloomFilter``."""
    bits = int.from_bytes(bytes(bf._bits), byteorder="little", signed=False)
    # Mask off any spurious high bits beyond size_bits (last byte may have padding).
    mask = (1 << bf.size_bits) - 1
    return BloomFilter(
        size_bits=bf.size_bits,
        n_hashes=bf.n_hashes,
        n_items=bf.n_items,
        bits=bits & mask,
    )


def thaw(snapshot: BloomFilter, capacity: int, target_fpr: float) -> BuildableBloom:
    """Rebuild a mutable filter from an immutable snapshot.

    ``capacity`` and ``target_fpr`` aren't carried in the snapshot
    (they're sizing hints, not part of the filter state) — caller must
    re-supply them. ``size_bits`` and ``n_hashes`` come from the snapshot.
    """
    n_bytes = (snapshot.size_bits + 7) // 8
    raw = snapshot.bits.to_bytes(n_bytes, byteorder="little", signed=False)
    return BuildableBloom(
        size_bits=snapshot.size_bits,
        n_hashes=snapshot.n_hashes,
        capacity=capacity,
        target_fpr=target_fpr,
        _bits=bytearray(raw),
        n_items=snapshot.n_items,
    )


def union(a: BloomFilter, b: BloomFilter) -> BloomFilter:
    """Exact bitwise union of two filters (same shape required).

    Result represents the multiset ``A ∪ B``; ``n_items`` is upper-bounded
    by the sum (true distinct count would require knowing the overlap).
    """
    _check_shape(a, b)
    return BloomFilter(
        size_bits=a.size_bits,
        n_hashes=a.n_hashes,
        n_items=a.n_items + b.n_items,
        bits=a.bits | b.bits,
    )


def intersect_estimate(a: BloomFilter, b: BloomFilter) -> BloomFilter:
    """Bitwise intersection — approximates ``A ∩ B``.

    Every element in the true intersection is preserved (no false
    negatives), but the result may contain spurious bits where two
    unrelated items in A and B happened to set the same position. The
    effective FPR can be higher than either input.
    """
    _check_shape(a, b)
    return BloomFilter(
        size_bits=a.size_bits,
        n_hashes=a.n_hashes,
        n_items=min(a.n_items, b.n_items),
        bits=a.bits & b.bits,
    )


def _check_shape(a: BloomFilter, b: BloomFilter) -> None:
    if a.size_bits != b.size_bits:
        raise ValueError(
            f"filters must share size_bits ({a.size_bits} != {b.size_bits})",
        )
    if a.n_hashes != b.n_hashes:
        raise ValueError(
            f"filters must share n_hashes ({a.n_hashes} != {b.n_hashes})",
        )


__all__ = [
    "add",
    "build",
    "contains",
    "freeze",
    "intersect_estimate",
    "thaw",
    "union",
]
