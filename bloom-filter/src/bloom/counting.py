"""Counting Bloom filter — supports deletion.

A counting Bloom replaces each single bit with an 8-bit saturating
counter. ``add(v)`` increments each of v's k cells (cap at 255);
``remove(v)`` decrements them (clamped at 0). ``contains(v)`` is
``True`` iff every cell is non-zero.

Trade-offs vs vanilla Bloom:

* **+** Supports ``remove(v)``.
* **−** 8× the memory.
* **−** Saturation: if any cell hits 255 due to many hash collisions,
  subsequent ``remove`` calls cannot decrement that cell back without
  risking a *false negative* (we lost track of how many distinct items
  share that cell). We never decrement saturated cells — preserves the
  "no false negatives" property at the cost of a small permanent
  membership overhead.
"""

from __future__ import annotations

from bloom.hash import positions
from bloom.schema import CountingBloom
from bloom.sizing import optimal_n_hashes, optimal_size_bits

_MAX_COUNTER = 255


def build_counting(capacity: int, target_fpr: float = 0.01) -> CountingBloom:
    """Construct an empty CountingBloom sized for ``capacity`` at ``target_fpr``."""
    m = optimal_size_bits(capacity, target_fpr)
    k = optimal_n_hashes(m, capacity)
    return CountingBloom(
        size_buckets=m,
        n_hashes=k,
        capacity=capacity,
        target_fpr=target_fpr,
        _counters=bytearray(m),
    )


def add_counting(cb: CountingBloom, value: str | bytes | int | float) -> None:
    """Increment each of ``value``'s k counters (saturating at 255)."""
    for pos in positions(value, cb.n_hashes, cb.size_buckets):
        if cb._counters[pos] < _MAX_COUNTER:
            cb._counters[pos] += 1
    cb.n_items += 1


def remove_counting(
    cb: CountingBloom,
    value: str | bytes | int | float,
) -> bool:
    """Decrement each of ``value``'s k counters; return ``True`` if removed.

    Returns ``False`` if any counter is already 0 (meaning ``value`` was
    never added — refuse to corrupt the filter). Saturated counters
    (255) are never decremented (we lost the exact insertion count).
    """
    pos_list = positions(value, cb.n_hashes, cb.size_buckets)
    if any(cb._counters[p] == 0 for p in pos_list):
        return False
    for pos in pos_list:
        if cb._counters[pos] < _MAX_COUNTER:
            cb._counters[pos] -= 1
    cb.n_items = max(0, cb.n_items - 1)
    return True


def contains_counting(
    cb: CountingBloom,
    value: str | bytes | int | float,
) -> bool:
    """``True`` if every counter for ``value`` is non-zero."""
    return all(cb._counters[p] > 0 for p in positions(value, cb.n_hashes, cb.size_buckets))


__all__ = [
    "add_counting",
    "build_counting",
    "contains_counting",
    "remove_counting",
]
