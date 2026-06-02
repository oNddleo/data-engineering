"""Time-series observation store, keyed by (sku, platform)."""

from __future__ import annotations

import bisect
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime

    from multiprice.schema import Platform, ProductObservation


class ObservationStore:
    """Per-(SKU, platform) time-sorted observation series.

    Inserts go through :meth:`append`, which keeps each per-key
    list sorted by ``observed_at``. Reads are O(log n) via bisect.
    """

    def __init__(self) -> None:
        self._series: dict[tuple[str, Platform], list[ProductObservation]] = {}

    def __len__(self) -> int:
        return sum(len(v) for v in self._series.values())

    @property
    def n_series(self) -> int:
        return len(self._series)

    def append(self, obs: ProductObservation) -> None:
        key = (obs.canonical_sku, obs.platform)
        s = self._series.setdefault(key, [])
        times = [o.observed_at for o in s]
        idx = bisect.bisect_left(times, obs.observed_at)
        s.insert(idx, obs)

    def append_many(self, observations: Iterable[ProductObservation]) -> None:
        for o in observations:
            self.append(o)

    def latest(self, canonical_sku: str, platform: Platform) -> ProductObservation | None:
        s = self._series.get((canonical_sku, platform))
        return s[-1] if s else None

    def all_latest_for_sku(self, canonical_sku: str) -> dict[Platform, ProductObservation]:
        """Latest observation for each platform that has data for this SKU."""
        out: dict[Platform, ProductObservation] = {}
        for (sku, plat), series in self._series.items():
            if sku == canonical_sku and series:
                out[plat] = series[-1]
        return out

    def history(
        self,
        canonical_sku: str,
        platform: Platform,
        *,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[ProductObservation]:
        s = self._series.get((canonical_sku, platform), [])
        if since is None and until is None:
            return list(s)
        lo = 0
        hi = len(s)
        if since is not None:
            lo = bisect.bisect_left([o.observed_at for o in s], since)
        if until is not None:
            hi = bisect.bisect_right([o.observed_at for o in s], until)
        return s[lo:hi]

    def all_skus(self) -> set[str]:
        return {sku for (sku, _) in self._series}


__all__ = ["ObservationStore"]
