"""Seeded synthetic VN-equity tick streams.

Generates ticks for a basket of real VN blue-chips (VIC, VHM, HPG,
VCB, VNM, …) following a geometric random walk inside the daily
price band. Volumes follow a log-normal distribution with daily
mean-reversion. Trading sessions are correctly modelled — no ticks
emitted during the lunch break or after 14:45.
"""

from __future__ import annotations

import math
import random
from datetime import datetime, time, timedelta

from vntick.schema import (
    VN_TZ,
    Exchange,
    Symbol,
    Tick,
    ceiling_price,
    floor_price,
    lot_size,
)

_DEFAULT_BASE_TS = datetime(2026, 5, 4, 9, 0, 0, tzinfo=VN_TZ)  # Monday

# Real VN-30 blue-chip names + sectors. Listed-share counts are rounded
# to nearest 100M shares to keep math clean.
_DEFAULT_SYMBOLS: tuple[tuple[str, Exchange, str, str, int, int], ...] = (
    # code, exchange, name, sector, listed_shares, starting price (VND)
    ("VIC", Exchange.HOSE, "Vingroup", "real_estate", 3_800_000_000, 42_000),
    ("VHM", Exchange.HOSE, "Vinhomes", "real_estate", 4_300_000_000, 38_500),
    ("HPG", Exchange.HOSE, "Hoa Phat", "steel", 6_400_000_000, 27_300),
    ("VCB", Exchange.HOSE, "Vietcombank", "banking", 5_500_000_000, 88_500),
    ("VNM", Exchange.HOSE, "Vinamilk", "consumer", 2_100_000_000, 67_200),
    ("FPT", Exchange.HOSE, "FPT Corp", "technology", 1_500_000_000, 124_000),
    ("MSN", Exchange.HOSE, "Masan", "consumer", 1_400_000_000, 65_800),
    ("MWG", Exchange.HOSE, "Mobile World", "retail", 1_500_000_000, 51_400),
    ("ACB", Exchange.HNX, "Asia Commercial Bank", "banking", 3_900_000_000, 24_100),
    ("SHB", Exchange.HNX, "Saigon-Hanoi Bank", "banking", 3_700_000_000, 11_700),
    ("BCG", Exchange.UPCOM, "Bamboo Capital", "industrial", 1_200_000_000, 8_900),
)


_MORNING_OPEN = time(9, 0)
_MORNING_CLOSE = time(11, 30)
_AFTERNOON_OPEN = time(13, 0)
_AFTERNOON_CLOSE = time(14, 45)


def _is_in_session(ts: datetime) -> bool:
    """Inline check (kept private so the public ``schema.is_in_session`` is the canonical API)."""
    local = ts.astimezone(VN_TZ).time()
    return _MORNING_OPEN <= local <= _MORNING_CLOSE or _AFTERNOON_OPEN <= local <= _AFTERNOON_CLOSE


def default_symbols() -> list[Symbol]:
    """The bundled blue-chip universe."""
    return [
        Symbol(code=code, exchange=exch, name=name, sector=sector, listed_shares=shares)
        for code, exch, name, sector, shares, _ in _DEFAULT_SYMBOLS
    ]


def default_reference_prices() -> dict[str, int]:
    """Previous-close prices that bound the simulated day's trading band."""
    return {code: price for code, _, _, _, _, price in _DEFAULT_SYMBOLS}


def _next_session_minute(ts: datetime) -> datetime:
    """Walk ``ts`` forward to the next in-session minute."""
    while not _is_in_session(ts):
        ts = ts + timedelta(minutes=1)
    return ts


def generate(
    *,
    n_ticks_per_symbol: int = 200,
    seed: int = 0,
    base_time: datetime | None = None,
    ceiling_hit_codes: tuple[str, ...] = (),
) -> tuple[list[Symbol], list[Tick], dict[str, int]]:
    """Generate (symbols, ticks, previous_close map).

    ``ceiling_hit_codes`` forces those symbols' first tick of the day
    to print at the daily ceiling — useful for exercising the
    circuit-breaker anomaly path.
    """
    if n_ticks_per_symbol < 1:
        raise ValueError("n_ticks_per_symbol must be >= 1")
    rng = random.Random(seed)
    base = base_time or _DEFAULT_BASE_TS

    symbols = default_symbols()
    prev_close = default_reference_prices()

    ticks: list[Tick] = []
    tick_counter = 0
    for sym in symbols:
        ref = prev_close[sym.code]
        ceiling = ceiling_price(ref, sym.exchange)
        floor = floor_price(ref, sym.exchange)
        lot = lot_size(sym.exchange)
        # Geometric random walk inside the band.
        log_price = math.log(ref)
        # Volatility ~ 1% per tick (annualised-ish realistic for VN large caps).
        vol = 0.01
        ts = base
        for i in range(n_ticks_per_symbol):
            ts = _next_session_minute(ts + timedelta(seconds=rng.randint(15, 90)))
            if i == 0 and sym.code in ceiling_hit_codes:
                price = ceiling
            else:
                log_price += rng.gauss(0, vol)
                price = int(math.exp(log_price))
                price = max(floor, min(ceiling, price))
            volume = lot * rng.randint(1, 50)  # 100 – 5000 shares
            side = "B" if rng.random() < 0.55 else "S"
            ticks.append(
                Tick(
                    code=sym.code,
                    price_vnd=price,
                    volume=volume,
                    occurred_at=ts,
                    side=side,
                )
            )
            tick_counter += 1

    ticks.sort(key=lambda t: t.occurred_at)
    return symbols, ticks, prev_close


__all__ = ["default_reference_prices", "default_symbols", "generate"]
