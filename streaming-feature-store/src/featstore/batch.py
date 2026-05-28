"""Batch processor: read JSONL records, apply transforms, write output JSONL."""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from featstore.registry import FeatureRegistry
from featstore.transforms import FeatureTransform, IdentityTransform, get_transform

_NUM_BUCKETS = 20


@dataclass
class DistributionStats:
    """Descriptive statistics + histogram for a feature distribution."""

    feature_name: str
    count: int = 0
    mean: float = 0.0
    std: float = 0.0
    min_val: float = math.inf
    max_val: float = -math.inf
    # Histogram: list of (lower_bound, upper_bound, count) tuples
    histogram: list[tuple[float, float, int]] = field(default_factory=list)

    # Welford accumulators (not serialised)
    _m2: float = field(default=0.0, repr=False)

    def update(self, x: float) -> None:
        """Welford online update."""
        self.count += 1
        delta = x - self.mean
        self.mean += delta / self.count
        delta2 = x - self.mean
        self._m2 += delta * delta2
        if x < self.min_val:
            self.min_val = x
        if x > self.max_val:
            self.max_val = x

    def finalise(self, values: list[float]) -> None:
        """Build histogram from collected values after all updates."""
        if self.count < 2:
            self.std = 0.0
        else:
            self.std = math.sqrt(self._m2 / (self.count - 1))
        if not values:
            return
        lo = min(values)
        hi = max(values)
        if lo == hi:
            width = 1.0
        else:
            width = (hi - lo) / _NUM_BUCKETS
        buckets: list[int] = [0] * _NUM_BUCKETS
        for v in values:
            idx = int((v - lo) / width)
            if idx >= _NUM_BUCKETS:
                idx = _NUM_BUCKETS - 1
            buckets[idx] += 1
        self.histogram = [
            (lo + i * width, lo + (i + 1) * width, buckets[i]) for i in range(_NUM_BUCKETS)
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "count": self.count,
            "mean": self.mean,
            "std": self.std,
            "min_val": self.min_val,
            "max_val": self.max_val,
            "histogram": self.histogram,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> DistributionStats:
        ds = cls(feature_name=d["feature_name"])
        ds.count = d.get("count", 0)
        ds.mean = d.get("mean", 0.0)
        ds.std = d.get("std", 0.0)
        ds.min_val = d.get("min_val", math.inf)
        ds.max_val = d.get("max_val", -math.inf)
        raw_hist = d.get("histogram", [])
        ds.histogram = [(float(r[0]), float(r[1]), int(r[2])) for r in raw_hist]
        return ds


class BatchProcessor:
    """Process historical JSONL records, apply transforms, compute distribution stats."""

    def __init__(
        self,
        registry: FeatureRegistry,
        transforms: dict[str, FeatureTransform] | None = None,
    ) -> None:
        self._registry = registry
        self._transforms: dict[str, FeatureTransform] = transforms or {}

    def _get_transform(self, feature_name: str) -> FeatureTransform:
        if feature_name in self._transforms:
            return self._transforms[feature_name]
        try:
            spec = self._registry.get(feature_name)
            return get_transform(spec.transform)
        except Exception:
            return IdentityTransform()

    def process(
        self,
        input_path: Path,
        output_path: Path,
        feature_cols: list[str],
        entity_col: str = "entity_id",
        ts_col: str = "ts",
    ) -> dict[str, DistributionStats]:
        """Read *input_path* (JSONL), apply transforms, write to *output_path*.

        Returns per-feature DistributionStats.
        """
        stats: dict[str, DistributionStats] = {f: DistributionStats(f) for f in feature_cols}
        raw_values: dict[str, list[float]] = {f: [] for f in feature_cols}
        transforms = {f: self._get_transform(f) for f in feature_cols}

        records: list[dict[str, Any]] = []
        with input_path.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                rec: dict[str, Any] = json.loads(line)
                out: dict[str, Any] = {
                    entity_col: rec.get(entity_col, ""),
                    ts_col: rec.get(ts_col, ""),
                }
                for feat in feature_cols:
                    raw = rec.get(feat)
                    if raw is None:
                        out[feat] = None
                        continue
                    fval = float(raw)
                    transformed = transforms[feat].apply(fval)
                    out[feat] = transformed
                    if not math.isnan(transformed):
                        stats[feat].update(transformed)
                        raw_values[feat].append(transformed)
                records.append(out)

        # Finalise stats (histogram)
        for feat in feature_cols:
            stats[feat].finalise(raw_values[feat])

        with output_path.open("w") as fh:
            for rec in records:
                fh.write(json.dumps(rec) + "\n")

        return stats

    def write_stats(self, stats: dict[str, DistributionStats], path: Path) -> None:
        """Serialize stats to JSONL."""
        with path.open("w") as fh:
            for ds in stats.values():
                fh.write(json.dumps(ds.to_dict()) + "\n")

    def load_stats(self, path: Path) -> dict[str, DistributionStats]:
        """Load stats from JSONL written by write_stats."""
        result: dict[str, DistributionStats] = {}
        with path.open() as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                d: dict[str, Any] = json.loads(line)
                ds = DistributionStats.from_dict(d)
                result[ds.feature_name] = ds
        return result
