"""Core type definitions for the streaming feature store."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from datetime import datetime

DType = Literal["float", "int", "str"]


@dataclass(frozen=True)
class FeatureSpec:
    """Specification for a single feature."""

    name: str
    dtype: DType
    transform: str = "identity"
    description: str = ""


@dataclass
class FeatureValue:
    """A single feature value at a point in time."""

    feature_name: str
    value: float | int | str | None
    timestamp: datetime


@dataclass
class FeatureVector:
    """A collection of feature values for one entity at a point in time."""

    entity_id: str
    as_of_ts: datetime
    features: dict[str, float | int | str | None] = field(default_factory=dict)


EntityKey = tuple[str, str]  # (entity_id, feature_name)
