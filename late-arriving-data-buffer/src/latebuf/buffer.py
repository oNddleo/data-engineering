"""The core ``LateArrivingBuffer`` — accept events, advance watermark,
emit in event-time order, dead-letter late arrivals.

The contract:

1. ``accept(event)`` — feed in a new event. Returns the disposition
   plus any records emitted as a side-effect of the watermark
   advancing past their event-times.
2. ``flush()`` — at end-of-stream, force-advance the watermark and
   emit everything left in the buffer.

Internally we maintain a **min-heap** keyed by event-time so the
next-to-emit event is always at the heap root. When the watermark
advances past an event's event-time, that event is popped and
appended to the emit queue.

Late events (``event_time < watermark`` at arrival) are dead-lettered
immediately without entering the heap.

Duplicate ``event_id`` events are also dropped (idempotency).
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from latebuf.schema import (
    BufferConfig,
    EmittedRecord,
    EventDisposition,
)
from latebuf.watermark import new_watermark

if TYPE_CHECKING:
    from datetime import datetime

    from latebuf.schema import Event
    from latebuf.watermark import WatermarkState


@dataclass
class _HeapEntry:
    """Wrapper to make ``Event`` heap-orderable by event-time + event-id."""

    event_time: datetime
    event_id: str  # tie-breaker for deterministic ordering
    event: Event

    def __lt__(self, other: _HeapEntry) -> bool:
        if self.event_time != other.event_time:
            return self.event_time < other.event_time
        return self.event_id < other.event_id


@dataclass
class LateArrivingBuffer:
    """Buffer events, emit in event-time order, dead-letter late arrivals."""

    config: BufferConfig = field(default_factory=BufferConfig)
    _heap: list[_HeapEntry] = field(default_factory=list, init=False)
    _seen_ids: set[str] = field(default_factory=set, init=False)
    _watermark: WatermarkState = field(init=False)
    _accepted: int = field(default=0, init=False)
    _emitted: int = field(default=0, init=False)
    _dead_lettered: int = field(default=0, init=False)
    _lateness_observed: list[int] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._watermark = new_watermark(self.config)

    def accept(self, event: Event) -> list[EmittedRecord]:
        """Accept one event; return the disposition + any side-effect emits."""
        out: list[EmittedRecord] = []
        # Idempotency: drop duplicates.
        if event.event_id in self._seen_ids:
            return out
        self._seen_ids.add(event.event_id)
        self._accepted += 1

        # Determine lateness *against the current watermark*.
        current_wm = self._watermark.get()
        if current_wm is not None and event.event_time < current_wm:
            # Late on arrival → dead-letter immediately.
            lateness = int((current_wm - event.event_time).total_seconds())
            self._dead_lettered += 1
            self._lateness_observed.append(lateness)
            out.append(
                EmittedRecord(
                    event=event,
                    disposition=EventDisposition.DEAD_LETTERED,
                    lateness_seconds=lateness,
                )
            )
            return out

        # Push into the heap.
        heapq.heappush(
            self._heap,
            _HeapEntry(
                event_time=event.event_time,
                event_id=event.event_id,
                event=event,
            ),
        )

        # Advance watermark + drain anything below it.
        new_wm = self._watermark.update(event)
        if new_wm is not None:
            out.extend(self._drain_below(new_wm))
        return out

    def flush(self) -> list[EmittedRecord]:
        """End-of-stream: force-advance the watermark + drain everything."""
        final_wm = self._watermark.finalise()
        if final_wm is None:
            return []
        # Drain everything, even the last events, regardless of watermark.
        out: list[EmittedRecord] = []
        out.extend(self._drain_below(final_wm))
        # Anything still in the heap is at event_time > final_wm — emit
        # them at the trailing edge for deterministic final state.
        while self._heap:
            entry = heapq.heappop(self._heap)
            self._emitted += 1
            out.append(
                EmittedRecord(
                    event=entry.event,
                    disposition=EventDisposition.EMITTED,
                    lateness_seconds=0,
                )
            )
        return out

    def _drain_below(self, watermark: datetime) -> list[EmittedRecord]:
        """Pop everything from the heap with event_time <= watermark."""
        out: list[EmittedRecord] = []
        while self._heap and self._heap[0].event_time <= watermark:
            entry = heapq.heappop(self._heap)
            self._emitted += 1
            out.append(
                EmittedRecord(
                    event=entry.event,
                    disposition=EventDisposition.EMITTED,
                    lateness_seconds=0,
                )
            )
        return out

    # ---------- introspection ------------------------------------------------

    @property
    def n_accepted(self) -> int:
        return self._accepted

    @property
    def n_emitted(self) -> int:
        return self._emitted

    @property
    def n_dead_lettered(self) -> int:
        return self._dead_lettered

    @property
    def n_buffered(self) -> int:
        return len(self._heap)

    @property
    def current_watermark(self) -> datetime | None:
        return self._watermark.get()

    @property
    def lateness_observed(self) -> list[int]:
        """Lateness (seconds) for each dead-lettered event so far."""
        return list(self._lateness_observed)


__all__ = ["LateArrivingBuffer"]
