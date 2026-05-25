"""Adaptive window manager — integrates PID, backpressure, and SLA targets."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from microbatch.backpressure import BackpressureMonitor
from microbatch.metrics import MetricsCollector
from microbatch.pid import PIDConfig, PIDController

logger = logging.getLogger(__name__)


@dataclass
class SLAConfig:
    target_latency_s: float = 0.2
    min_throughput_eps: float = 100.0
    backpressure_weight: float = 0.5


@dataclass
class WindowSnapshot:
    window_size_s: float
    pid_error: float
    backpressure_level: float
    p95_latency: float | None
    throughput_eps: float | None
    timestamp: float


class AdaptiveWindowManager:
    """Owns the current window size and updates it after each batch.

    Error composition::

        latency_error  = (p95 - target) / target   ∈ ℝ
        pressure_error = backpressure_level         ∈ [0,1]
        combined       = latency_error + w * pressure_error  (clamped [-1,1])
    """

    MIN_WINDOW: float = 0.05
    MAX_WINDOW: float = 5.0

    def __init__(
        self,
        sla: SLAConfig | None = None,
        pid_config: PIDConfig | None = None,
        metrics: MetricsCollector | None = None,
        backpressure: BackpressureMonitor | None = None,
        initial_window: float = 0.5,
    ) -> None:
        self.sla = sla or SLAConfig()
        self.pid = PIDController(pid_config)
        self.metrics = metrics or MetricsCollector()
        self.backpressure = backpressure or BackpressureMonitor()
        self._window = max(self.MIN_WINDOW, min(self.MAX_WINDOW, initial_window))
        self._history: list[WindowSnapshot] = []
        self._last_batch_time: float = time.monotonic()

    @property
    def current_window(self) -> float:
        return self._window

    def after_batch(self, batch_size: int, processing_time_s: float) -> float:
        """Called after every batch. Returns next window size (seconds)."""
        now = time.monotonic()
        dt = max(now - self._last_batch_time, 1e-6)
        self._last_batch_time = now

        self.metrics.record(batch_size, processing_time_s, self._window)

        lat = self.metrics.latency_snapshot()
        tput = self.metrics.throughput_snapshot()

        p95 = lat.p95 if lat is not None else processing_time_s
        eps = tput.events_per_second if tput is not None else 0.0
        bp = self.backpressure.current_level()

        target = self.sla.target_latency_s
        latency_error = (p95 - target) / max(target, 1e-9)
        combined_error = max(-1.0, min(1.0, latency_error + self.sla.backpressure_weight * bp))

        self._window = self.pid.apply(self._window, combined_error, dt)

        snap = WindowSnapshot(
            window_size_s=self._window,
            pid_error=combined_error,
            backpressure_level=bp,
            p95_latency=p95,
            throughput_eps=eps,
            timestamp=now,
        )
        self._history.append(snap)
        if len(self._history) > 1000:
            self._history = self._history[-1000:]

        logger.debug(
            "window=%.3fs  error=%.3f  bp=%.2f  p95=%.3fs  tput=%.1f eps",
            self._window,
            combined_error,
            bp,
            p95,
            eps,
        )
        return self._window

    def history(self) -> list[WindowSnapshot]:
        return list(self._history)

    def reset(self) -> None:
        self.pid.reset()
        self._window = 0.5
        self._history.clear()
        self._last_batch_time = time.monotonic()
