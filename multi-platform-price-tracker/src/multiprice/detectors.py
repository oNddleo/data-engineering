"""Detection functions: price changes, cross-platform arbitrage, stockouts, MAP breaches.

Every detector is a pure function ``(store, **params) -> list[Event]``.
Composable: caller decides which to run + in what order.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from multiprice.events import (
    ArbitrageEvent,
    BelowMapEvent,
    Direction,
    EventKind,
    PriceChangeEvent,
    StockoutEvent,
)

if TYPE_CHECKING:
    from datetime import datetime

    from multiprice.store import ObservationStore


# ---------------------------------------------------------------------------
# Price change.


def detect_price_changes(
    store: ObservationStore,
    *,
    since: datetime | None = None,
    min_pct_change: float = 0.0,
) -> list[PriceChangeEvent]:
    """Find each ``(SKU, platform)`` series where the *latest* observation's
    price differs from the *previous* observation by ≥ ``min_pct_change`` %.

    Only one event per series — the most recent transition. To get
    full historical changes, iterate per-pair and call this on
    successively bounded ``since`` windows.
    """
    if min_pct_change < 0:
        raise ValueError("min_pct_change must be >= 0")
    events: list[PriceChangeEvent] = []
    for sku in sorted(store.all_skus()):
        from multiprice.schema import Platform as _Platform

        for plat in _Platform:
            hist = store.history(sku, plat, since=since)
            if len(hist) < 2:
                continue
            prev = hist[-2]
            curr = hist[-1]
            if curr.price_vnd == prev.price_vnd:
                continue
            pct = (curr.price_vnd - prev.price_vnd) / prev.price_vnd * 100
            if abs(pct) < min_pct_change:
                continue
            events.append(
                PriceChangeEvent(
                    kind=EventKind.PRICE_CHANGE,
                    canonical_sku=sku,
                    platform=plat,
                    platform_item_id=curr.platform_item_id,
                    previous_price_vnd=prev.price_vnd,
                    current_price_vnd=curr.price_vnd,
                    direction=Direction.UP if pct > 0 else Direction.DOWN,
                    pct_change=pct,
                    observed_at=curr.observed_at,
                )
            )
    return events


# ---------------------------------------------------------------------------
# Cross-platform arbitrage.


def detect_arbitrage(
    store: ObservationStore,
    *,
    min_spread_pct: float = 10.0,
) -> list[ArbitrageEvent]:
    """For each SKU, compare the latest in-stock price across platforms.

    Emits one event per SKU if ``(max - min) / min * 100 ≥ min_spread_pct``.
    Out-of-stock observations are skipped — you can't actually buy
    them to arbitrage. Need ≥ 2 platforms with in-stock data.
    """
    if min_spread_pct < 0:
        raise ValueError("min_spread_pct must be >= 0")
    events: list[ArbitrageEvent] = []
    for sku in sorted(store.all_skus()):
        latest = store.all_latest_for_sku(sku)
        in_stock = {plat: obs for plat, obs in latest.items() if obs.is_in_stock}
        if len(in_stock) < 2:
            continue
        cheapest_plat, cheapest_obs = min(in_stock.items(), key=lambda kv: kv[1].price_vnd)
        most_exp_plat, most_exp_obs = max(in_stock.items(), key=lambda kv: kv[1].price_vnd)
        if most_exp_obs.price_vnd == cheapest_obs.price_vnd:
            continue
        spread = most_exp_obs.price_vnd - cheapest_obs.price_vnd
        spread_pct = spread / cheapest_obs.price_vnd * 100
        if spread_pct < min_spread_pct:
            continue
        events.append(
            ArbitrageEvent(
                kind=EventKind.ARBITRAGE,
                canonical_sku=sku,
                cheapest_platform=cheapest_plat,
                cheapest_price_vnd=cheapest_obs.price_vnd,
                most_expensive_platform=most_exp_plat,
                most_expensive_price_vnd=most_exp_obs.price_vnd,
                spread_vnd=spread,
                spread_pct=spread_pct,
            )
        )
    return events


# ---------------------------------------------------------------------------
# Stockout.


def detect_stockouts(store: ObservationStore) -> list[StockoutEvent]:
    """Emit one event per ``(SKU, platform)`` whose latest observation has stock 0."""
    from multiprice.schema import Platform as _Platform

    events: list[StockoutEvent] = []
    for sku in sorted(store.all_skus()):
        for plat in _Platform:
            obs = store.latest(sku, plat)
            if obs is None or obs.is_in_stock:
                continue
            events.append(
                StockoutEvent(
                    kind=EventKind.STOCKOUT,
                    canonical_sku=sku,
                    platform=plat,
                    platform_item_id=obs.platform_item_id,
                    observed_at=obs.observed_at,
                )
            )
    return events


# ---------------------------------------------------------------------------
# Below-MAP (Minimum Advertised Price) breach.


def detect_below_map(
    store: ObservationStore,
    map_table: dict[str, int],
) -> list[BelowMapEvent]:
    """Emit one event per ``(SKU, platform)`` whose latest price is below
    the manufacturer's MAP (Minimum Advertised Price).

    ``map_table`` maps ``canonical_sku → map_vnd``. SKUs not in the
    table are skipped silently — not every product has a MAP set.
    """
    from multiprice.schema import Platform as _Platform

    events: list[BelowMapEvent] = []
    for sku in sorted(store.all_skus()):
        map_vnd = map_table.get(sku)
        if map_vnd is None:
            continue
        for plat in _Platform:
            obs = store.latest(sku, plat)
            if obs is None or obs.price_vnd >= map_vnd:
                continue
            events.append(
                BelowMapEvent(
                    kind=EventKind.BELOW_MAP,
                    canonical_sku=sku,
                    platform=plat,
                    platform_item_id=obs.platform_item_id,
                    current_price_vnd=obs.price_vnd,
                    map_vnd=map_vnd,
                    breach_vnd=map_vnd - obs.price_vnd,
                )
            )
    return events


__all__ = [
    "detect_arbitrage",
    "detect_below_map",
    "detect_price_changes",
    "detect_stockouts",
]
