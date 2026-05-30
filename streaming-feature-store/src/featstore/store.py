"""Online feature store with point-in-time correct lookups."""

from __future__ import annotations

import bisect
import threading
from typing import TYPE_CHECKING

from featstore.types import EntityKey, FeatureVector

if TYPE_CHECKING:
    from datetime import datetime


class FeatureStore:
    """In-memory online feature store.

    Stores a time-ordered list of ``(timestamp, value)`` pairs per
    ``(entity_id, feature_name)`` key.  All public methods are thread-safe.
    """

    def __init__(self) -> None:
        # Each key maps to a parallel pair of sorted lists for binary-search
        # efficiency: _ts_index[key] and _val_index[key].
        self._ts_index: dict[EntityKey, list[datetime]] = {}
        self._val_index: dict[EntityKey, list[float | int | str | None]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def put(
        self,
        entity: str,
        feature: str,
        value: float | int | str | None,
        ts: datetime,
    ) -> None:
        """Insert a (ts, value) observation."""
        key: EntityKey = (entity, feature)
        with self._lock:
            if key not in self._ts_index:
                self._ts_index[key] = []
                self._val_index[key] = []
            ts_list = self._ts_index[key]
            val_list = self._val_index[key]
            # Maintain sorted order by timestamp (insertions are usually appends).
            pos = bisect.bisect_right(ts_list, ts)
            ts_list.insert(pos, ts)
            val_list.insert(pos, value)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(
        self,
        entity: str,
        feature: str,
        as_of_ts: datetime | None = None,
    ) -> float | int | str | None:
        """Return the latest value <= as_of_ts (or the latest overall if None)."""
        key: EntityKey = (entity, feature)
        with self._lock:
            if key not in self._ts_index:
                return None
            ts_list = self._ts_index[key]
            val_list = self._val_index[key]
            if not ts_list:
                return None
            if as_of_ts is None:
                return val_list[-1]
            # Find rightmost position where ts <= as_of_ts
            pos = bisect.bisect_right(ts_list, as_of_ts)
            if pos == 0:
                return None
            return val_list[pos - 1]

    def get_vector(
        self,
        entity: str,
        features: list[str],
        as_of_ts: datetime,
    ) -> FeatureVector:
        """Return a FeatureVector for *entity* across *features* at *as_of_ts*."""
        fv = FeatureVector(entity_id=entity, as_of_ts=as_of_ts)
        for feat in features:
            fv.features[feat] = self.get(entity, feat, as_of_ts=as_of_ts)
        return fv

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def entity_count(self) -> int:
        """Number of distinct entities tracked."""
        with self._lock:
            return len({k[0] for k in self._ts_index})

    def feature_count(self) -> int:
        """Number of distinct (entity, feature) pairs tracked."""
        with self._lock:
            return len(self._ts_index)
