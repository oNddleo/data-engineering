"""Throughput + lag + latency metrics for the streaming engine.

We measure three things during a flash-sale run:

* **Throughput** — events/sec, computed as ``n_events / wall_seconds``.
* **Event-time lag** — ``wall_clock_at_processing − event.created_at``.
  Indicates how far behind real time the pipeline is.
* **Processing latency** — ``wall_clock_after − wall_clock_before``
  per event. Useful for finding slow downstream sinks.

Latency stats are summarised with p50 / p95 / max — production
ships these to Prometheus.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime


@dataclass(frozen=True, slots=True)
class MetricsSnapshot:
    """Immutable snapshot of the engine's metrics."""

    n_events: int
    n_late_events: int
    wall_seconds: float
    throughput_events_per_sec: float
    lag_ms_p50: float
    lag_ms_p95: float
    lag_ms_max: float
    latency_ms_p50: float
    latency_ms_p95: float
    latency_ms_max: float


@dataclass(slots=True)
class MetricsCollector:
    """Accumulate per-event timing samples; emit a snapshot on demand."""

    started_at: float = field(default_factory=time.perf_counter)
    n_events: int = 0
    n_late_events: int = 0
    _lag_samples_ms: list[float] = field(default_factory=list)
    _latency_samples_ms: list[float] = field(default_factory=list)

    def record(
        self,
        *,
        event_time: datetime,
        wall_clock_before: float,
        wall_clock_after: float,
        processed_at_wall: datetime,
    ) -> None:
        self.n_events += 1
        lag_seconds = (processed_at_wall - event_time).total_seconds()
        self._lag_samples_ms.append(lag_seconds * 1000.0)
        self._latency_samples_ms.append((wall_clock_after - wall_clock_before) * 1000.0)

    def mark_late(self) -> None:
        self.n_late_events += 1

    def snapshot(self) -> MetricsSnapshot:
        wall_seconds = max(time.perf_counter() - self.started_at, 1e-9)
        throughput = self.n_events / wall_seconds if self.n_events else 0.0
        return MetricsSnapshot(
            n_events=self.n_events,
            n_late_events=self.n_late_events,
            wall_seconds=wall_seconds,
            throughput_events_per_sec=throughput,
            lag_ms_p50=_percentile(self._lag_samples_ms, 50),
            lag_ms_p95=_percentile(self._lag_samples_ms, 95),
            lag_ms_max=max(self._lag_samples_ms, default=0.0),
            latency_ms_p50=_percentile(self._latency_samples_ms, 50),
            latency_ms_p95=_percentile(self._latency_samples_ms, 95),
            latency_ms_max=max(self._latency_samples_ms, default=0.0),
        )


def _percentile(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    xs_sorted = sorted(xs)
    rank = (len(xs_sorted) - 1) * p / 100
    lo = math.floor(rank)
    hi = math.ceil(rank)
    if lo == hi:
        return xs_sorted[int(rank)]
    weight = rank - lo
    return xs_sorted[lo] * (1 - weight) + xs_sorted[hi] * weight


__all__ = ["MetricsCollector", "MetricsSnapshot"]
