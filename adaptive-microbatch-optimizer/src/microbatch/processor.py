"""MicroBatchProcessor — asyncio-based adaptive batch dispatcher."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

from microbatch.backpressure import BackpressureMonitor
from microbatch.metrics import MetricsCollector
from microbatch.window import AdaptiveWindowManager, SLAConfig

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class ProcessorStats:
    total_events: int = field(default=0)
    total_batches: int = field(default=0)
    dropped_events: int = field(default=0)
    current_window_s: float = field(default=0.5)
    uptime_s: float = field(default=0.0)


class MicroBatchProcessor(Generic[T]):
    """Collects events into micro-batches whose window is adaptively controlled."""

    def __init__(
        self,
        handler: Callable[[list[T]], Awaitable[None]],
        sla: SLAConfig | None = None,
        max_queue_size: int = 10_000,
        initial_window: float = 0.5,
    ) -> None:
        self._handler = handler
        self._queue: asyncio.Queue[T] = asyncio.Queue(maxsize=max_queue_size)
        self.backpressure = BackpressureMonitor()
        self.metrics = MetricsCollector()
        self.window_mgr = AdaptiveWindowManager(
            sla=sla,
            metrics=self.metrics,
            backpressure=self.backpressure,
            initial_window=initial_window,
        )
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._start_time: float = 0.0
        self._stats = ProcessorStats()

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._start_time = time.monotonic()
        self._task = asyncio.create_task(self._dispatch_loop(), name="microbatch-dispatch")

    async def stop(self, drain: bool = True) -> None:
        self._running = False
        if drain:
            await self._flush()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def ingest(self, event: T) -> bool:
        try:
            self._queue.put_nowait(event)
            return True
        except asyncio.QueueFull:
            self._stats.dropped_events += 1
            return False

    async def ingest_many(self, events: list[T]) -> int:
        count = 0
        for e in events:
            if await self.ingest(e):
                count += 1
        return count

    def report_backpressure(self, source: str, level: float) -> None:
        self.backpressure.push(source, level)

    def stats(self) -> ProcessorStats:
        self._stats.current_window_s = self.window_mgr.current_window
        self._stats.uptime_s = time.monotonic() - self._start_time
        return self._stats

    async def _dispatch_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self.window_mgr.current_window)
            await self._flush()

    async def _flush(self) -> None:
        batch: list[T] = []
        while not self._queue.empty():
            try:
                batch.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        if not batch:
            return
        t0 = time.monotonic()
        try:
            await self._handler(batch)
        except Exception:
            logger.exception("Batch handler raised (size=%d)", len(batch))
        elapsed = time.monotonic() - t0
        self._stats.total_events += len(batch)
        self._stats.total_batches += 1
        self.window_mgr.after_batch(len(batch), elapsed)
