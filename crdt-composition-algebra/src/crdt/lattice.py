"""Abstract semilattice interface and composition operators.

A semilattice is a set S with a binary join operation (⊔) that is:
- Idempotent:    s ⊔ s  = s
- Commutative:   s ⊔ t  = t ⊔ s
- Associative:   (s ⊔ t) ⊔ u = s ⊔ (t ⊔ u)

The induced partial order is: s ≤ t ⟺ s ⊔ t = t.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TypeVar

T = TypeVar("T", bound="Lattice")


class Lattice(ABC):
    """Abstract base for all semilattice-based CRDTs."""

    @abstractmethod
    def merge(self: T, other: T) -> T:
        """Join two lattice elements: self ⊔ other."""

    def __le__(self: T, other: T) -> bool:
        """Induced partial order: self ≤ other ⟺ self ⊔ other = other."""
        return self.merge(other) == other

    def __eq__(self, other: object) -> bool:
        raise NotImplementedError


def merge(a: T, b: T) -> T:
    """Functional alias for a.merge(b)."""
    return a.merge(b)
