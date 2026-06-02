"""Feature transform hierarchy."""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from collections import deque
from typing import Any


class FeatureTransform(ABC):
    """Abstract base class for feature transforms."""

    @abstractmethod
    def apply(self, value: float) -> float:
        """Apply the transform to *value* and return the result."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Canonical name used in FeatureSpec."""


class IdentityTransform(FeatureTransform):
    """Pass-through transform."""

    @property
    def name(self) -> str:
        return "identity"

    def apply(self, value: float) -> float:
        return value


class ZScoreTransform(FeatureTransform):
    """Standardize: (x - mean) / std.

    If *std* is 0 the transform returns 0 for all inputs (avoids division by zero).
    """

    def __init__(self, mean: float, std: float) -> None:
        self._mean = mean
        self._std = std

    @property
    def name(self) -> str:
        return "zscore"

    @property
    def mean(self) -> float:
        return self._mean

    @property
    def std(self) -> float:
        return self._std

    def apply(self, value: float) -> float:
        if self._std == 0.0:
            return 0.0
        return (value - self._mean) / self._std

    def inverse(self, z: float) -> float:
        """Reverse the z-score transform."""
        return z * self._std + self._mean


class Log1pTransform(FeatureTransform):
    """Natural log(1 + x) transform."""

    @property
    def name(self) -> str:
        return "log1p"

    def apply(self, value: float) -> float:
        return math.log1p(value)


class BucketizeTransform(FeatureTransform):
    """Map a continuous value to a bucket index given sorted boundary thresholds.

    Bucket 0 → value < boundaries[0]
    Bucket k → boundaries[k-1] <= value < boundaries[k]
    Bucket n → value >= boundaries[-1]
    """

    def __init__(self, boundaries: list[float]) -> None:
        self._boundaries = sorted(boundaries)

    @property
    def name(self) -> str:
        return "bucketize"

    @property
    def boundaries(self) -> list[float]:
        return list(self._boundaries)

    def apply(self, value: float) -> float:
        for i, b in enumerate(self._boundaries):
            if value < b:
                return float(i)
        return float(len(self._boundaries))


class LagTransform(FeatureTransform):
    """Return the value from *n* steps ago using an internal ring buffer.

    The buffer is per-instance, so each entity should have its own LagTransform.
    Returns ``math.nan`` when the buffer has fewer than *n+1* entries.
    """

    def __init__(self, n: int) -> None:
        if n < 1:
            raise ValueError("n must be >= 1")
        self._n = n
        self._buffer: deque[float] = deque(maxlen=n + 1)

    @property
    def name(self) -> str:
        return "lag"

    @property
    def n(self) -> int:
        return self._n

    def apply(self, value: float) -> float:
        """Append *value* to buffer and return the value from *n* steps ago."""
        self._buffer.append(value)
        if len(self._buffer) < self._n + 1:
            return math.nan
        return self._buffer[0]

    def reset(self) -> None:
        """Clear the internal buffer."""
        self._buffer.clear()


# Registry of transform names → factory callables
_TRANSFORM_REGISTRY: dict[str, Any] = {
    "identity": IdentityTransform,
    "log1p": Log1pTransform,
}


def get_transform(name: str, **kwargs: Any) -> FeatureTransform:
    """Look up and instantiate a transform by name."""
    if name == "zscore":
        return ZScoreTransform(mean=kwargs.get("mean", 0.0), std=kwargs.get("std", 1.0))
    if name == "bucketize":
        return BucketizeTransform(boundaries=kwargs.get("boundaries", []))
    if name == "lag":
        return LagTransform(n=kwargs.get("n", 1))
    if name in _TRANSFORM_REGISTRY:
        return _TRANSFORM_REGISTRY[name]()  # type: ignore[no-any-return]
    raise ValueError(f"Unknown transform: '{name}'")
