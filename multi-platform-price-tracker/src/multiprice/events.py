"""Event types produced by the detectors."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime

    from multiprice.schema import Platform


class EventKind(str, Enum):
    PRICE_CHANGE = "PRICE_CHANGE"
    """The latest observation's price differs from the previous one on the same platform."""

    ARBITRAGE = "ARBITRAGE"
    """Same SKU's spread across platforms exceeds the threshold."""

    STOCKOUT = "STOCKOUT"
    """Latest observation has ``stock == 0``."""

    BELOW_MAP = "BELOW_MAP"
    """Latest price is below the manufacturer's minimum advertised price."""


class Direction(str, Enum):
    """Price-change direction."""

    UP = "UP"
    DOWN = "DOWN"
    SAME = "SAME"


@dataclass(frozen=True, slots=True)
class PriceChangeEvent:
    """A price changed between two consecutive observations."""

    kind: EventKind
    canonical_sku: str
    platform: Platform
    platform_item_id: str
    previous_price_vnd: int
    current_price_vnd: int
    direction: Direction
    pct_change: float
    observed_at: datetime


@dataclass(frozen=True, slots=True)
class ArbitrageEvent:
    """Same SKU has a significant price spread between platforms."""

    kind: EventKind
    canonical_sku: str
    cheapest_platform: Platform
    cheapest_price_vnd: int
    most_expensive_platform: Platform
    most_expensive_price_vnd: int
    spread_vnd: int
    spread_pct: float


@dataclass(frozen=True, slots=True)
class StockoutEvent:
    """Latest observation shows zero stock."""

    kind: EventKind
    canonical_sku: str
    platform: Platform
    platform_item_id: str
    observed_at: datetime


@dataclass(frozen=True, slots=True)
class BelowMapEvent:
    """Latest price is below the manufacturer's MAP (minimum advertised price)."""

    kind: EventKind
    canonical_sku: str
    platform: Platform
    platform_item_id: str
    current_price_vnd: int
    map_vnd: int
    breach_vnd: int


__all__ = [
    "ArbitrageEvent",
    "BelowMapEvent",
    "Direction",
    "EventKind",
    "PriceChangeEvent",
    "StockoutEvent",
]
