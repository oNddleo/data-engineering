"""Tests for InMemoryBus pub/sub."""

from __future__ import annotations

import pytest

from mesh.bus import InMemoryBus
from mesh.metrics import BackpressureLevel, BackpressureSignal, ThrottleCommand


@pytest.mark.asyncio
async def test_signal_delivered_to_subscriber() -> None:
    bus = InMemoryBus()
    received: list[BackpressureSignal] = []

    async def on_signal(sig: BackpressureSignal) -> None:
        received.append(sig)

    await bus.subscribe_signals(on_signal)
    sig = BackpressureSignal("job-1", BackpressureLevel.HIGH, 0.8)
    await bus.publish_signal(sig)

    assert len(received) == 1
    assert received[0].source_job_id == "job-1"
    await bus.close()


@pytest.mark.asyncio
async def test_throttle_delivered_to_correct_job() -> None:
    bus = InMemoryBus()
    received_a: list[ThrottleCommand] = []
    received_b: list[ThrottleCommand] = []

    async def on_throttle_a(cmd: ThrottleCommand) -> None:
        received_a.append(cmd)

    async def on_throttle_b(cmd: ThrottleCommand) -> None:
        received_b.append(cmd)

    await bus.subscribe_throttle("job-a", on_throttle_a)
    await bus.subscribe_throttle("job-b", on_throttle_b)

    cmd = ThrottleCommand("job-a", 0.5, reason="test")
    await bus.publish_throttle(cmd)

    assert len(received_a) == 1
    assert len(received_b) == 0
    await bus.close()


@pytest.mark.asyncio
async def test_multiple_subscribers_all_receive() -> None:
    bus = InMemoryBus()
    bucket: list[BackpressureSignal] = []

    for _ in range(3):

        async def handler(sig: BackpressureSignal, b: list[BackpressureSignal] = bucket) -> None:
            b.append(sig)

        await bus.subscribe_signals(handler)

    await bus.publish_signal(BackpressureSignal("job-x", BackpressureLevel.LOW, 0.2))
    assert len(bucket) == 3
    await bus.close()


@pytest.mark.asyncio
async def test_throttle_not_delivered_to_wrong_job() -> None:
    bus = InMemoryBus()
    received: list[ThrottleCommand] = []

    async def capture(cmd: ThrottleCommand) -> None:
        received.append(cmd)

    await bus.subscribe_throttle("job-a", capture)
    cmd = ThrottleCommand("job-b", 0.5, reason="test")
    await bus.publish_throttle(cmd)

    assert received == []
    await bus.close()


@pytest.mark.asyncio
async def test_publish_signal_no_subscribers_does_not_crash() -> None:
    bus = InMemoryBus()
    sig = BackpressureSignal("job-1", BackpressureLevel.LOW, 0.1)
    await bus.publish_signal(sig)  # should not raise
    await bus.close()
