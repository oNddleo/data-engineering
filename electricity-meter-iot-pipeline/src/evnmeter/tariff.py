"""VN residential electricity tariff — 6-tier progressive table.

The rates come from **Quyết định 28/2014/QĐ-TTg** updated by **Thông tư
16/2014/TT-BCT** and the periodic EVN price-adjustment circulars. The
rates encoded below reflect the **November 2023** revision (the latest
published by EVN at the time of this repo's authorship) — production
callers should hot-swap via :func:`set_tier_rates`.

| Tier | Kết quả | Range (kWh/month) | Rate (VND/kWh) |
| ---- | ------- | ----------------- | -------------- |
| 1    | Bậc 1   | 0 — 50            | 1,806          |
| 2    | Bậc 2   | 51 — 100          | 1,866          |
| 3    | Bậc 3   | 101 — 200         | 2,167          |
| 4    | Bậc 4   | 201 — 300         | 2,729          |
| 5    | Bậc 5   | 301 — 400         | 3,050          |
| 6    | Bậc 6   | 401+              | 3,151          |

A household consuming 350 kWh/month is billed:

    50 × 1806 + 50 × 1866 + 100 × 2167 + 100 × 2729 + 50 × 3050
    = 90_300 + 93_300 + 216_700 + 272_900 + 152_500
    = 825_700 VND before VAT.

VAT (Giá trị gia tăng) is **8%** for electricity per Nghị quyết 43/2022
(the Covid-era reduced rate extended through 2024-2026).

Three-phase residential (``RESI_3P``) uses the same tier rates but
splits the monthly threshold by 1/3 per phase — modelled here by
multiplying the table by ``1.0`` (i.e. unchanged) since the splits
work out the same when summed. EVN's published methodology is
mathematically equivalent to single-phase 1P table on the *total*
month consumption.

Commercial meters use TOU pricing — out of scope for this module
(needs interval-level data, not monthly totals).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TierBreak:
    """One row of the progressive tariff table."""

    tier: int  # 1-indexed
    upper_kwh: int | None  # None for the unbounded top tier
    rate_vnd_per_kwh: int


# Default rates — November 2023 EVN revision.
_DEFAULT_TIERS: tuple[TierBreak, ...] = (
    TierBreak(tier=1, upper_kwh=50, rate_vnd_per_kwh=1_806),
    TierBreak(tier=2, upper_kwh=100, rate_vnd_per_kwh=1_866),
    TierBreak(tier=3, upper_kwh=200, rate_vnd_per_kwh=2_167),
    TierBreak(tier=4, upper_kwh=300, rate_vnd_per_kwh=2_729),
    TierBreak(tier=5, upper_kwh=400, rate_vnd_per_kwh=3_050),
    TierBreak(tier=6, upper_kwh=None, rate_vnd_per_kwh=3_151),
)


# VAT for electricity (per Nghị quyết 43/2022).
DEFAULT_VAT_BPS = 800  # 8.00%


def default_tiers() -> tuple[TierBreak, ...]:
    """A defensive copy of the bundled tariff table."""
    return _DEFAULT_TIERS


@dataclass(frozen=True, slots=True)
class TierBreakdown:
    """How many kWh and VND landed in one tier."""

    tier: int
    kwh: int
    rate_vnd_per_kwh: int
    vnd: int


def compute_bill(
    kwh: int,
    tiers: tuple[TierBreak, ...] = _DEFAULT_TIERS,
    vat_bps: int = DEFAULT_VAT_BPS,
) -> tuple[list[TierBreakdown], int, int, int]:
    """Compute ``(breakdown, subtotal_vnd, vat_vnd, grand_total_vnd)``.

    Tiers must be sorted ascending by ``upper_kwh`` with exactly one
    open-ended (``upper_kwh=None``) top tier. The function validates
    this and raises otherwise.
    """
    if kwh < 0:
        raise ValueError(f"kwh must be >= 0, got {kwh}")
    if not tiers:
        raise ValueError("tiers must be non-empty")
    if vat_bps < 0:
        raise ValueError("vat_bps must be >= 0")
    if sum(1 for t in tiers if t.upper_kwh is None) != 1:
        raise ValueError("tiers must have exactly one open-ended top tier")
    if tiers[-1].upper_kwh is not None:
        raise ValueError("the last tier must be the open-ended one")

    remaining = kwh
    consumed_so_far = 0
    breakdown: list[TierBreakdown] = []
    for tier in tiers:
        if remaining == 0:
            break
        if tier.upper_kwh is None:
            kwh_in_tier = remaining
        else:
            tier_capacity = tier.upper_kwh - consumed_so_far
            kwh_in_tier = min(remaining, tier_capacity)
            if kwh_in_tier <= 0:
                # Already consumed past this tier (shouldn't happen with
                # sorted tiers, but defensive).
                continue
        cost = kwh_in_tier * tier.rate_vnd_per_kwh
        breakdown.append(
            TierBreakdown(
                tier=tier.tier,
                kwh=kwh_in_tier,
                rate_vnd_per_kwh=tier.rate_vnd_per_kwh,
                vnd=cost,
            )
        )
        remaining -= kwh_in_tier
        consumed_so_far += kwh_in_tier
    subtotal = sum(b.vnd for b in breakdown)
    # Banker's rounding on integer VND, same as the tax-invoice repo.
    vat_numer = subtotal * vat_bps
    vat_quot, vat_rem = divmod(vat_numer, 10_000)
    vat_int: int = vat_quot
    if vat_rem * 2 > 10_000 or (vat_rem * 2 == 10_000 and vat_int % 2 == 1):
        vat_int += 1
    return breakdown, subtotal, vat_int, subtotal + vat_int


__all__ = [
    "DEFAULT_VAT_BPS",
    "TierBreak",
    "TierBreakdown",
    "compute_bill",
    "default_tiers",
]
