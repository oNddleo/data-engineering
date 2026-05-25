"""Rolling-window metrics collector for throughput and latency."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from statistics import mean, quantiles


@dataclass
class BatchMetric:
    timestamp: float
    batch_size: int
    processing_time_s: float
    window_size_s: float


@dataclass
class LatencySnapshot:
    p50: float
    p95: float
    p99: float
    mean: float


@dataclass
class ThroughputSnapshot:
    events_per_second: float
    batches_per_second: float


class MetricsCollector:
    """Keeps a rolling window of batch metrics and exposes aggregated stats."""

    def __init__(self, window_seconds: float = 10.0) -> None:
        self.window_seconds = window_seconds
        self._records: deque[BatchMetric] = deque()

    def record(self, batch_size: int, processing_time_s: float, window_size_s: float) -> None:
        self._records.append(
            BatchMetric(
                timestamp=time.monotonic(),
                batch_size=batch_size,
                processing_time_s=processing_time_s,
                window_size_s=window_size_s,
            )
        )
        self._evict()

    def latency_snapshot(self) -> LatencySnapshot | None:
        self._evict()
        if not self._records:
            return None
        times = [r.processing_time_s for r in self._records]
        if len(times) < 2:
            return LatencySnapshot(p50=times[0], p95=times[0], p99=times[0], mean=times[0])
        qs = quantiles(times, n=100)
        return LatencySnapshot(p50=qs[49], p95=qs[94], p99=qs[98], mean=mean(times))

    def throughput_snapshot(self) -> ThroughputSnapshot | None:
        self._evict()
        if len(self._records) < 2:
            return None
        elapsed = self._records[-1].timestamp - self._records[0].timestamp
        if elapsed <= 0:
            return None
        total = sum(r.batch_size for r in self._records)
        return ThroughputSnapshot(
            events_per_second=total / elapsed,
            batches_per_second=len(self._records) / elapsed,
        )

    def recent_latencies(self, n: int = 20) -> list[float]:
        self._evict()
        return [r.processing_time_s for r in list(self._records)[-n:]]

    def _evict(self) -> None:
        cutoff = time.monotonic() - self.window_seconds
        while self._records and self._records[0].timestamp < cutoff:
            self._records.popleft()
