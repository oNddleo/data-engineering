"""Synthetic request stream generators for rate-limiter benchmarks."""

from __future__ import annotations

import random


def constant_rate(
    *,
    n_keys: int = 3,
    n_requests: int = 100,
    interval_ms: int = 100,
    base_ts_ms: int = 0,
    seed: int = 0,
) -> list[tuple[str, int]]:
    """Steady, evenly-spaced per-key request stream.

    Returns a list of ``(key, ts_ms)`` tuples sorted by ts_ms.
    """
    if n_keys < 1 or n_requests < 0 or interval_ms < 1:
        raise ValueError("invalid parameters")
    rng = random.Random(seed)
    out: list[tuple[str, int]] = []
    for k in range(n_keys):
        key = f"key-{k:03d}"
        for i in range(n_requests):
            out.append((key, base_ts_ms + i * interval_ms))
        # Tiny shuffle of starting offset across keys.
        rng.random()
    out.sort(key=lambda x: x[1])
    return out


def burst_then_idle(
    *,
    n_keys: int = 2,
    n_bursts: int = 5,
    burst_size: int = 20,
    burst_duration_ms: int = 100,
    idle_gap_ms: int = 5_000,
    base_ts_ms: int = 0,
    seed: int = 0,
) -> list[tuple[str, int]]:
    """Per-key bursts of ``burst_size`` requests in ``burst_duration_ms``."""
    _ = random.Random(seed)
    if n_keys < 1 or n_bursts < 0:
        raise ValueError("invalid parameters")
    if burst_duration_ms <= 0 or idle_gap_ms <= 0 or burst_size < 1:
        raise ValueError("invalid parameters")
    out: list[tuple[str, int]] = []
    for k in range(n_keys):
        key = f"key-{k:03d}"
        cursor = base_ts_ms
        for _ in range(n_bursts):
            for i in range(burst_size):
                offset = i * burst_duration_ms // max(1, burst_size - 1)
                out.append((key, cursor + offset))
            cursor += burst_duration_ms + idle_gap_ms
    out.sort(key=lambda x: x[1])
    return out


__all__ = ["burst_then_idle", "constant_rate"]
