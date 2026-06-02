"""Concrete CRDT implementations built on the semilattice algebra.

All CRDTs implement merge() which is idempotent, commutative, and associative.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

from crdt.lattice import Lattice

V = TypeVar("V")

# ── GCounter ──────────────────────────────────────────────────────────────────


@dataclass
class GCounter(Lattice):
    """Grow-only counter: per-node unsigned counters under pointwise max.

    State: {node_id: count}
    """

    _counts: dict[str, int] = field(default_factory=dict)

    @classmethod
    def new(cls) -> GCounter:
        return cls()

    def increment(self, node_id: str, delta: int = 1) -> GCounter:
        counts = dict(self._counts)
        counts[node_id] = counts.get(node_id, 0) + delta
        return GCounter(counts)

    def value(self) -> int:
        return sum(self._counts.values())

    def merge(self, other: GCounter) -> GCounter:
        all_keys = set(self._counts) | set(other._counts)
        merged = {k: max(self._counts.get(k, 0), other._counts.get(k, 0)) for k in all_keys}
        return GCounter(merged)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GCounter):
            return NotImplemented
        return self._counts == other._counts

    def __hash__(self) -> int:
        return hash(tuple(sorted(self._counts.items())))

    def to_dict(self) -> dict[str, object]:
        return {"type": "GCounter", "counts": dict(self._counts)}


# ── PNCounter ─────────────────────────────────────────────────────────────────


@dataclass
class PNCounter(Lattice):
    """PN-Counter = Product(GCounter, GCounter) — increments and decrements.

    State: (increments: GCounter, decrements: GCounter)
    value = inc.value() - dec.value()
    """

    _inc: GCounter = field(default_factory=GCounter)
    _dec: GCounter = field(default_factory=GCounter)

    @classmethod
    def new(cls) -> PNCounter:
        return cls()

    def increment(self, node_id: str, delta: int = 1) -> PNCounter:
        return PNCounter(self._inc.increment(node_id, delta), self._dec)

    def decrement(self, node_id: str, delta: int = 1) -> PNCounter:
        return PNCounter(self._inc, self._dec.increment(node_id, delta))

    def value(self) -> int:
        return self._inc.value() - self._dec.value()

    def merge(self, other: PNCounter) -> PNCounter:
        return PNCounter(self._inc.merge(other._inc), self._dec.merge(other._dec))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, PNCounter):
            return NotImplemented
        return self._inc == other._inc and self._dec == other._dec

    def __hash__(self) -> int:
        return hash((self._inc, self._dec))

    def to_dict(self) -> dict[str, object]:
        return {
            "type": "PNCounter",
            "inc": self._inc.to_dict(),
            "dec": self._dec.to_dict(),
        }


# ── LWWRegister ───────────────────────────────────────────────────────────────


@dataclass
class LWWRegister(Lattice, Generic[V]):
    """Last-Write-Wins register.

    Tie-break on (timestamp, node_id); larger wins.
    """

    _value: V | None = field(default=None)
    _timestamp: float = field(default=0.0)
    _node_id: str = field(default="")

    @classmethod
    def new(cls, value: V, timestamp: float = 0.0, node_id: str = "") -> LWWRegister[V]:
        return cls(value, timestamp, node_id)

    def write(self, value: V, timestamp: float, node_id: str = "") -> LWWRegister[V]:
        return LWWRegister(value, timestamp, node_id)

    def read(self) -> V | None:
        return self._value

    def merge(self, other: LWWRegister[V]) -> LWWRegister[V]:
        # Higher timestamp wins; tie-break on node_id
        if (other._timestamp, other._node_id) > (self._timestamp, self._node_id):
            return other
        return self

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, LWWRegister):
            return NotImplemented
        return (
            self._value == other._value
            and self._timestamp == other._timestamp
            and self._node_id == other._node_id
        )

    def __hash__(self) -> int:
        return hash((self._timestamp, self._node_id))

    def to_dict(self) -> dict[str, object]:
        return {
            "type": "LWWRegister",
            "value": self._value,
            "timestamp": self._timestamp,
            "node_id": self._node_id,
        }


# ── GSet ──────────────────────────────────────────────────────────────────────


@dataclass
class GSet(Lattice):
    """Grow-only set: elements under set union."""

    _elements: frozenset[str] = field(default_factory=frozenset)

    @classmethod
    def new(cls, *elements: str) -> GSet:
        return cls(frozenset(elements))

    def add(self, element: str) -> GSet:
        return GSet(self._elements | {element})

    def elements(self) -> frozenset[str]:
        return self._elements

    def merge(self, other: GSet) -> GSet:
        return GSet(self._elements | other._elements)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GSet):
            return NotImplemented
        return self._elements == other._elements

    def __hash__(self) -> int:
        return hash(self._elements)

    def to_dict(self) -> dict[str, object]:
        return {"type": "GSet", "elements": sorted(self._elements)}


# ── 2PSet ─────────────────────────────────────────────────────────────────────


@dataclass
class TwoPSet(Lattice):
    """Two-phase set: once removed, never re-added.

    State: (additions: GSet, removals: GSet)
    value = additions - removals
    """

    _add: GSet = field(default_factory=GSet)
    _rem: GSet = field(default_factory=GSet)

    @classmethod
    def new(cls) -> TwoPSet:
        return cls()

    def add(self, element: str) -> TwoPSet:
        if element in self._rem.elements():
            return self  # already tombstoned
        return TwoPSet(self._add.add(element), self._rem)

    def remove(self, element: str) -> TwoPSet:
        if element not in self._add.elements():
            return self  # can't remove what wasn't added
        return TwoPSet(self._add, self._rem.add(element))

    def contains(self, element: str) -> bool:
        return element in self._add.elements() and element not in self._rem.elements()

    def elements(self) -> frozenset[str]:
        return self._add.elements() - self._rem.elements()

    def merge(self, other: TwoPSet) -> TwoPSet:
        return TwoPSet(self._add.merge(other._add), self._rem.merge(other._rem))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TwoPSet):
            return NotImplemented
        return self._add == other._add and self._rem == other._rem

    def __hash__(self) -> int:
        return hash((self._add, self._rem))

    def to_dict(self) -> dict[str, object]:
        return {
            "type": "TwoPSet",
            "add": self._add.to_dict(),
            "rem": self._rem.to_dict(),
        }


# ── ORSet ─────────────────────────────────────────────────────────────────────


@dataclass
class ORSet(Lattice):
    """Observed-Remove Set: concurrent add wins over remove.

    Each element is tagged with a unique token; removes tombstone tokens.
    State: {element: {token}} × {tombstone_token}
    """

    _entries: dict[str, frozenset[str]] = field(default_factory=dict)
    _tombstones: frozenset[str] = field(default_factory=frozenset)
    _counter: int = field(default=0)

    @classmethod
    def new(cls) -> ORSet:
        return cls()

    def add(self, element: str, node_id: str = "n") -> ORSet:
        token = f"{node_id}:{self._counter}"
        entries = dict(self._entries)
        entries[element] = (entries.get(element) or frozenset()) | {token}
        return ORSet(entries, self._tombstones, self._counter + 1)

    def remove(self, element: str) -> ORSet:
        tokens = self._entries.get(element) or frozenset()
        return ORSet(self._entries, self._tombstones | tokens, self._counter)

    def contains(self, element: str) -> bool:
        alive = (self._entries.get(element) or frozenset()) - self._tombstones
        return len(alive) > 0

    def elements(self) -> frozenset[str]:
        return frozenset(e for e in self._entries if self.contains(e))

    def merge(self, other: ORSet) -> ORSet:
        all_keys = set(self._entries) | set(other._entries)
        merged_entries: dict[str, frozenset[str]] = {
            k: (self._entries.get(k) or frozenset()) | (other._entries.get(k) or frozenset())
            for k in all_keys
        }
        merged_tombs = self._tombstones | other._tombstones
        counter = max(self._counter, other._counter)
        return ORSet(merged_entries, merged_tombs, counter)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ORSet):
            return NotImplemented
        return self._entries == other._entries and self._tombstones == other._tombstones

    def __hash__(self) -> int:
        return hash((tuple(sorted(self._entries.items())), self._tombstones))

    def to_dict(self) -> dict[str, object]:
        return {
            "type": "ORSet",
            "entries": {k: sorted(v) for k, v in self._entries.items()},
            "tombstones": sorted(self._tombstones),
        }


# ── MVRegister ────────────────────────────────────────────────────────────────


@dataclass
class MVRegister(Lattice):
    """Multi-Value Register: concurrent writes produce multiple values.

    State: {(value, vector_clock_version)}
    On concurrent writes, all values are kept.
    On merge, dominate entries (causally later) win over dominated ones.
    """

    _versions: frozenset[tuple[str, int]] = field(default_factory=frozenset)
    _node_clocks: dict[str, int] = field(default_factory=dict)

    @classmethod
    def new(cls) -> MVRegister:
        return cls()

    def write(self, value: str, node_id: str) -> MVRegister:
        new_clock = self._node_clocks.get(node_id, 0) + 1
        clocks = dict(self._node_clocks)
        clocks[node_id] = new_clock
        version = (value, new_clock)
        # Keep only versions not dominated by this new one
        old_clock = self._node_clocks.get(node_id, 0)
        kept = frozenset(v for v in self._versions if clocks.get(node_id, 0) <= old_clock)
        return MVRegister(kept | {version}, clocks)

    def read(self) -> list[str]:
        return [v for v, _ in self._versions]

    def merge(self, other: MVRegister) -> MVRegister:
        merged_clocks = {
            k: max(self._node_clocks.get(k, 0), other._node_clocks.get(k, 0))
            for k in set(self._node_clocks) | set(other._node_clocks)
        }
        merged_versions = self._versions | other._versions
        return MVRegister(merged_versions, merged_clocks)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, MVRegister):
            return NotImplemented
        return self._versions == other._versions and self._node_clocks == other._node_clocks

    def __hash__(self) -> int:
        return hash((self._versions, tuple(sorted(self._node_clocks.items()))))

    def to_dict(self) -> dict[str, object]:
        return {
            "type": "MVRegister",
            "versions": sorted((v, c) for v, c in self._versions),
            "node_clocks": dict(self._node_clocks),
        }
