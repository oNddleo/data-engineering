"""Stream-derived detectors fed by `WindowAggregate` outputs.

Three patterns the flash-sale ops team cares about:

* **Hot product** — a single item's views/orders in one window exceed a
  threshold. Operators use this to feature the item, refresh CDN
  cache, or push notifications to wishlist subscribers.
* **Stampede** — a sudden 10×+ spike in views for an item versus its
  prior window. Suggests a viral push or a price-error story
  spreading on social media. Often correlates with checkout
  failures and inventory race conditions.
* **Inventory burn-down** — stock for an item dropped below a
  per-item threshold OR is depleting at a rate that will hit zero
  within the next minute at current order velocity.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from flashpipe.windows import WindowAggregate


class HotnessKind(str, Enum):
    HOT_PRODUCT = "HOT_PRODUCT"
    STAMPEDE = "STAMPEDE"
    INVENTORY_BURNDOWN = "INVENTORY_BURNDOWN"


@dataclass(frozen=True, slots=True)
class HotnessEvent:
    """One detector output."""

    kind: HotnessKind
    item_id: int
    window_start: datetime
    window_end: datetime
    detail: str
    metric: int


# ---------------------------------------------------------------------------
# Hot product.


def detect_hot_product(
    aggregate: WindowAggregate,
    *,
    min_views: int = 1_000,
    min_orders: int = 50,
) -> HotnessEvent | None:
    """Flag a single window's aggregate as a hot product."""
    if aggregate.n_views >= min_views or aggregate.n_orders >= min_orders:
        return HotnessEvent(
            kind=HotnessKind.HOT_PRODUCT,
            item_id=aggregate.item_id,
            window_start=aggregate.window_start,
            window_end=aggregate.window_end,
            detail=(
                f"views={aggregate.n_views}, orders={aggregate.n_orders} "
                f"(thresholds views≥{min_views} OR orders≥{min_orders})"
            ),
            metric=max(aggregate.n_views, aggregate.n_orders),
        )
    return None


# ---------------------------------------------------------------------------
# Stampede.


class StampedeDetector:
    """Per-item view-spike detector that compares window N vs N−1."""

    def __init__(self, *, multiplier: float = 10.0, min_baseline: int = 10) -> None:
        if multiplier <= 1:
            raise ValueError("multiplier must be > 1")
        if min_baseline < 1:
            raise ValueError("min_baseline must be >= 1")
        self._multiplier = multiplier
        self._min_baseline = min_baseline
        self._last_views: dict[int, int] = {}

    def consume(self, aggregate: WindowAggregate) -> HotnessEvent | None:
        prev = self._last_views.get(aggregate.item_id, 0)
        self._last_views[aggregate.item_id] = aggregate.n_views
        if prev < self._min_baseline:
            return None
        if aggregate.n_views < prev * self._multiplier:
            return None
        return HotnessEvent(
            kind=HotnessKind.STAMPEDE,
            item_id=aggregate.item_id,
            window_start=aggregate.window_start,
            window_end=aggregate.window_end,
            detail=(
                f"views spiked {aggregate.n_views} from {prev} "
                f"(multiplier ≥ {self._multiplier:.1f}×)"
            ),
            metric=aggregate.n_views,
        )


# ---------------------------------------------------------------------------
# Inventory burndown.


def detect_burndown(
    aggregate: WindowAggregate,
    *,
    current_stock: int,
    horizon_seconds: int = 60,
) -> HotnessEvent | None:
    """Flag if at the current orders/window rate we'd run out within ``horizon_seconds``.

    ``current_stock`` is supplied by the caller (typically from a
    side-channel inventory snapshot — this module doesn't track
    stock itself).
    """
    if horizon_seconds <= 0:
        raise ValueError("horizon_seconds must be > 0")
    if current_stock <= 0:
        return None  # already out
    if aggregate.units_sold == 0:
        return None
    window_seconds = max(int((aggregate.window_end - aggregate.window_start).total_seconds()), 1)
    rate_per_sec = aggregate.units_sold / window_seconds
    seconds_until_zero = current_stock / rate_per_sec
    if seconds_until_zero > horizon_seconds:
        return None
    return HotnessEvent(
        kind=HotnessKind.INVENTORY_BURNDOWN,
        item_id=aggregate.item_id,
        window_start=aggregate.window_start,
        window_end=aggregate.window_end,
        detail=(
            f"stock {current_stock} burning at {rate_per_sec:.1f}/s → "
            f"~{seconds_until_zero:.0f}s to zero (horizon {horizon_seconds}s)"
        ),
        metric=int(seconds_until_zero),
    )


__all__ = [
    "HotnessEvent",
    "HotnessKind",
    "StampedeDetector",
    "detect_burndown",
    "detect_hot_product",
]
