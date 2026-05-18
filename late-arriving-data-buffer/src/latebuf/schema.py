"""Event-time + buffer schema.

The buffer accepts ``Event`` records carrying:

* an opaque ``event_id`` (deduplication key),
* an **event-time** ``event_time`` (when the event occurred at source),
* a **processing-time** ``ingest_time`` (when the buffer received it).

The watermark tracks "how far we believe event-time has progressed".
Events arriving with ``event_time < watermark`` are **late** —
either dead-lettered or, if ``allowed_lateness`` permits, included
in a side-output.

Three watermark strategies are supported:

| Strategy        | Watermark behaviour                                                  |
| --------------- | -------------------------------------------------------------------- |
| ``HEURISTIC``   | ``max(event_time_seen) - allowed_lateness`` — Beam/Flink default     |
| ``PERIODIC``    | Advance every ``tick_seconds`` to ``max - allowed_lateness``         |
| ``PUNCTUATED``  | Advance only on arrival of an event whose ``is_punctuation`` is True |
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))


class WatermarkStrategy(str, Enum):
    """Three canonical watermark generation strategies."""

    HEURISTIC = "HEURISTIC"  # max(event_time) - allowed_lateness
    PERIODIC = "PERIODIC"  # advance every tick_seconds
    PUNCTUATED = "PUNCTUATED"  # advance on punctuation events


class EventDisposition(str, Enum):
    """What happened to an event after passing through the buffer."""

    EMITTED = "EMITTED"  # delivered in event-time order
    BUFFERED = "BUFFERED"  # held, awaiting watermark advance
    DEAD_LETTERED = "DEAD_LETTERED"  # arrived after watermark passed → dropped


@dataclass(frozen=True, slots=True)
class Event:
    """One event line. Free-form ``payload`` for application data."""

    event_id: str
    event_time: datetime  # when the event occurred at the source
    ingest_time: datetime  # when the buffer received it
    payload: str = ""  # opaque application data
    is_punctuation: bool = False  # only meaningful for PUNCTUATED strategy

    def __post_init__(self) -> None:
        if not self.event_id:
            raise ValueError("event_id must be non-empty")
        if self.event_time.tzinfo is None:
            raise ValueError("event_time must be timezone-aware")
        if self.ingest_time.tzinfo is None:
            raise ValueError("ingest_time must be timezone-aware")
        if self.ingest_time < self.event_time:
            raise ValueError(
                f"ingest_time {self.ingest_time} before event_time {self.event_time}",
            )


@dataclass(frozen=True, slots=True)
class BufferConfig:
    """Configuration for a ``LateArrivingBuffer``.

    ``allowed_lateness`` is the duration by which the watermark
    trails the max-seen event-time. Larger values reduce
    dead-lettering at the cost of higher emission latency.
    """

    strategy: WatermarkStrategy = WatermarkStrategy.HEURISTIC
    allowed_lateness: timedelta = timedelta(seconds=60)
    periodic_tick: timedelta = timedelta(seconds=5)  # only for PERIODIC

    def __post_init__(self) -> None:
        if self.allowed_lateness < timedelta(0):
            raise ValueError(
                f"allowed_lateness must be >= 0, got {self.allowed_lateness}",
            )
        if self.strategy is WatermarkStrategy.PERIODIC and self.periodic_tick <= timedelta(0):
            raise ValueError(
                f"periodic_tick must be > 0, got {self.periodic_tick}",
            )


@dataclass(frozen=True, slots=True)
class EmittedRecord:
    """One record emitted by the buffer, with its disposition."""

    event: Event
    disposition: EventDisposition
    lateness_seconds: int  # event_time vs the watermark at emit; 0 if EMITTED on time


@dataclass(frozen=True, slots=True)
class BufferStats:
    """End-of-run stats for one buffer instance."""

    n_accepted: int
    n_emitted: int
    n_dead_lettered: int
    n_still_buffered: int  # at end of stream
    max_lateness_seconds: int  # worst observed lateness
    median_lateness_seconds: int  # median for late-only events
    p99_lateness_seconds: int  # 99th percentile for late-only events
    final_watermark: datetime | None = field(default=None)

    @property
    def total(self) -> int:
        """Total events seen, regardless of disposition."""
        return self.n_emitted + self.n_dead_lettered + self.n_still_buffered

    @property
    def drop_rate_pct(self) -> float:
        """Percentage of accepted events that were dead-lettered."""
        if self.n_accepted == 0:
            return 0.0
        return self.n_dead_lettered / self.n_accepted * 100


__all__ = [
    "VN_TZ",
    "BufferConfig",
    "BufferStats",
    "EmittedRecord",
    "Event",
    "EventDisposition",
    "WatermarkStrategy",
]
