"""featstore — stdlib-only streaming feature store."""
from __future__ import annotations

from featstore.batch import BatchProcessor, DistributionStats
from featstore.registry import (
    DuplicateFeatureError,
    FeatureNotFoundError,
    FeatureRegistry,
)
from featstore.skew import SkewAlert, SkewDetector, SkewReport
from featstore.store import FeatureStore
from featstore.stream import RunningStats, StreamProcessor
from featstore.transforms import (
    BucketizeTransform,
    FeatureTransform,
    IdentityTransform,
    LagTransform,
    Log1pTransform,
    ZScoreTransform,
    get_transform,
)
from featstore.types import EntityKey, FeatureSpec, FeatureValue, FeatureVector

__all__ = [
    "BatchProcessor",
    "BucketizeTransform",
    "DistributionStats",
    "DuplicateFeatureError",
    "EntityKey",
    "FeatureNotFoundError",
    "FeatureRegistry",
    "FeatureSpec",
    "FeatureStore",
    "FeatureTransform",
    "FeatureValue",
    "FeatureVector",
    "IdentityTransform",
    "LagTransform",
    "Log1pTransform",
    "RunningStats",
    "SkewAlert",
    "SkewDetector",
    "SkewReport",
    "StreamProcessor",
    "ZScoreTransform",
    "get_transform",
]
