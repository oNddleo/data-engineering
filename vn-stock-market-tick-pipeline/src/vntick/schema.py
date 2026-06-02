"""VN-equity tick schema + exchange rules.

Three exchanges + their distinct trading rules:

| Exchange | Daily band | Lot size | Notes                                  |
| -------- | ---------- | -------- | -------------------------------------- |
| HOSE     | ±7%        | 100      | Ho Chi Minh — VN30, VN-Index           |
| HNX      | ±10%       | 100      | Hanoi — HNX-Index, mid-caps            |
| UPCoM    | ±15%       | 100      | Unlisted Public Company — wider band   |

All money is **integer VND** (no Decimal, no float drift). Prices in
the VN market trade at whole-dong granularity, so int is the natural
type — and joins between tick streams, indicators, and indexes stay
exact.

Trading sessions (``VN_TZ`` = ``UTC+7``):

* **Morning**: 09:00 — 11:30
* **Afternoon**: 13:00 — 14:45 (HOSE/HNX close 14:30, ATC 14:30 — 14:45)

Ticks outside session hours are dropped by ``validate_session``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))


class Exchange(str, Enum):
    """The three VN trading venues."""

    HOSE = "HOSE"
    HNX = "HNX"
    UPCOM = "UPCOM"


# Daily price-band as percentage; multiply by 100 internally for int math.
_BAND_BPS: dict[Exchange, int] = {
    Exchange.HOSE: 700,  # ±7.00%
    Exchange.HNX: 1000,  # ±10.00%
    Exchange.UPCOM: 1500,  # ±15.00%
}

_LOT_SIZE: dict[Exchange, int] = {
    Exchange.HOSE: 100,
    Exchange.HNX: 100,
    Exchange.UPCOM: 100,
}


def daily_band_bps(exchange: Exchange) -> int:
    """Daily price-band as basis points (1% = 100 bps)."""
    return _BAND_BPS[exchange]


def lot_size(exchange: Exchange) -> int:
    """Minimum order quantity for the exchange."""
    return _LOT_SIZE[exchange]


def ceiling_price(reference_vnd: int, exchange: Exchange) -> int:
    """Upper price band (giá trần) — rounded to the nearest VND."""
    return reference_vnd + reference_vnd * daily_band_bps(exchange) // 10_000


def floor_price(reference_vnd: int, exchange: Exchange) -> int:
    """Lower price band (giá sàn)."""
    return reference_vnd - reference_vnd * daily_band_bps(exchange) // 10_000


_MORNING_OPEN = time(9, 0)
_MORNING_CLOSE = time(11, 30)
_AFTERNOON_OPEN = time(13, 0)
_AFTERNOON_CLOSE = time(14, 45)


def is_in_session(ts: datetime) -> bool:
    """``True`` if ``ts`` (any tz) falls in a VN trading session."""
    if ts.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    local = ts.astimezone(VN_TZ).time()
    return _MORNING_OPEN <= local <= _MORNING_CLOSE or _AFTERNOON_OPEN <= local <= _AFTERNOON_CLOSE


@dataclass(frozen=True, slots=True)
class Symbol:
    """One listed equity — symbol-level reference data."""

    code: str  # ticker (e.g. "VIC", "VHM", "HPG")
    exchange: Exchange
    name: str
    sector: str
    listed_shares: int  # outstanding shares; used for market-cap weighting

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("code must be non-empty")
        if not self.code.isascii() or not self.code.isupper():
            raise ValueError(f"code must be ASCII uppercase, got {self.code!r}")
        if not self.name:
            raise ValueError("name must be non-empty")
        if not self.sector:
            raise ValueError("sector must be non-empty")
        if self.listed_shares <= 0:
            raise ValueError(f"listed_shares must be > 0, got {self.listed_shares}")


@dataclass(frozen=True, slots=True)
class Tick:
    """One traded print (matched order)."""

    code: str
    price_vnd: int
    volume: int  # shares — must be a multiple of the exchange's lot size
    occurred_at: datetime
    side: str  # "B" (buyer-initiated) or "S" (seller-initiated)

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("code must be non-empty")
        if self.price_vnd <= 0:
            raise ValueError(f"price_vnd must be > 0, got {self.price_vnd}")
        if self.volume <= 0:
            raise ValueError(f"volume must be > 0, got {self.volume}")
        if self.occurred_at.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware")
        if self.side not in ("B", "S"):
            raise ValueError(f"side must be 'B' or 'S', got {self.side!r}")


@dataclass(frozen=True, slots=True)
class OHLCVBar:
    """One aggregated OHLCV bar at a fixed interval."""

    code: str
    interval_seconds: int  # 60, 300, 900, 3600, 86400
    bar_start: datetime  # left-closed
    open_vnd: int
    high_vnd: int
    low_vnd: int
    close_vnd: int
    volume: int
    n_trades: int

    def __post_init__(self) -> None:
        if not self.code:
            raise ValueError("code must be non-empty")
        if self.interval_seconds <= 0:
            raise ValueError("interval_seconds must be > 0")
        if self.bar_start.tzinfo is None:
            raise ValueError("bar_start must be timezone-aware")
        if min(self.open_vnd, self.high_vnd, self.low_vnd, self.close_vnd) <= 0:
            raise ValueError("OHLC must all be > 0")
        if self.low_vnd > min(self.open_vnd, self.close_vnd):
            raise ValueError(f"low ({self.low_vnd}) must be <= min(open, close)")
        if self.high_vnd < max(self.open_vnd, self.close_vnd):
            raise ValueError(f"high ({self.high_vnd}) must be >= max(open, close)")
        if self.volume < 0 or self.n_trades < 0:
            raise ValueError("volume and n_trades must be >= 0")


__all__ = [
    "VN_TZ",
    "Exchange",
    "OHLCVBar",
    "Symbol",
    "Tick",
    "ceiling_price",
    "daily_band_bps",
    "floor_price",
    "is_in_session",
    "lot_size",
]
