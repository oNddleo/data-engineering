"""Anomaly detection: circuit-breaker hits + unusual volume.

Two anomalies VN ops cares about:

* **Circuit-breaker hit** — the last trade hit the daily ``ceiling`` or
  ``floor`` price for the symbol's exchange. HOSE is ±7% from the
  previous-day close, HNX ±10%, UPCoM ±15%.
* **Unusual volume** — today's volume so far is more than ``k × σ``
  above the trailing-N-day mean. Default ``k = 3`` (3-sigma).

Both detectors are pure functions over ``OHLCVBar`` lists + reference
data (``previous_close`` for circuit breakers, a history window for
unusual volume).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

from vntick.schema import Exchange, ceiling_price, floor_price

if TYPE_CHECKING:
    from vntick.schema import OHLCVBar


class AnomalyKind(str, Enum):
    """One per detector."""

    CEILING_HIT = "CEILING_HIT"
    FLOOR_HIT = "FLOOR_HIT"
    UNUSUAL_VOLUME = "UNUSUAL_VOLUME"


@dataclass(frozen=True, slots=True)
class Anomaly:
    """One ops-actionable market anomaly."""

    kind: AnomalyKind
    code: str
    detected_at: datetime
    metric: int  # for CEILING/FLOOR: the price; for UNUSUAL_VOLUME: the volume
    detail: str


def find_circuit_breaker_hits(
    bars: list[OHLCVBar],
    previous_close: dict[str, int],
    exchanges: dict[str, Exchange],
) -> list[Anomaly]:
    """Flag every bar that printed at the ceiling or floor price.

    ``previous_close`` and ``exchanges`` are reference data keyed by
    symbol code. Symbols missing from either map are silently skipped
    — that's expected behaviour during cold-start (no prior session
    yet).
    """
    out: list[Anomaly] = []
    for bar in bars:
        prev = previous_close.get(bar.code)
        exch = exchanges.get(bar.code)
        if prev is None or exch is None:
            continue
        ceiling = ceiling_price(prev, exch)
        floor = floor_price(prev, exch)
        if bar.high_vnd >= ceiling:
            out.append(
                Anomaly(
                    kind=AnomalyKind.CEILING_HIT,
                    code=bar.code,
                    detected_at=bar.bar_start,
                    metric=ceiling,
                    detail=f"high={bar.high_vnd} hit ceiling={ceiling} (prev close={prev}, {exch.value})",
                )
            )
        if bar.low_vnd <= floor:
            out.append(
                Anomaly(
                    kind=AnomalyKind.FLOOR_HIT,
                    code=bar.code,
                    detected_at=bar.bar_start,
                    metric=floor,
                    detail=f"low={bar.low_vnd} hit floor={floor} (prev close={prev}, {exch.value})",
                )
            )
    return out


def find_unusual_volume(
    today_volume: dict[str, int],
    history: dict[str, list[int]],
    sigma: float = 3.0,
) -> list[Anomaly]:
    """Flag symbols whose today's volume is > ``mean + sigma × std``.

    ``history`` is a list of recent daily volumes per symbol. We need
    at least 5 history points to compute a stable mean / std — symbols
    with shorter history are skipped (cold-start tolerance).
    """
    if sigma <= 0:
        raise ValueError("sigma must be > 0")
    out: list[Anomaly] = []
    for code, today in today_volume.items():
        hist = history.get(code, [])
        if len(hist) < 5:
            continue
        mean = sum(hist) / len(hist)
        var = sum((v - mean) ** 2 for v in hist) / len(hist)
        std = math.sqrt(var)
        if std == 0:
            continue
        z = (today - mean) / std
        if z >= sigma:
            out.append(
                Anomaly(
                    kind=AnomalyKind.UNUSUAL_VOLUME,
                    code=code,
                    detected_at=datetime.min,  # caller fills in if needed
                    metric=today,
                    detail=f"vol={today} z={z:.2f} (mean={mean:.0f}, std={std:.0f})",
                )
            )
    return out


__all__ = ["Anomaly", "AnomalyKind", "find_circuit_breaker_hits", "find_unusual_volume"]
