"""VN-Index / VN30 / HNX-Index calculation — market-cap-weighted.

The official VN-Index is a **modified Paasche** index against a
fixed base (28 Jul 2000 = 100). For our purposes we expose the
ratio directly: ``Σ(price × listed_shares) / Σ(prev_price × listed_shares)``
times the base divisor. Callers pin the divisor at index-genesis or
rebalance time; the pipeline is otherwise stateless.

Three flavours:

* :func:`vn_index`   — all HOSE-listed symbols.
* :func:`vn30_index` — top-30 by market cap (caller supplies the list).
* :func:`hnx_index`  — all HNX-listed symbols.

All three share the same underlying ``compute_index`` — they're just
different filter functions over the universe.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from vntick.schema import Exchange

if TYPE_CHECKING:
    from vntick.schema import Symbol


def compute_index(
    last_prices: dict[str, int],
    symbols: dict[str, Symbol],
    universe: set[str],
    base_divisor: float = 1.0,
) -> float:
    """Sum-of-market-cap of ``universe`` divided by ``base_divisor``.

    A symbol present in ``universe`` but missing from ``last_prices``
    or ``symbols`` is silently skipped (a halted symbol on index day
    is what the official methodology does too).
    """
    if base_divisor <= 0:
        raise ValueError("base_divisor must be > 0")
    total_cap = 0
    for code in universe:
        price = last_prices.get(code)
        sym = symbols.get(code)
        if price is None or sym is None:
            continue
        total_cap += price * sym.listed_shares
    return total_cap / base_divisor


def vn_index(
    last_prices: dict[str, int], symbols: dict[str, Symbol], base_divisor: float = 1.0
) -> float:
    """All HOSE-listed names."""
    universe = {code for code, sym in symbols.items() if sym.exchange is Exchange.HOSE}
    return compute_index(last_prices, symbols, universe, base_divisor)


def vn30_index(
    last_prices: dict[str, int],
    symbols: dict[str, Symbol],
    vn30_codes: set[str],
    base_divisor: float = 1.0,
) -> float:
    """The 30 HOSE blue-chips the index committee picks each quarter.

    Caller supplies the membership list (we don't try to derive it
    from market cap — the official methodology has additional liquidity
    and free-float filters we don't model).
    """
    if not vn30_codes:
        raise ValueError("vn30_codes must be non-empty")
    return compute_index(last_prices, symbols, vn30_codes, base_divisor)


def hnx_index(
    last_prices: dict[str, int], symbols: dict[str, Symbol], base_divisor: float = 1.0
) -> float:
    """All HNX-listed names."""
    universe = {code for code, sym in symbols.items() if sym.exchange is Exchange.HNX}
    return compute_index(last_prices, symbols, universe, base_divisor)


__all__ = ["compute_index", "hnx_index", "vn30_index", "vn_index"]
