"""Bloom filter implementation using double hashing.

Trick: instead of running k independent hash functions, we use only
two — sha256 and md5 — and synthesise the rest as

    h_i(x) = (h1(x) + i · h2(x)) mod m

This is the Kirsch-Mitzenmacher "less hashing, same performance"
construction. It preserves the asymptotic FPR while costing only two
hash evaluations per item, not k.

We avoid external deps; sha256 and md5 are both in ``hashlib``. md5
isn't cryptographically secure, but for hashing into a Bloom filter
it's fine — we only care about uniform distribution, not collision
resistance.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

    from bloomdedup.schema import BloomParams


class BloomFilter:
    """Mutable Bloom filter with ``add`` and ``contains``.

    The filter is exposed as a flat bytearray so it can be cheaply
    serialised — we don't ship a fancy binary format. Use
    ``to_bytes`` / ``from_bytes`` for snapshots.
    """

    __slots__ = ("params", "_bits", "_n_added")

    def __init__(self, params: BloomParams) -> None:
        self.params = params
        self._bits = bytearray(params.m_bytes)
        self._n_added = 0

    # ----- core primitive ------------------------------------------------

    def _indices(self, item: str) -> tuple[int, ...]:
        """Yield ``k`` bit indices for ``item`` via double hashing."""
        data = item.encode("utf-8")
        h1 = int.from_bytes(hashlib.sha256(data).digest()[:8], "big")
        h2 = int.from_bytes(hashlib.md5(data).digest()[:8], "big")
        m = self.params.m_bits
        # h2 must be odd to ensure coprimality with any m (cycles full ring).
        if h2 % 2 == 0:
            h2 += 1
        return tuple((h1 + i * h2) % m for i in range(self.params.k_hashes))

    # ----- public API ----------------------------------------------------

    def add(self, item: str) -> bool:
        """Add ``item`` to the filter.

        Returns ``True`` if the item was probably already present
        (i.e. all bits were already set — could be a false positive),
        ``False`` if at least one bit was new (definitely not present
        before).
        """
        was_present = True
        for idx in self._indices(item):
            byte, bit = divmod(idx, 8)
            mask = 1 << bit
            if not self._bits[byte] & mask:
                was_present = False
                self._bits[byte] |= mask
        if not was_present:
            self._n_added += 1
        return was_present

    def __contains__(self, item: object) -> bool:
        if not isinstance(item, str):
            return False
        return all(
            self._bits[byte] & (1 << bit)
            for byte, bit in (divmod(idx, 8) for idx in self._indices(item))
        )

    def update(self, items: Iterable[str]) -> None:
        for item in items:
            self.add(item)

    # ----- introspection -------------------------------------------------

    @property
    def n_added(self) -> int:
        """Approximate count of unique items added (may undercount on
        false positives, since we don't increment when ``add`` thinks
        the item was already there)."""
        return self._n_added

    @property
    def fill_ratio(self) -> float:
        """Fraction of bits set — a real-time saturation indicator."""
        set_bits = sum(bin(b).count("1") for b in self._bits)
        return set_bits / self.params.m_bits

    # ----- serialisation -------------------------------------------------

    def to_bytes(self) -> bytes:
        return bytes(self._bits)

    @classmethod
    def from_bytes(cls, params: BloomParams, data: bytes) -> BloomFilter:
        if len(data) != params.m_bytes:
            raise ValueError(
                f"data length {len(data)} doesn't match params.m_bytes {params.m_bytes}",
            )
        bf = cls(params)
        bf._bits = bytearray(data)
        return bf


__all__ = ["BloomFilter"]
