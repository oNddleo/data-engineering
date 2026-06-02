"""Synthetic event stream generator.

Two patterns useful for testing windowing semantics:

* ``uniform_stream`` — events at a constant inter-arrival rate
  across ``n_keys`` keys.
* ``bursty_stream`` — events arrive in bursts separated by idle
  periods (the classic session-window stress test).
"""

from __future__ import annotations

import random

from windows.schema import Event


def uniform_stream(
    *,
    n_keys: int = 5,
    n_events_per_key: int = 100,
    interval_ms: int = 1_000,
    base_ts_ms: int = 0,
    seed: int = 0,
) -> list[Event]:
    """``n_keys × n_events_per_key`` events at constant cadence per key."""
    if n_keys < 0 or n_events_per_key < 0:
        raise ValueError("counts must be >= 0")
    if interval_ms <= 0:
        raise ValueError("interval_ms must be > 0")
    rng = random.Random(seed)
    out: list[Event] = []
    for k in range(n_keys):
        key = f"key-{k:04d}"
        for i in range(n_events_per_key):
            out.append(
                Event(
                    key=key,
                    value=rng.randint(1, 1_000),
                    ts_ms=base_ts_ms + i * interval_ms,
                )
            )
    out.sort(key=lambda e: e.ts_ms)
    return out


def bursty_stream(
    *,
    n_keys: int = 3,
    n_bursts: int = 5,
    events_per_burst: int = 20,
    burst_duration_ms: int = 60_000,
    idle_gap_ms: int = 300_000,
    base_ts_ms: int = 0,
    seed: int = 0,
) -> list[Event]:
    """Per-key bursts of activity separated by idle gaps.

    A burst contains ``events_per_burst`` events spread uniformly over
    ``burst_duration_ms``. Idle gaps between bursts are ``idle_gap_ms``.
    """
    if any(v < 0 for v in (n_keys, n_bursts, events_per_burst)):
        raise ValueError("counts must be >= 0")
    if burst_duration_ms <= 0 or idle_gap_ms <= 0:
        raise ValueError("durations must be > 0")
    rng = random.Random(seed)
    out: list[Event] = []
    for k in range(n_keys):
        key = f"key-{k:04d}"
        cursor = base_ts_ms
        for _ in range(n_bursts):
            for i in range(events_per_burst):
                offset = i * burst_duration_ms // max(1, events_per_burst - 1)
                out.append(
                    Event(
                        key=key,
                        value=rng.randint(1, 1_000),
                        ts_ms=cursor + offset,
                    )
                )
            cursor += burst_duration_ms + idle_gap_ms
    out.sort(key=lambda e: e.ts_ms)
    return out


__all__ = ["bursty_stream", "uniform_stream"]
