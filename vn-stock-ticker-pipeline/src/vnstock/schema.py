"""VN stock exchange schema — Exchange, Ticker, OHLCBar, Order.

Models the three VN equity exchanges and their daily-bar / order data:

| Exchange | Code   | Operator        | Band (normal) | Band (IPO day) |
| -------- | ------ | --------------- | ------------- | -------------- |
| HOSE     | HOSE   | Sở GDCK TP HCM  | ±7%           | ±20%           |
| HNX      | HNX    | Sở GDCK Hà Nội  | ±10%          | ±30%           |
| UPCoM    | UPCOM  | HNX (subsidiary)| ±15%          | ±40%           |

All prices are **integer VND** (the published tick is 10/50/100 VND;
fractional VND prices are not used in VN equity trading).

All ticker symbols are 3 ASCII uppercase letters in normal practice
(VIC, VNM, FPT, ...); we permit 3-5 letters for generality.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date


class Exchange(str, Enum):
    """Three VN equity exchanges."""

    HOSE = "HOSE"  # Sở GDCK TP. Hồ Chí Minh — main board
    HNX = "HNX"  # Sở GDCK Hà Nội
    UPCOM = "UPCOM"  # Unlisted Public Company Market


class OrderKind(str, Enum):
    """Four order kinds covering ~99% of VN equity flow."""

    LO = "LO"  # Limit Order
    MP = "MP"  # Market Price
    ATO = "ATO"  # At-the-Open
    ATC = "ATC"  # At-the-Close


class OrderSide(str, Enum):
    """Buy / Sell."""

    BUY = "BUY"
    SELL = "SELL"


def _is_valid_ticker_symbol(symbol: str) -> bool:
    """Allow 3-5 ASCII uppercase letters.

    VN equity tickers on HOSE / HNX / UPCoM are 3 ASCII letters in the
    overwhelming majority (VIC, VNM, FPT, ...). A handful of UPCoM
    names go to 4 letters. 1-2 chars never appear in practice.
    """
    return 3 <= len(symbol) <= 5 and symbol.isascii() and symbol.isalpha() and symbol.isupper()


@dataclass(frozen=True, slots=True)
class Ticker:
    """One listed ticker."""

    symbol: str
    exchange: Exchange
    name_vi: str
    name_en: str
    industry: str = ""
    is_active: bool = True

    def __post_init__(self) -> None:
        if not _is_valid_ticker_symbol(self.symbol):
            raise ValueError(
                f"symbol must be 3-5 uppercase ASCII letters, got {self.symbol!r}",
            )
        if not self.name_vi:
            raise ValueError("name_vi must be non-empty")


@dataclass(frozen=True, slots=True)
class OHLCBar:
    """One day's open / high / low / close + volume bar for a ticker.

    ``reference_price`` is the previous session's close (used to
    compute today's price band). For an IPO day it's the listing price.
    """

    symbol: str
    exchange: Exchange
    date: date
    open_vnd: int
    high_vnd: int
    low_vnd: int
    close_vnd: int
    volume: int
    reference_price_vnd: int

    def __post_init__(self) -> None:
        if not _is_valid_ticker_symbol(self.symbol):
            raise ValueError(f"symbol must be 3-5 uppercase letters, got {self.symbol!r}")
        for name, val in (
            ("open_vnd", self.open_vnd),
            ("high_vnd", self.high_vnd),
            ("low_vnd", self.low_vnd),
            ("close_vnd", self.close_vnd),
            ("reference_price_vnd", self.reference_price_vnd),
        ):
            if val <= 0:
                raise ValueError(f"{name} must be > 0, got {val}")
        if self.volume < 0:
            raise ValueError(f"volume must be >= 0, got {self.volume}")
        # OHLC invariants — high >= max(open, close, low), low <= everything.
        if self.high_vnd < max(self.open_vnd, self.close_vnd, self.low_vnd):
            raise ValueError(
                f"high {self.high_vnd} must be >= max(open, close, low)",
            )
        if self.low_vnd > min(self.open_vnd, self.close_vnd, self.high_vnd):
            raise ValueError(
                f"low {self.low_vnd} must be <= min(open, close, high)",
            )

    @property
    def daily_change_vnd(self) -> int:
        """Close − reference. Positive if price rose."""
        return self.close_vnd - self.reference_price_vnd

    @property
    def daily_change_bps(self) -> int:
        """Change as basis points of reference (10_000 = 100%)."""
        return (self.daily_change_vnd * 10_000) // self.reference_price_vnd


@dataclass(frozen=True, slots=True)
class Order:
    """One order submission."""

    order_id: str
    symbol: str
    exchange: Exchange
    side: OrderSide
    kind: OrderKind
    quantity: int
    limit_price_vnd: int  # 0 for MP / ATO / ATC

    def __post_init__(self) -> None:
        if not self.order_id:
            raise ValueError("order_id must be non-empty")
        if not _is_valid_ticker_symbol(self.symbol):
            raise ValueError(f"symbol must be 3-5 uppercase letters, got {self.symbol!r}")
        if self.quantity <= 0:
            raise ValueError(f"quantity must be > 0, got {self.quantity}")
        if self.limit_price_vnd < 0:
            raise ValueError(
                f"limit_price_vnd must be >= 0, got {self.limit_price_vnd}",
            )
        if self.kind is OrderKind.LO and self.limit_price_vnd == 0:
            raise ValueError("LO order must have limit_price_vnd > 0")
        if self.kind in {OrderKind.MP, OrderKind.ATO, OrderKind.ATC} and self.limit_price_vnd != 0:
            raise ValueError(
                f"{self.kind.value} order must have limit_price_vnd=0, "
                f"got {self.limit_price_vnd}",
            )


class AnomalyKind(str, Enum):
    """Three OHLC-bar anomaly classes."""

    PRICE_BAND_BREACH = "PRICE_BAND_BREACH"  # close moved beyond exchange band
    VOLUME_SPIKE = "VOLUME_SPIKE"  # volume > 5× trailing average
    PRICE_GAP = "PRICE_GAP"  # open jumped > 5% from prev close


@dataclass(frozen=True, slots=True)
class AnomalyFinding:
    """One ops-actionable bar anomaly."""

    kind: AnomalyKind
    symbol: str
    exchange: Exchange
    date: date
    detail: str
    metric: int


__all__ = [
    "AnomalyFinding",
    "AnomalyKind",
    "Exchange",
    "OHLCBar",
    "Order",
    "OrderKind",
    "OrderSide",
    "Ticker",
]
