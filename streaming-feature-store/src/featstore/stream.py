"""Stream processor: process events one-by-one using Welford's online algorithm."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from featstore.registry import FeatureRegistry
from featstore.store import FeatureStore
from featstore.transforms import FeatureTransform, IdentityTransform, get_transform


@dataclass
class RunningStats:
    """Welford running statistics for a single feature stream."""

    feature_name: str
    count: int = 0
    mean: float = 0.0
    _m2: float = field(default=0.0, repr=False)

    def update(self, x: float) -> None:
        """Update running mean and variance with new observation *x*."""
        self.count += 1
        delta = x - self.mean
        self.mean += delta / self.count
        delta2 = x - self.mean
        self._m2 += delta * delta2

    @property
    def variance(self) -> float:
        if self.count < 2:
            return 0.0
        return self._m2 / (self.count - 1)

    @property
    def std(self) -> float:
        return math.sqrt(self.variance)

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "count": self.count,
            "mean": self.mean,
            "std": self.std,
        }


class StreamProcessor:
    """Process a stream of events, update online store, and track rolling stats."""

    def __init__(
        self,
        registry: FeatureRegistry,
        store: FeatureStore,
        transforms: dict[str, FeatureTransform] | None = None,
    ) -> None:
        self._registry = registry
        self._store = store
        self._transforms: dict[str, FeatureTransform] = transforms or {}
        self._stats: dict[str, RunningStats] = {}

    def _get_transform(self, feature_name: str) -> FeatureTransform:
        if feature_name in self._transforms:
            return self._transforms[feature_name]
        try:
            spec = self._registry.get(feature_name)
            return get_transform(spec.transform)
        except Exception:
            return IdentityTransform()

    def process_event(
        self,
        entity_id: str,
        feature_name: str,
        raw_value: float,
        ts: datetime,
    ) -> float:
        """Process one event: transform, store, update stats; return transformed value."""
        transform = self._get_transform(feature_name)
        transformed = transform.apply(raw_value)

        self._store.put(entity_id, feature_name, transformed, ts)

        if feature_name not in self._stats:
            self._stats[feature_name] = RunningStats(feature_name)
        if not math.isnan(transformed):
            self._stats[feature_name].update(transformed)

        return transformed

    def get_stats(self, feature_name: str) -> RunningStats | None:
        """Return running stats for *feature_name*, or None if no data."""
        return self._stats.get(feature_name)

    def all_stats(self) -> dict[str, RunningStats]:
        """Return all running stats keyed by feature name."""
        return dict(self._stats)
