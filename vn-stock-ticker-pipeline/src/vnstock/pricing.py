"""Price-band / tick-size / lot-size validators.

Every VN equity order must satisfy three constraints set by the
exchange:

1. **Lot size** — quantity must be a multiple of the exchange's lot
   (100 shares since 2017).
2. **Tick size** — limit price must be a multiple of the exchange-
   and price-tier-specific tick.
3. **Price band** — limit price must lie within
   ``[floor, ceiling]`` derived from the previous close.

The HOSE tick size is *price-dependent*:

| Price range (VND)  | Tick (VND) |
| ------------------ | ---------- |
| < 10 000           | 10         |
| 10 000 – 49 950    | 50         |
| ≥ 50 000           | 100        |

HNX and UPCoM use a flat 100 VND tick.

We expose:

* ``tick_size(price, exchange)`` — the applicable tick at this price.
* ``round_to_tick(price, exchange)`` — snap a raw price to the grid.
* ``is_valid_tick(price, exchange)`` — strict check.
* ``ceiling_floor(reference, exchange, is_ipo_day)`` — return the
  tradable price range for the day, rounded to tick.
* ``is_within_band(price, reference, exchange, is_ipo_day)``.
* ``is_valid_lot(quantity, exchange)``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vnstock.exchanges import profile_for

if TYPE_CHECKING:
    from vnstock.schema import Exchange

# HOSE tier boundaries.
_HOSE_TIER_1_UPPER = 10_000  # below this → 10 VND tick
_HOSE_TIER_2_UPPER = 50_000  # below this → 50 VND tick (else 100)


def tick_size(price_vnd: int, exchange: Exchange) -> int:
    """Return the applicable tick (in VND) at the given price."""
    if price_vnd <= 0:
        raise ValueError(f"price_vnd must be > 0, got {price_vnd}")
    profile = profile_for(exchange)
    if profile.flat_tick_vnd > 0:
        return profile.flat_tick_vnd
    # HOSE multi-tier:
    if price_vnd < _HOSE_TIER_1_UPPER:
        return 10
    if price_vnd < _HOSE_TIER_2_UPPER:
        return 50
    return 100


def round_to_tick(price_vnd: int, exchange: Exchange, *, mode: str = "down") -> int:
    """Snap ``price_vnd`` to the exchange's tick grid.

    ``mode`` is ``"down"`` (floor), ``"up"`` (ceiling), or ``"nearest"``.
    """
    if mode not in {"down", "up", "nearest"}:
        raise ValueError(f"mode must be down/up/nearest, got {mode!r}")
    tick = tick_size(price_vnd, exchange)
    if mode == "down":
        return (price_vnd // tick) * tick
    if mode == "up":
        return -(-price_vnd // tick) * tick  # ceil division
    # nearest
    quotient, remainder = divmod(price_vnd, tick)
    if remainder * 2 >= tick:
        return (quotient + 1) * tick
    return quotient * tick


def is_valid_tick(price_vnd: int, exchange: Exchange) -> bool:
    """``True`` iff ``price_vnd`` lies exactly on the tick grid."""
    if price_vnd <= 0:
        return False
    tick = tick_size(price_vnd, exchange)
    return price_vnd % tick == 0


def is_valid_lot(quantity: int, exchange: Exchange) -> bool:
    """``True`` iff ``quantity`` is a positive multiple of the lot size."""
    if quantity <= 0:
        return False
    profile = profile_for(exchange)
    return quantity % profile.lot_size == 0


def ceiling_floor(
    reference_price_vnd: int,
    exchange: Exchange,
    *,
    is_ipo_day: bool = False,
) -> tuple[int, int]:
    """Return ``(ceiling, floor)`` in VND for the day.

    Both values are snapped to the exchange's tick grid — ceiling
    rounded *down* (so trades can't land on a price above the
    regulator's stated band), floor rounded *up* (same reason).

    The band may collapse to a single tick when the reference price
    is very small; both bounds are guaranteed ``>= 0``.
    """
    if reference_price_vnd <= 0:
        raise ValueError(
            f"reference_price_vnd must be > 0, got {reference_price_vnd}",
        )
    profile = profile_for(exchange)
    band_bps = profile.ipo_band_bps if is_ipo_day else profile.price_band_bps
    raw_ceiling = (reference_price_vnd * (10_000 + band_bps) + 9_999) // 10_000
    raw_floor = (reference_price_vnd * (10_000 - band_bps)) // 10_000
    ceiling = round_to_tick(raw_ceiling, exchange, mode="down")
    floor = round_to_tick(max(raw_floor, 1), exchange, mode="up")
    return ceiling, floor


def is_within_band(
    price_vnd: int,
    reference_price_vnd: int,
    exchange: Exchange,
    *,
    is_ipo_day: bool = False,
) -> bool:
    """``True`` iff ``price_vnd`` is between today's floor and ceiling."""
    ceiling, floor = ceiling_floor(
        reference_price_vnd,
        exchange,
        is_ipo_day=is_ipo_day,
    )
    return floor <= price_vnd <= ceiling


__all__ = [
    "ceiling_floor",
    "is_valid_lot",
    "is_valid_tick",
    "is_within_band",
    "round_to_tick",
    "tick_size",
]
