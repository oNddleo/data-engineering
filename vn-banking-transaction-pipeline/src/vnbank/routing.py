"""Interbank routing — NAPAS-247 instant rail vs Citad RTGS.

A VN domestic transfer is routed according to **amount** and **bank pair**:

* **Same bank**  → handled in-house; no NAPAS hop. Settlement is
  instant, fee is typically zero.
* **Different banks, ≤ NAPAS_247_MAX_VND** → NAPAS-247 (24/7 instant
  retail rail). Receiver gets funds in seconds.
* **Different banks, > NAPAS_247_MAX_VND** → Citad (SBV's RTGS).
  Settled at the next clearing window (4 per business day).

The per-transaction cap on NAPAS-247 was raised to **500,000,000 VND**
on 2024-07-01 (SBV Decision 1085/QĐ-NHNN). We hard-code that figure
rather than reading it from config — the change rate is once per
~5 years.

We surface the routing decision via ``RouteDecision`` so the simulator
+ AML modules can reason about it without re-implementing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from vnbank.banks import profile_for_bin

# Updated 2024-07-01 per SBV Decision 1085/QĐ-NHNN.
NAPAS_247_MAX_VND = 500_000_000


class Rail(str, Enum):
    """Settlement rail for one transfer."""

    INTRA_BANK = "INTRA_BANK"  # in-house, same bank both sides
    NAPAS_247 = "NAPAS_247"  # 24/7 instant interbank
    CITAD = "CITAD"  # SBV RTGS, batch clearing


@dataclass(frozen=True, slots=True)
class RouteDecision:
    """The chosen rail + the fee charged to the sender, in VND."""

    rail: Rail
    fee_vnd: int


def route(
    sender_bank_bin: str,
    receiver_bank_bin: str,
    amount_vnd: int,
) -> RouteDecision:
    """Choose the settlement rail + compute the sender's fee."""
    if amount_vnd < 0:
        raise ValueError(f"amount_vnd must be >= 0, got {amount_vnd}")
    if not sender_bank_bin or not receiver_bank_bin:
        raise ValueError("both bank BINs must be non-empty")

    if sender_bank_bin == receiver_bank_bin:
        return RouteDecision(rail=Rail.INTRA_BANK, fee_vnd=0)

    # Sanity-check both banks are known to NAPAS.
    if profile_for_bin(sender_bank_bin) is None:
        raise ValueError(f"unknown sender bank BIN {sender_bank_bin!r}")
    if profile_for_bin(receiver_bank_bin) is None:
        raise ValueError(f"unknown receiver bank BIN {receiver_bank_bin!r}")

    if amount_vnd <= NAPAS_247_MAX_VND:
        return RouteDecision(rail=Rail.NAPAS_247, fee_vnd=_napas_fee(amount_vnd))
    return RouteDecision(rail=Rail.CITAD, fee_vnd=_citad_fee(amount_vnd))


def _napas_fee(amount_vnd: int) -> int:
    """Typical retail NAPAS-247 fee schedule (2025 market-blended).

    * Up to 1M VND   → free at most consumer banks (post-2024 SBV push)
    * 1M – 100M VND  → 5,000 VND flat
    * 100M – 500M    → 0.01% (capped at 50,000)
    """
    if amount_vnd <= 1_000_000:
        return 0
    if amount_vnd <= 100_000_000:
        return 5_000
    return min(50_000, max(11_000, amount_vnd // 10_000))


def _citad_fee(amount_vnd: int) -> int:
    """Citad RTGS fee (0.02% capped at 1,000,000 VND, SBV schedule)."""
    return min(1_000_000, max(20_000, amount_vnd // 5_000))


__all__ = [
    "NAPAS_247_MAX_VND",
    "Rail",
    "RouteDecision",
    "route",
]
