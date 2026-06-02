"""Tests for the async MicroBatchProcessor."""

from __future__ import annotations

import asyncio

import pytest

from microbatch.processor import MicroBatchProcessor


@pytest.mark.asyncio
async def test_events_are_processed() -> None:
    received: list[int] = []

    async def handler(batch: list[int]) -> None:
        received.extend(batch)

    proc: MicroBatchProcessor[int] = MicroBatchProcessor(handler=handler, initial_window=0.05)
    await proc.start()
    for i in range(50):
        await proc.ingest(i)
    await asyncio.sleep(0.2)
    await proc.stop(drain=True)
    assert set(received) == set(range(50))


@pytest.mark.asyncio
async def test_dropped_events_counted() -> None:
    async def handler(batch: list[int]) -> None:
        await asyncio.sleep(0.01)

    proc: MicroBatchProcessor[int] = MicroBatchProcessor(
        handler=handler, max_queue_size=5, initial_window=0.5
    )
    await proc.start()
    dropped = 0
    for i in range(200):
        ok = await proc.ingest(i)
        if not ok:
            dropped += 1
    await proc.stop(drain=False)
    assert proc.stats().dropped_events == dropped
    assert dropped > 0


@pytest.mark.asyncio
async def test_ingest_many() -> None:
    received: list[int] = []

    async def handler(batch: list[int]) -> None:
        received.extend(batch)

    proc: MicroBatchProcessor[int] = MicroBatchProcessor(handler=handler, initial_window=0.05)
    await proc.start()
    accepted = await proc.ingest_many(list(range(100)))
    await asyncio.sleep(0.3)
    await proc.stop(drain=True)
    assert accepted == 100
    assert len(received) == 100


@pytest.mark.asyncio
async def test_backpressure_reported() -> None:
    async def handler(batch: list[int]) -> None:
        pass

    proc: MicroBatchProcessor[int] = MicroBatchProcessor(handler=handler, initial_window=0.1)
    await proc.start()
    proc.report_backpressure("sink", 0.9)
    bp = proc.backpressure.current_level()
    assert bp > 0.8
    await proc.stop(drain=False)


@pytest.mark.asyncio
async def test_stats_updated() -> None:
    async def handler(batch: list[int]) -> None:
        pass

    proc: MicroBatchProcessor[int] = MicroBatchProcessor(handler=handler, initial_window=0.05)
    await proc.start()
    for i in range(30):
        await proc.ingest(i)
    await asyncio.sleep(0.3)
    await proc.stop(drain=True)
    stats = proc.stats()
    assert stats.total_events == 30
    assert stats.total_batches >= 1
    assert stats.uptime_s > 0


@pytest.mark.asyncio
async def test_handler_exception_does_not_crash_loop() -> None:
    call_count = [0]

    async def flaky_handler(batch: list[int]) -> None:
        call_count[0] += 1
        if call_count[0] % 2 == 0:
            raise ValueError("intentional error")

    proc: MicroBatchProcessor[int] = MicroBatchProcessor(
        handler=flaky_handler, initial_window=0.05
    )
    await proc.start()
    for i in range(10):
        await proc.ingest(i)
        await asyncio.sleep(0.06)
    await proc.stop(drain=True)
    assert call_count[0] >= 2
