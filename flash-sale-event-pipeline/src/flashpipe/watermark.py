"""Watermark tracker for out-of-order event streams.

Watermark semantics (Flink-style):

    watermark(t) = max(event_time observed so far) − max_out_of_orderness

Any event whose ``created_at < watermark`` is **late** — the
pipeline has decided that windows ending before this watermark
are sealed and downstream sinks already saw aggregates for them.
Late events are surfaced via :meth:`WatermarkTracker.is_late` so
callers can route them to a side output.

Watermark advances monotonically — once it's at ``W`` it never
goes backwards even if a much earlier event arrives.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


class WatermarkTracker:
    """Track the current watermark over a stream of event timestamps."""

    def __init__(self, *, max_out_of_orderness_seconds: float = 5.0) -> None:
        if max_out_of_orderness_seconds < 0:
            raise ValueError("max_out_of_orderness_seconds must be >= 0")
        self._max_oo = timedelta(seconds=max_out_of_orderness_seconds)
        self._max_observed: datetime | None = None
        self._watermark: datetime | None = None

    @property
    def watermark(self) -> datetime | None:
        return self._watermark

    @property
    def max_observed(self) -> datetime | None:
        return self._max_observed

    def observe(self, event_time: datetime) -> None:
        """Update the watermark based on a newly-observed event time."""
        if self._max_observed is None or event_time > self._max_observed:
            self._max_observed = event_time
            candidate = event_time - self._max_oo
            # Monotonic: never move backwards.
            if self._watermark is None or candidate > self._watermark:
                self._watermark = candidate

    def is_late(self, event_time: datetime) -> bool:
        """Return True iff the event is past the current watermark."""
        if self._watermark is None:
            return False
        return event_time < self._watermark


__all__ = ["WatermarkTracker"]
