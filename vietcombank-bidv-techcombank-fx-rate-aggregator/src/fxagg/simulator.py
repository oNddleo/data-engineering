"""Seeded synthetic FX-quote generator for tests + local demos.

Reproducibility is the point: a fixed ``seed`` makes the output
identical across runs, so the test suite can pin expected alerts.
Optionally inject one or more anomaly kinds — outlier, inverted
spread, stale quote — to exercise rule behaviour end-to-end.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from fxagg.schema import VN_TZ, Bank, Currency, Quote

if TYPE_CHECKING:
    from collections.abc import Iterable

_DEFAULT_BASE_TS = datetime(2026, 5, 14, 9, 0, 0, tzinfo=VN_TZ)


# Approximate market mid-prices in VND per unit, mid-2026 era.
_MID: dict[Currency, int] = {
    Currency.USD: 25_000,
    Currency.EUR: 27_000,
    Currency.JPY: 170,  # JPY rates are usually quoted per 1 JPY
    Currency.GBP: 31_500,
    Currency.AUD: 16_500,
    Currency.SGD: 18_500,
    Currency.CNY: 3_500,
    Currency.KRW: 19,  # tiny rate
    Currency.THB: 700,
    Currency.HKD: 3_200,
    Currency.CAD: 18_000,
}


def _bank_jitter(rng: random.Random, mid: int) -> tuple[int, int]:
    """Return (buy_transfer, sell) with a typical 0.5–1.0% spread around mid."""
    spread_pct = rng.uniform(0.005, 0.012)
    half = mid * spread_pct / 2
    return int(mid - half), int(mid + half)


def quote(
    rng: random.Random,
    *,
    bank: Bank,
    currency: Currency,
    occurred_at: datetime,
    override_buy: int | None = None,
    override_sell: int | None = None,
) -> Quote:
    mid = _MID[currency]
    buy, sell = _bank_jitter(rng, mid)
    if override_buy is not None:
        buy = override_buy
    if override_sell is not None:
        sell = override_sell
    return Quote(
        bank=bank,
        currency=currency,
        buy_transfer_vnd=buy,
        sell_vnd=sell,
        quoted_at=occurred_at,
        buy_cash_vnd=max(1, buy - rng.randint(20, 80)),
    )


def generate(
    *,
    banks: Iterable[Bank] = (Bank.VCB, Bank.BIDV, Bank.TCB, Bank.MB, Bank.VPB),
    currencies: Iterable[Currency] = (Currency.USD, Currency.EUR, Currency.JPY),
    n_snapshots: int = 3,
    interval_minutes: int = 5,
    seed: int = 0,
    base_time: datetime | None = None,
    inject_anomalies: Iterable[str] = (),
) -> list[Quote]:
    """Return a flat list of quotes across ``banks × currencies × n_snapshots``.

    Anomaly kinds:

    * ``"outlier_buy"``  — last snapshot, first bank, push buy +5 %.
    * ``"outlier_sell"`` — last snapshot, first bank, push sell +5 %.
    * ``"inverted"``     — last snapshot, last bank, sell < buy.
    * ``"stale"``        — *drop* the last snapshot for the last bank.
    """
    rng = random.Random(seed)
    base = base_time or _DEFAULT_BASE_TS
    banks_l = list(banks)
    currencies_l = list(currencies)
    anomalies = list(inject_anomalies)

    quotes: list[Quote] = []
    for snap_i in range(n_snapshots):
        ts = base + timedelta(minutes=interval_minutes * snap_i)
        for bank in banks_l:
            is_last_snapshot = snap_i == n_snapshots - 1
            is_first_bank = bank is banks_l[0]
            is_last_bank = bank is banks_l[-1]
            if is_last_snapshot and "stale" in anomalies and is_last_bank:
                continue
            for currency in currencies_l:
                ov_buy: int | None = None
                ov_sell: int | None = None
                if is_last_snapshot and is_first_bank and currency is currencies_l[0]:
                    mid = _MID[currency]
                    if "outlier_buy" in anomalies:
                        # Bump buy + sell together so the row stays non-inverted;
                        # otherwise INVERTED_SPREAD would short-circuit the outlier rule.
                        ov_buy = int(mid * 1.05)
                        ov_sell = int(mid * 1.07)
                    if "outlier_sell" in anomalies:
                        ov_sell = int(mid * 1.05)
                if is_last_snapshot and is_last_bank and "inverted" in anomalies:
                    mid = _MID[currency]
                    ov_buy = int(mid * 1.01)
                    ov_sell = int(mid * 0.99)
                quotes.append(
                    quote(
                        rng,
                        bank=bank,
                        currency=currency,
                        occurred_at=ts,
                        override_buy=ov_buy,
                        override_sell=ov_sell,
                    )
                )
    for a in anomalies:
        if a not in {"outlier_buy", "outlier_sell", "inverted", "stale"}:
            raise ValueError(f"unknown anomaly kind: {a!r}")
    return quotes


__all__ = ["generate", "quote"]
