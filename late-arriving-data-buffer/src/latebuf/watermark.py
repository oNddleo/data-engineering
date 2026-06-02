"""Watermark generators — three canonical strategies.

Each generator implements a single ``update(event) -> datetime | None``
contract: feed it events as they arrive, and it returns the **new
watermark** if it should advance (or ``None`` if not).

Strategies:

* **Heuristic** — advance to ``max(event_time_seen) - allowed_lateness``
  on every event. This is the Beam / Flink "bounded out-of-orderness"
  default. Cheap, never reports a stale watermark, but reacts fast.
* **Periodic** — accumulate max(event_time) silently; only advance
  the watermark when ``processing_time - last_tick >= tick`` has
  elapsed. Useful for systems where downstream prefers fewer, larger
  watermark steps.
* **Punctuated** — only advance when the incoming event has
  ``is_punctuation=True``. Useful when the source emits END_OF_BATCH
  markers (e.g. file rolls, CDC commit boundaries).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from latebuf.schema import BufferConfig, WatermarkStrategy

if TYPE_CHECKING:
    from datetime import datetime

    from latebuf.schema import Event


@dataclass(slots=True)
class WatermarkState:
    """Mutable state for one watermark generator."""

    config: BufferConfig
    max_event_time: datetime | None = None
    current: datetime | None = None
    last_tick: datetime | None = None  # processing-time of last PERIODIC tick
    pending_advance: datetime | None = field(default=None)

    def update(self, event: Event) -> datetime | None:
        """Process one event; return the new watermark, or ``None``.

        ``None`` means "no change" — callers should treat the
        previous ``current`` as authoritative.
        """
        if self.max_event_time is None or event.event_time > self.max_event_time:
            self.max_event_time = event.event_time
        target = self.max_event_time - self.config.allowed_lateness

        strategy = self.config.strategy
        if strategy is WatermarkStrategy.HEURISTIC:
            return self._advance_to(target)
        if strategy is WatermarkStrategy.PERIODIC:
            return self._periodic_tick(event.ingest_time, target)
        if strategy is WatermarkStrategy.PUNCTUATED:
            if event.is_punctuation:
                return self._advance_to(target)
            return None
        raise ValueError(f"unknown strategy: {strategy}")

    def _advance_to(self, target: datetime) -> datetime | None:
        """Advance watermark to ``target`` if it's a strict increase."""
        if self.current is None or target > self.current:
            self.current = target
            return target
        return None

    def _periodic_tick(
        self,
        ingest_time: datetime,
        target: datetime,
    ) -> datetime | None:
        """Tick-driven advance: emit only every ``periodic_tick`` interval."""
        if self.last_tick is None:
            self.last_tick = ingest_time
            return self._advance_to(target)
        if ingest_time - self.last_tick >= self.config.periodic_tick:
            self.last_tick = ingest_time
            return self._advance_to(target)
        return None

    def finalise(self) -> datetime | None:
        """Force-advance the watermark to ``max(event_time) - allowed_lateness``.

        Called at end-of-stream so any remaining buffered events
        get flushed deterministically.
        """
        if self.max_event_time is None:
            return self.current
        target = self.max_event_time - self.config.allowed_lateness
        if self.current is None or target > self.current:
            self.current = target
        return self.current

    def get(self) -> datetime | None:
        """The current watermark, or ``None`` if no event has been seen."""
        return self.current


def new_watermark(config: BufferConfig | None = None) -> WatermarkState:
    """Construct a fresh watermark state with the given config."""
    return WatermarkState(config=config or BufferConfig())


__all__ = ["WatermarkState", "new_watermark"]
