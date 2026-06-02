"""Feature registry: thread-safe store for FeatureSpec objects."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from featstore.types import FeatureSpec


class DuplicateFeatureError(Exception):
    """Raised when registering a feature that already exists."""


class FeatureNotFoundError(KeyError):
    """Raised when a requested feature is not registered."""


class FeatureRegistry:
    """Thread-safe registry of FeatureSpec objects."""

    def __init__(self) -> None:
        self._specs: dict[str, FeatureSpec] = {}
        self._lock = threading.Lock()

    def register(self, spec: FeatureSpec) -> None:
        """Register a feature spec; raises DuplicateFeatureError if already registered."""
        with self._lock:
            if spec.name in self._specs:
                raise DuplicateFeatureError(f"Feature '{spec.name}' is already registered.")
            self._specs[spec.name] = spec

    def get(self, name: str) -> FeatureSpec:
        """Return the spec for *name*; raises FeatureNotFoundError if absent."""
        with self._lock:
            try:
                return self._specs[name]
            except KeyError:
                raise FeatureNotFoundError(f"Feature '{name}' not found in registry.") from None

    def list_features(self) -> list[str]:
        """Return sorted list of all registered feature names."""
        with self._lock:
            return sorted(self._specs.keys())

    def __len__(self) -> int:
        with self._lock:
            return len(self._specs)
