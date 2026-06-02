"""Technical indicators over OHLCV bars — pure float math, no pandas.

All indicators operate on a chronologically-sorted list of bars for
**one symbol**. The output is aligned to the input — when there's
insufficient history (e.g. the first ``period-1`` bars for an SMA),
the entry is ``None``. Callers can filter or pad as they like.

Implemented indicators:

* **SMA** — simple moving average over the close price.
* **EMA** — exponential moving average, ``α = 2 / (period + 1)``.
* **RSI** — Wilder's 14-period (or any period) relative strength index.
* **MACD** — 12/26/9 EMA-of-EMA convergence + signal + histogram.
* **Bollinger Bands** — 20-period SMA ± 2 σ.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vntick.schema import OHLCVBar


def _closes(bars: list[OHLCVBar]) -> list[int]:
    return [b.close_vnd for b in bars]


def sma(bars: list[OHLCVBar], period: int) -> list[float | None]:
    """Simple moving average over close. First ``period-1`` outputs are ``None``."""
    if period < 1:
        raise ValueError("period must be >= 1")
    closes = _closes(bars)
    out: list[float | None] = [None] * len(closes)
    if len(closes) < period:
        return out
    running = sum(closes[:period])
    out[period - 1] = running / period
    for i in range(period, len(closes)):
        running += closes[i] - closes[i - period]
        out[i] = running / period
    return out


def ema(bars: list[OHLCVBar], period: int) -> list[float | None]:
    """Exponential moving average. Seeded with the first ``period``-bar SMA."""
    if period < 1:
        raise ValueError("period must be >= 1")
    closes = _closes(bars)
    out: list[float | None] = [None] * len(closes)
    if len(closes) < period:
        return out
    alpha = 2.0 / (period + 1)
    seed = sum(closes[:period]) / period
    out[period - 1] = seed
    prev = seed
    for i in range(period, len(closes)):
        prev = closes[i] * alpha + prev * (1 - alpha)
        out[i] = prev
    return out


def rsi(bars: list[OHLCVBar], period: int = 14) -> list[float | None]:
    """Wilder's RSI. Output range ``[0, 100]``. First ``period`` entries are ``None``.

    Uses Wilder's smoothed averaging, not the naive ratio — that's why
    the first usable index is ``period`` (not ``period - 1``).
    """
    if period < 2:
        raise ValueError("period must be >= 2")
    closes = _closes(bars)
    n = len(closes)
    out: list[float | None] = [None] * n
    if n <= period:
        return out
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, period + 1):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    out[period] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    for i in range(period + 1, n):
        change = closes[i] - closes[i - 1]
        gain = max(change, 0)
        loss = max(-change, 0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[i] = 100.0 if avg_loss == 0 else 100 - 100 / (1 + avg_gain / avg_loss)
    return out


@dataclass(frozen=True, slots=True)
class MACDPoint:
    """One point on the MACD curve."""

    macd: float
    signal: float
    histogram: float


def macd(
    bars: list[OHLCVBar],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> list[MACDPoint | None]:
    """MACD line = EMA(fast) − EMA(slow); signal = EMA(signal) of MACD.

    The histogram is ``macd − signal``. All three are aligned to the
    input length; pre-history bars produce ``None``.
    """
    if not 1 <= fast < slow:
        raise ValueError(f"need 1 <= fast ({fast}) < slow ({slow})")
    if signal < 1:
        raise ValueError("signal must be >= 1")
    ema_fast = ema(bars, fast)
    ema_slow = ema(bars, slow)
    n = len(bars)
    macd_line: list[float | None] = [None] * n
    for i in range(n):
        if ema_fast[i] is not None and ema_slow[i] is not None:
            macd_line[i] = ema_fast[i] - ema_slow[i]  # type: ignore[operator]
    # EMA-of-MACD for the signal line; need to skip leading Nones.
    out: list[MACDPoint | None] = [None] * n
    alpha = 2.0 / (signal + 1)
    # First index where macd_line is non-None for ``signal`` consecutive values.
    start: int | None = None
    for i, v in enumerate(macd_line):
        if v is None:
            continue
        if start is None:
            start = i
            break
    if start is None or start + signal > n:
        return out
    # Seed the signal EMA with an SMA of the first ``signal`` MACD values.
    seed_values = [v for v in macd_line[start : start + signal] if v is not None]
    if len(seed_values) < signal:
        return out
    sig_prev = sum(seed_values) / signal
    seed_idx = start + signal - 1
    m_seed = macd_line[seed_idx]
    if m_seed is not None:
        out[seed_idx] = MACDPoint(macd=m_seed, signal=sig_prev, histogram=m_seed - sig_prev)
    for i in range(seed_idx + 1, n):
        m = macd_line[i]
        if m is None:
            continue
        sig_prev = m * alpha + sig_prev * (1 - alpha)
        out[i] = MACDPoint(macd=m, signal=sig_prev, histogram=m - sig_prev)
    return out


@dataclass(frozen=True, slots=True)
class BollingerBand:
    """One slice of Bollinger Bands: middle SMA + upper/lower σ-bands."""

    middle: float
    upper: float
    lower: float


def bollinger(
    bars: list[OHLCVBar], period: int = 20, n_std: float = 2.0
) -> list[BollingerBand | None]:
    """Bollinger Bands: ``SMA ± n_std × σ`` of the close.

    ``σ`` is the *population* std-dev over the ``period`` window (the
    convention every charting library uses).
    """
    if period < 2:
        raise ValueError("period must be >= 2")
    if n_std <= 0:
        raise ValueError("n_std must be > 0")
    closes = _closes(bars)
    out: list[BollingerBand | None] = [None] * len(closes)
    if len(closes) < period:
        return out
    for i in range(period - 1, len(closes)):
        window = closes[i - period + 1 : i + 1]
        mean = sum(window) / period
        var = sum((c - mean) ** 2 for c in window) / period
        sigma = math.sqrt(var)
        out[i] = BollingerBand(
            middle=mean,
            upper=mean + n_std * sigma,
            lower=mean - n_std * sigma,
        )
    return out


__all__ = [
    "BollingerBand",
    "MACDPoint",
    "bollinger",
    "ema",
    "macd",
    "rsi",
    "sma",
]
