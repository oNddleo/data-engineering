"""Tumbling-window aggregation per ``item_id``.

A tumbling window is a fixed-size, non-overlapping bucket. We
align windows to the wall clock at second granularity: the window
containing event time ``t`` is ``[t // W * W, (t // W + 1) * W)``.

The aggregator keeps an open `WindowState` per `(window_start,
item_id)` while events are still arriving. When the watermark
advances past a window's end, that window is emitted as a
`WindowAggregate` and dropped from the live state.

Late events (`event_time < watermark`) bypass the aggregator and
are reported separately by the engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from flashpipe.events import EventKind

if TYPE_CHECKING:
    from flashpipe.events import Event


def window_start_for(event_time: datetime, window_seconds: int) -> datetime:
    """Snap an event time to the start of its tumbling window."""
    epoch = event_time.timestamp()
    bucket = int(epoch // window_seconds) * window_seconds
    return datetime.fromtimestamp(bucket, tz=event_time.tzinfo)


@dataclass(slots=True)
class WindowState:
    """Mutable per-(window_start, item_id) accumulator."""

    window_start: datetime
    window_end: datetime
    item_id: int
    n_views: int = 0
    n_add_to_cart: int = 0
    n_checkout: int = 0
    n_orders: int = 0
    units_sold: int = 0
    gmv_vnd: int = 0
    unique_users: set[str] = field(default_factory=set)

    def consume(self, event: Event) -> None:
        if event.kind is EventKind.VIEW:
            self.n_views += 1
        elif event.kind is EventKind.ADD_TO_CART:
            self.n_add_to_cart += 1
        elif event.kind is EventKind.CHECKOUT:
            self.n_checkout += 1
        elif event.kind is EventKind.ORDER:
            self.n_orders += 1
            self.units_sold += event.quantity
            self.gmv_vnd += event.amount_vnd
        if event.user_id:
            self.unique_users.add(event.user_id)


@dataclass(frozen=True, slots=True)
class WindowAggregate:
    """Immutable output of one closed window for one item."""

    window_start: datetime
    window_end: datetime
    item_id: int
    n_views: int
    n_add_to_cart: int
    n_checkout: int
    n_orders: int
    units_sold: int
    gmv_vnd: int
    unique_users: int

    @property
    def conversion_pct(self) -> float:
        """``orders / views * 100``. Returns 0.0 when no views."""
        if self.n_views == 0:
            return 0.0
        return self.n_orders / self.n_views * 100


def _aggregate_from_state(state: WindowState) -> WindowAggregate:
    return WindowAggregate(
        window_start=state.window_start,
        window_end=state.window_end,
        item_id=state.item_id,
        n_views=state.n_views,
        n_add_to_cart=state.n_add_to_cart,
        n_checkout=state.n_checkout,
        n_orders=state.n_orders,
        units_sold=state.units_sold,
        gmv_vnd=state.gmv_vnd,
        unique_users=len(state.unique_users),
    )


class TumblingAggregator:
    """Per-item tumbling-window aggregator with watermark-driven emission."""

    def __init__(self, *, window_seconds: int = 1) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        self._window_seconds = window_seconds
        self._open: dict[tuple[datetime, int], WindowState] = {}
        self._dropped_late: int = 0

    @property
    def n_open_windows(self) -> int:
        return len(self._open)

    @property
    def dropped_late_events(self) -> int:
        return self._dropped_late

    def consume(self, event: Event, *, watermark: datetime | None) -> list[WindowAggregate]:
        """Process one event. Returns the list of windows that just closed."""
        if watermark is not None and event.created_at < watermark:
            self._dropped_late += 1
            return []
        ws = window_start_for(event.created_at, self._window_seconds)
        we = ws + timedelta(seconds=self._window_seconds)
        key = (ws, event.item_id)
        state = self._open.get(key)
        if state is None:
            state = WindowState(window_start=ws, window_end=we, item_id=event.item_id)
            self._open[key] = state
        state.consume(event)
        # Close any windows whose end is ≤ current watermark.
        return self._flush(watermark)

    def _flush(self, watermark: datetime | None) -> list[WindowAggregate]:
        if watermark is None:
            return []
        closed: list[WindowAggregate] = []
        for key in list(self._open):
            state = self._open[key]
            if state.window_end <= watermark:
                closed.append(_aggregate_from_state(state))
                del self._open[key]
        closed.sort(key=lambda a: (a.window_start, a.item_id))
        return closed

    def flush_all(self) -> list[WindowAggregate]:
        """Force-close every still-open window. Use at end of stream."""
        closed = [_aggregate_from_state(s) for s in self._open.values()]
        self._open.clear()
        closed.sort(key=lambda a: (a.window_start, a.item_id))
        return closed


__all__ = [
    "TumblingAggregator",
    "WindowAggregate",
    "WindowState",
    "window_start_for",
]
