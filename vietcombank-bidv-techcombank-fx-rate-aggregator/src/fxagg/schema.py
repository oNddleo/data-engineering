"""FX-quote data model.

A :class:`Quote` is one currency-pair line as advertised by one
Vietnamese commercial bank at a point in time. A :class:`Snapshot`
is the full set of currency quotes one bank published together —
everything they showed on their rate page in one scrape.

VND has no fractional unit, so all prices are integer VND. Some
banks quote "buy cash" (mua tiền mặt) separately from "buy
transfer" (mua chuyển khoản) because cash carries an extra
counting / vault-handling cost; others publish only the transfer
rate. We model that by making ``buy_cash_vnd`` optional.

Currency codes are ISO 4217. The enum here is the subset that
matters for the VN market (USD, EUR, JPY, GBP, AUD, SGD, CNY, KRW,
THB, HKD, CAD). Add more as the test suite demands them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum

VN_TZ = timezone(timedelta(hours=7))
"""Vietnam Standard Time (Indochina Time). No DST."""


class Currency(str, Enum):
    """ISO-4217 codes for the currencies VN banks routinely quote."""

    USD = "USD"
    EUR = "EUR"
    JPY = "JPY"
    GBP = "GBP"
    AUD = "AUD"
    SGD = "SGD"
    CNY = "CNY"
    KRW = "KRW"
    THB = "THB"
    HKD = "HKD"
    CAD = "CAD"


class Bank(str, Enum):
    """Top-10 commercial banks the aggregator routinely scrapes."""

    VCB = "VCB"  # Vietcombank
    BIDV = "BIDV"  # BIDV
    TCB = "TCB"  # Techcombank
    MB = "MB"  # MB Bank
    VPB = "VPB"  # VPBank
    ACB = "ACB"  # ACB
    VTB = "VTB"  # VietinBank
    AGB = "AGB"  # Agribank
    HDB = "HDB"  # HDBank
    TPB = "TPB"  # TPBank


@dataclass(frozen=True, slots=True)
class Quote:
    """One currency-pair quote from one bank at one point in time."""

    bank: Bank
    currency: Currency
    buy_transfer_vnd: int
    sell_vnd: int
    quoted_at: datetime
    buy_cash_vnd: int | None = None

    def __post_init__(self) -> None:
        if self.buy_transfer_vnd <= 0:
            raise ValueError(f"buy_transfer_vnd must be > 0, got {self.buy_transfer_vnd}")
        if self.sell_vnd <= 0:
            raise ValueError(f"sell_vnd must be > 0, got {self.sell_vnd}")
        if self.buy_cash_vnd is not None and self.buy_cash_vnd <= 0:
            raise ValueError(f"buy_cash_vnd must be > 0 or None, got {self.buy_cash_vnd}")
        if self.quoted_at.tzinfo is None:
            raise ValueError("quoted_at must be timezone-aware")

    @property
    def bid_ask_spread_vnd(self) -> int:
        """Sell minus buy_transfer. Negative means the row is broken (inverted)."""
        return self.sell_vnd - self.buy_transfer_vnd

    @property
    def bid_ask_spread_pct(self) -> float:
        """Spread expressed as a percentage of the mid-price."""
        mid = (self.sell_vnd + self.buy_transfer_vnd) / 2
        if mid == 0:
            return 0.0
        return (self.sell_vnd - self.buy_transfer_vnd) / mid * 100


@dataclass(frozen=True, slots=True)
class Snapshot:
    """All quotes one bank published together — the result of one scrape."""

    bank: Bank
    quoted_at: datetime
    quotes: tuple[Quote, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.quoted_at.tzinfo is None:
            raise ValueError("quoted_at must be timezone-aware")
        for q in self.quotes:
            if q.bank is not self.bank:
                raise ValueError(
                    f"quote bank {q.bank.value} doesn't match snapshot bank {self.bank.value}"
                )

    def get(self, currency: Currency) -> Quote | None:
        for q in self.quotes:
            if q.currency is currency:
                return q
        return None


__all__ = ["VN_TZ", "Bank", "Currency", "Quote", "Snapshot"]
