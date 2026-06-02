"""Spread analysis + cross-bank outlier detection.

Given a snapshot of each bank's latest quote for one currency, we
compute:

* The peer **median** buy_transfer and sell rates.
* Each bank's **deviation** from that median, in percent of median.
* The peer **median bid/ask spread** (sell - buy_transfer).

From there we fire 4 alert kinds:

* :attr:`AlertKind.INVERTED_SPREAD` — a single quote has
  ``sell < buy_transfer``. The row is broken regardless of what the
  rest of the market is doing.
* :attr:`AlertKind.BUY_OUTLIER` — bank's ``buy_transfer`` is more
  than ``outlier_pct`` from the peer median.
* :attr:`AlertKind.SELL_OUTLIER` — same for ``sell``.
* :attr:`AlertKind.STALE_QUOTE` — bank's most-recent quote is older
  than ``stale_threshold`` minutes relative to a reference clock.

All of the above are intentionally event-time / reference-clock
based; nothing pulls wall-clock.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from statistics import median
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fxagg.schema import Bank, Currency, Quote


class AlertKind(str, Enum):
    """Cross-bank FX-spread anomaly kinds."""

    INVERTED_SPREAD = "INVERTED_SPREAD"
    BUY_OUTLIER = "BUY_OUTLIER"
    SELL_OUTLIER = "SELL_OUTLIER"
    STALE_QUOTE = "STALE_QUOTE"


class Severity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    CRIT = "CRIT"


@dataclass(frozen=True, slots=True)
class Alert:
    kind: AlertKind
    severity: Severity
    bank: Bank
    currency: Currency
    detail: str
    deviation_pct: float | None = None


@dataclass(frozen=True, slots=True)
class CurrencyAnalysis:
    """The peer-comparison view of one currency at one moment."""

    currency: Currency
    bank_quotes: dict[Bank, Quote]
    median_buy_transfer: int
    median_sell: int
    median_bid_ask_pct: float
    alerts: tuple[Alert, ...] = field(default_factory=tuple)


def _pct_dev(value: int, ref: int) -> float:
    if ref == 0:
        return 0.0
    return (value - ref) / ref * 100


def analyze(
    bank_quotes: dict[Bank, Quote],
    *,
    outlier_pct: float = 1.0,
    stale_threshold_min: int = 30,
    reference_time: datetime | None = None,
) -> CurrencyAnalysis:
    """Run the four anomaly rules across a set of one-currency quotes."""
    if not bank_quotes:
        from fxagg.schema import Currency as _Currency

        # Empty input → empty analysis with first-defined currency placeholder.
        placeholder = next(iter(_Currency))
        return CurrencyAnalysis(
            currency=placeholder,
            bank_quotes={},
            median_buy_transfer=0,
            median_sell=0,
            median_bid_ask_pct=0.0,
        )

    currencies = {q.currency for q in bank_quotes.values()}
    if len(currencies) != 1:
        raise ValueError(f"analyze() requires one currency, got {currencies}")
    currency = next(iter(currencies))

    buys = sorted(q.buy_transfer_vnd for q in bank_quotes.values())
    sells = sorted(q.sell_vnd for q in bank_quotes.values())
    med_buy = int(median(buys))
    med_sell = int(median(sells))
    med_bid_ask_pct = float(median(q.bid_ask_spread_pct for q in bank_quotes.values()))

    alerts: list[Alert] = []
    for bank, q in bank_quotes.items():
        if q.bid_ask_spread_vnd < 0:
            alerts.append(
                Alert(
                    kind=AlertKind.INVERTED_SPREAD,
                    severity=Severity.CRIT,
                    bank=bank,
                    currency=currency,
                    detail=(
                        f"{bank.value} {currency.value}: sell={q.sell_vnd:,} < "
                        f"buy_transfer={q.buy_transfer_vnd:,} — broken row"
                    ),
                )
            )
            continue
        if len(bank_quotes) >= 3:
            dev_buy = _pct_dev(q.buy_transfer_vnd, med_buy)
            dev_sell = _pct_dev(q.sell_vnd, med_sell)
            if abs(dev_buy) >= outlier_pct:
                alerts.append(
                    Alert(
                        kind=AlertKind.BUY_OUTLIER,
                        severity=Severity.WARN,
                        bank=bank,
                        currency=currency,
                        detail=(
                            f"{bank.value} {currency.value}: buy_transfer={q.buy_transfer_vnd:,} "
                            f"vs peer median {med_buy:,} ({dev_buy:+.2f}%)"
                        ),
                        deviation_pct=dev_buy,
                    )
                )
            if abs(dev_sell) >= outlier_pct:
                alerts.append(
                    Alert(
                        kind=AlertKind.SELL_OUTLIER,
                        severity=Severity.WARN,
                        bank=bank,
                        currency=currency,
                        detail=(
                            f"{bank.value} {currency.value}: sell={q.sell_vnd:,} "
                            f"vs peer median {med_sell:,} ({dev_sell:+.2f}%)"
                        ),
                        deviation_pct=dev_sell,
                    )
                )
        if reference_time is not None:
            age = reference_time - q.quoted_at
            if age > timedelta(minutes=stale_threshold_min):
                alerts.append(
                    Alert(
                        kind=AlertKind.STALE_QUOTE,
                        severity=Severity.INFO,
                        bank=bank,
                        currency=currency,
                        detail=(
                            f"{bank.value} {currency.value} not updated for {age}; "
                            f"threshold {stale_threshold_min} min"
                        ),
                    )
                )

    alerts.sort(key=lambda a: (a.kind.value, a.bank.value))
    return CurrencyAnalysis(
        currency=currency,
        bank_quotes=dict(bank_quotes),
        median_buy_transfer=med_buy,
        median_sell=med_sell,
        median_bid_ask_pct=med_bid_ask_pct,
        alerts=tuple(alerts),
    )


__all__ = ["Alert", "AlertKind", "CurrencyAnalysis", "Severity", "analyze"]
