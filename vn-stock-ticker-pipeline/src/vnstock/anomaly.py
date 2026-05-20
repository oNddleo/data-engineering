"""OHLC-bar anomaly detection — three patterns market surveillance watches.

* **Price-band breach** — a bar's high or low went *beyond* the
  regulator-set band ``[floor, ceiling]`` derived from the
  reference price. This should be impossible in well-functioning
  matching — it indicates either a feed bug or a regulatory event.

* **Volume spike** — bar volume > ``multiplier`` × trailing average
  (default 5×, over the previous ``window`` bars). Indicates news /
  block trade / cornering.

* **Price gap** — open price > ``gap_bps`` away from the previous
  close (default 500 bps = ±5%). Open gaps inside the band are
  legitimate but ops-actionable on illiquid tickers.

All detectors need a per-ticker history of at least ``window``
trailing bars; tickers with shorter history are skipped.
"""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from vnstock.pricing import ceiling_floor
from vnstock.schema import AnomalyFinding, AnomalyKind

if TYPE_CHECKING:
    from vnstock.schema import OHLCBar


_MIN_HISTORY = 5


def find_band_breaches(bars: list[OHLCBar]) -> list[AnomalyFinding]:
    """Flag every bar whose high > ceiling or low < floor for its band."""
    out: list[AnomalyFinding] = []
    for b in bars:
        ceiling, floor = ceiling_floor(b.reference_price_vnd, b.exchange)
        if b.high_vnd > ceiling or b.low_vnd < floor:
            out.append(
                AnomalyFinding(
                    kind=AnomalyKind.PRICE_BAND_BREACH,
                    symbol=b.symbol,
                    exchange=b.exchange,
                    date=b.date,
                    detail=(
                        f"bar {b.symbol} {b.date.isoformat()}: "
                        f"range [{b.low_vnd}, {b.high_vnd}] "
                        f"vs band [{floor}, {ceiling}]"
                    ),
                    metric=max(
                        b.high_vnd - ceiling,
                        floor - b.low_vnd,
                    ),
                )
            )
    out.sort(key=lambda f: (-f.metric, f.symbol))
    return out


def find_volume_spikes(
    bars: list[OHLCBar],
    *,
    multiplier: float = 5.0,
    window: int = 5,
) -> list[AnomalyFinding]:
    """Surface bars whose volume exceeds ``multiplier`` × trailing average."""
    if multiplier <= 1.0:
        raise ValueError(f"multiplier must be > 1.0, got {multiplier}")
    if window < 1:
        raise ValueError(f"window must be >= 1, got {window}")

    per_ticker: dict[tuple[str, str], list[OHLCBar]] = defaultdict(list)
    for b in bars:
        per_ticker[(b.symbol, b.exchange.value)].append(b)

    out: list[AnomalyFinding] = []
    for series in per_ticker.values():
        series.sort(key=lambda b: b.date)
        if len(series) < window + 1:
            continue
        for i in range(window, len(series)):
            recent = series[i]
            avg = sum(s.volume for s in series[i - window : i]) // window
            if avg == 0:
                continue
            if recent.volume >= multiplier * avg:
                ratio = recent.volume // avg
                out.append(
                    AnomalyFinding(
                        kind=AnomalyKind.VOLUME_SPIKE,
                        symbol=recent.symbol,
                        exchange=recent.exchange,
                        date=recent.date,
                        detail=(
                            f"bar {recent.symbol} {recent.date.isoformat()}: "
                            f"volume {recent.volume} vs avg {avg} ({ratio}×)"
                        ),
                        metric=int(ratio),
                    )
                )
    out.sort(key=lambda f: (-f.metric, f.symbol, f.date))
    return out


def find_price_gaps(
    bars: list[OHLCBar],
    *,
    min_gap_bps: int = 500,
) -> list[AnomalyFinding]:
    """Surface bars whose open is ≥ ``min_gap_bps`` away from previous close."""
    if min_gap_bps <= 0:
        raise ValueError(f"min_gap_bps must be > 0, got {min_gap_bps}")

    per_ticker: dict[tuple[str, str], list[OHLCBar]] = defaultdict(list)
    for b in bars:
        per_ticker[(b.symbol, b.exchange.value)].append(b)

    out: list[AnomalyFinding] = []
    for series in per_ticker.values():
        series.sort(key=lambda b: b.date)
        for i in range(1, len(series)):
            prev_close = series[i - 1].close_vnd
            this_open = series[i].open_vnd
            gap_bps = abs(this_open - prev_close) * 10_000 // prev_close
            if gap_bps >= min_gap_bps:
                out.append(
                    AnomalyFinding(
                        kind=AnomalyKind.PRICE_GAP,
                        symbol=series[i].symbol,
                        exchange=series[i].exchange,
                        date=series[i].date,
                        detail=(
                            f"bar {series[i].symbol} {series[i].date.isoformat()}: "
                            f"open {this_open} vs prev close {prev_close} "
                            f"({gap_bps / 100:.1f}% gap)"
                        ),
                        metric=int(gap_bps),
                    )
                )
    out.sort(key=lambda f: (-f.metric, f.symbol, f.date))
    return out


__all__ = [
    "find_band_breaches",
    "find_price_gaps",
    "find_volume_spikes",
]
