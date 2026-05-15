"""Output sinks for window aggregates + hotness events.

Production cắm Kafka producer / Redis pub-sub / Postgres COPY at
the same surface. The Sink Protocol is narrow on purpose so swapping
backends doesn't ripple into the pipeline.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from flashpipe.detectors import HotnessEvent
    from flashpipe.windows import WindowAggregate


class WindowSink(Protocol):
    def write(self, aggregate: WindowAggregate) -> None: ...


class HotnessSink(Protocol):
    def write(self, event: HotnessEvent) -> None: ...


class InMemoryWindowSink:
    """Capture aggregates in a list — handy for tests + small batches."""

    def __init__(self) -> None:
        self.received: list[WindowAggregate] = []

    def write(self, aggregate: WindowAggregate) -> None:
        self.received.append(aggregate)

    @property
    def size(self) -> int:
        return len(self.received)


class InMemoryHotnessSink:
    """Capture hotness events in a list — handy for tests."""

    def __init__(self) -> None:
        self.received: list[HotnessEvent] = []

    def write(self, event: HotnessEvent) -> None:
        self.received.append(event)

    @property
    def size(self) -> int:
        return len(self.received)


__all__ = [
    "HotnessSink",
    "InMemoryHotnessSink",
    "InMemoryWindowSink",
    "WindowSink",
]
