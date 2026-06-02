"""Synthetic OHLC bar generator across the 3 VN exchanges.

Generates ``n_days`` of daily bars for ``n_tickers`` constituents
drawn from the bundled ticker registry. Each ticker walks a
geometric-brownian-style price path inside its exchange's band:

* Daily move ~ N(0, σ) where σ = 0.015 (1.5%)
* Move clipped to ±0.9 × band on extreme draws (so the walk
  *almost* never breaches the band naturally — the simulator can
  inject explicit breaches via ``breach_fraction``)
* Daily volume log-normal around 200k shares, multiplied by spike
  cohort

Configurable anomaly cohorts:

* ``breach_fraction`` — fraction of (ticker, day) cells that produce
  a deliberate price-band breach
* ``spike_fraction`` — fraction of (ticker, day) cells that produce
  a 10× volume spike
"""

from __future__ import annotations

import math
import random
from datetime import date, timedelta

from vnstock.exchanges import profile_for
from vnstock.schema import Exchange, OHLCBar
from vnstock.tickers import all_tickers


def generate(
    *,
    n_tickers: int = 20,
    n_days: int = 30,
    start_date: date | None = None,
    breach_fraction: float = 0.01,
    spike_fraction: float = 0.05,
    initial_price_low: int = 10_000,
    initial_price_high: int = 200_000,
    seed: int = 0,
) -> list[OHLCBar]:
    """Generate ``n_days`` of daily OHLC bars for ``n_tickers`` constituents."""
    if n_tickers < 0:
        raise ValueError("n_tickers must be >= 0")
    if n_days < 1:
        raise ValueError("n_days must be >= 1")
    for name, frac in (
        ("breach_fraction", breach_fraction),
        ("spike_fraction", spike_fraction),
    ):
        if not 0 <= frac <= 1:
            raise ValueError(f"{name} must be in [0, 1], got {frac}")
    if initial_price_low <= 0 or initial_price_high <= initial_price_low:
        raise ValueError("initial_price_low must be > 0 and < initial_price_high")

    rng = random.Random(seed)
    base = start_date or date(2025, 1, 6)  # a Monday

    # Pick the constituents from the bundled set.
    pool = list(all_tickers())
    rng.shuffle(pool)
    chosen = pool[: min(n_tickers, len(pool))]

    # Initial reference price per ticker.
    refs: dict[str, int] = {}
    for t in chosen:
        price = rng.randint(initial_price_low, initial_price_high)
        refs[t.symbol] = _snap_to_tick(price, t.exchange)

    bars: list[OHLCBar] = []
    for day_idx in range(n_days):
        # Skip weekends — Saturdays and Sundays don't trade.
        d = base + timedelta(days=day_idx)
        if d.weekday() >= 5:
            continue
        for t in chosen:
            ref = refs[t.symbol]
            band_bps = profile_for(t.exchange).price_band_bps
            # Daily fractional move drawn from a clipped gaussian.
            move_bps = int(rng.gauss(0, 150))  # ±~1.5%
            cap = int(band_bps * 0.9)
            move_bps = max(-cap, min(cap, move_bps))
            # 1% chance we deliberately breach the band.
            breach = rng.random() < breach_fraction
            if breach:
                # Push the close 1% outside the band.
                direction = rng.choice([1, -1])
                move_bps = direction * (band_bps + 100)

            new_ref = ref + (ref * move_bps) // 10_000
            new_ref = max(1, _snap_to_tick(new_ref, t.exchange))

            # Intraday spread (high-low) ~0.4× the move's magnitude.
            spread_bps = abs(move_bps) + rng.randint(30, 80)
            half_spread = (ref * spread_bps) // (2 * 10_000)
            open_p = _snap_to_tick(
                ref + (rng.randint(-half_spread, half_spread)),
                t.exchange,
            )
            close_p = new_ref
            high_p = _snap_to_tick(
                max(open_p, close_p) + rng.randint(0, half_spread or 1),
                t.exchange,
            )
            low_p = _snap_to_tick(
                max(1, min(open_p, close_p) - rng.randint(0, half_spread or 1)),
                t.exchange,
            )
            # Volume: log-normal with optional 10× spike.
            base_vol = int(math.exp(rng.normalvariate(12.5, 0.6)))  # ~200k
            volume = base_vol * 10 if rng.random() < spike_fraction else base_vol

            bars.append(
                OHLCBar(
                    symbol=t.symbol,
                    exchange=t.exchange,
                    date=d,
                    open_vnd=open_p,
                    high_vnd=high_p,
                    low_vnd=low_p,
                    close_vnd=close_p,
                    volume=volume,
                    reference_price_vnd=ref,
                )
            )
            refs[t.symbol] = close_p

    bars.sort(key=lambda b: (b.date, b.symbol))
    return bars


def _snap_to_tick(price: int, exchange: Exchange) -> int:
    from vnstock.pricing import round_to_tick

    return round_to_tick(price, exchange, mode="down")


__all__ = ["generate"]
