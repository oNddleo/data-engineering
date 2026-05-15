"""End-to-end engine wiring: watermark + window aggregator + detectors + sinks + metrics.

Single entry: :meth:`StreamEngine.consume_many` drains an iterable
of events and runs every stage. Production calls :meth:`consume`
per event from a Kafka poll loop.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from flashpipe.detectors import StampedeDetector, detect_hot_product
from flashpipe.metrics import MetricsCollector
from flashpipe.watermark import WatermarkTracker
from flashpipe.windows import TumblingAggregator

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import datetime

    from flashpipe.detectors import HotnessEvent
    from flashpipe.events import Event
    from flashpipe.metrics import MetricsSnapshot
    from flashpipe.sinks import HotnessSink, WindowSink


class StreamEngine:
    """Watermark + tumbling-window + detectors + sinks + metrics."""

    def __init__(
        self,
        *,
        window_seconds: int = 1,
        max_out_of_orderness_seconds: float = 5.0,
        hot_min_views: int = 1_000,
        hot_min_orders: int = 50,
        stampede_multiplier: float = 10.0,
        stampede_min_baseline: int = 10,
    ) -> None:
        self._watermark = WatermarkTracker(
            max_out_of_orderness_seconds=max_out_of_orderness_seconds
        )
        self._aggregator = TumblingAggregator(window_seconds=window_seconds)
        self._stampede = StampedeDetector(
            multiplier=stampede_multiplier, min_baseline=stampede_min_baseline
        )
        self._hot_min_views = hot_min_views
        self._hot_min_orders = hot_min_orders
        self._metrics = MetricsCollector()

    @property
    def watermark(self) -> datetime | None:
        return self._watermark.watermark

    @property
    def metrics(self) -> MetricsCollector:
        return self._metrics

    def consume(
        self,
        event: Event,
        *,
        window_sink: WindowSink | None = None,
        hotness_sink: HotnessSink | None = None,
        wall_clock_now: datetime | None = None,
    ) -> list[HotnessEvent]:
        """Process one event end-to-end. Returns the hotness events fired."""
        wall_before = time.perf_counter()
        if self._watermark.is_late(event.created_at):
            self._metrics.mark_late()
            return []
        self._watermark.observe(event.created_at)
        closed = self._aggregator.consume(event, watermark=self._watermark.watermark)
        hotness: list[HotnessEvent] = []
        for agg in closed:
            if window_sink is not None:
                window_sink.write(agg)
            hot = detect_hot_product(
                agg, min_views=self._hot_min_views, min_orders=self._hot_min_orders
            )
            if hot is not None:
                hotness.append(hot)
                if hotness_sink is not None:
                    hotness_sink.write(hot)
            stamp = self._stampede.consume(agg)
            if stamp is not None:
                hotness.append(stamp)
                if hotness_sink is not None:
                    hotness_sink.write(stamp)
        wall_after = time.perf_counter()
        self._metrics.record(
            event_time=event.created_at,
            wall_clock_before=wall_before,
            wall_clock_after=wall_after,
            processed_at_wall=wall_clock_now or event.created_at,
        )
        return hotness

    def consume_many(
        self,
        events: Iterable[Event],
        *,
        window_sink: WindowSink | None = None,
        hotness_sink: HotnessSink | None = None,
    ) -> list[HotnessEvent]:
        all_hot: list[HotnessEvent] = []
        for e in events:
            all_hot.extend(self.consume(e, window_sink=window_sink, hotness_sink=hotness_sink))
        # End-of-stream flush — still-open windows must pass through the detectors
        # too. Otherwise a stampede that lands in the final window (no trigger
        # event arrives to advance the watermark past it) would silently drop its
        # hotness alert.
        for agg in self._aggregator.flush_all():
            if window_sink is not None:
                window_sink.write(agg)
            hot = detect_hot_product(
                agg, min_views=self._hot_min_views, min_orders=self._hot_min_orders
            )
            if hot is not None:
                all_hot.append(hot)
                if hotness_sink is not None:
                    hotness_sink.write(hot)
            stamp = self._stampede.consume(agg)
            if stamp is not None:
                all_hot.append(stamp)
                if hotness_sink is not None:
                    hotness_sink.write(stamp)
        return all_hot

    def snapshot(self) -> MetricsSnapshot:
        return self._metrics.snapshot()


__all__ = ["StreamEngine"]
