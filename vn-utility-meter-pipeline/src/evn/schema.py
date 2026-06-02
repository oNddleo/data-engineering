"""EVN electricity meter-pipeline schema.

Models the core entities for VN domestic electricity billing as
administered by Tập đoàn Điện lực Việt Nam (EVN), the state-monopoly
utility. The retail tariff structure is set by the **Bộ Công Thương**
(Ministry of Industry and Trade) and adjusted periodically by EVN
decisions; we bundle the schedule effective from
**2023-11-09** per ``Decision 1416/QĐ-EVN``.

Customer categories per Decision 28/2014/QĐ-TTg + 80/2024/NĐ-CP:

| Category       | Pricing model                              |
| -------------- | ------------------------------------------ |
| HOUSEHOLD      | 6-tier progressive (the "bậc thang" model) |
| BUSINESS       | flat rate (commercial / services)          |
| ADMIN_PUBLIC   | flat rate (gov't offices, schools)         |
| PRODUCTION     | flat rate (industrial, low/medium volt)    |
| AGRICULTURE    | flat rate (lowest band, irrigation)        |

All money is **integer VND**. All dates are tz-naive ``date`` objects
(electricity billing is by calendar month, no timezone needed).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date

# 10% VAT per Decree 209/2013/NĐ-CP; electricity is excluded from the
# COVID-era 8% reduction (it stayed at 10%).
VAT_BPS = 1_000  # basis points, 10% = 1_000 bps


class CustomerCategory(str, Enum):
    """Five EVN customer categories covering ~99% of retail meters."""

    HOUSEHOLD = "HOUSEHOLD"
    BUSINESS = "BUSINESS"
    ADMIN_PUBLIC = "ADMIN_PUBLIC"
    PRODUCTION = "PRODUCTION"
    AGRICULTURE = "AGRICULTURE"


class AnomalyKind(str, Enum):
    """Three meter-reading anomaly classes."""

    ZERO_USAGE = "ZERO_USAGE"  # period with 0 kWh — possible vacancy or tampering
    SUDDEN_DROP = "SUDDEN_DROP"  # > 80% drop vs prior month average
    UNREALISTIC_SPIKE = "UNREALISTIC_SPIKE"  # > 5× the prior baseline


@dataclass(frozen=True, slots=True)
class MeterReading:
    """One billing-period meter reading for a customer.

    The customer code follows EVN's 13-character format ``PE`` + 11
    digits where the first two chars are the provincial unit code
    (``PA`` Hà Nội, ``PB`` Hải Phòng, ``PC`` Hồ Chí Minh, etc.). We
    validate the shape; the prefix–province mapping is bundled in
    ``evn.customer``.
    """

    customer_code: str
    category: CustomerCategory
    period_start: date
    period_end: date
    kwh_used: int

    def __post_init__(self) -> None:
        if not self.customer_code:
            raise ValueError("customer_code must be non-empty")
        if self.period_end < self.period_start:
            raise ValueError(
                f"period_end ({self.period_end}) must be >= period_start " f"({self.period_start})",
            )
        if self.kwh_used < 0:
            raise ValueError(f"kwh_used must be >= 0, got {self.kwh_used}")


@dataclass(frozen=True, slots=True)
class TierUsage:
    """One slice of usage within a single tariff tier — for itemised bills."""

    tier_index: int  # 1-based, matches EVN's bậc 1..6 labeling
    kwh: int
    rate_vnd_per_kwh: int
    amount_vnd: int

    def __post_init__(self) -> None:
        if self.tier_index < 1:
            raise ValueError(f"tier_index must be >= 1, got {self.tier_index}")
        if self.kwh < 0:
            raise ValueError(f"kwh must be >= 0, got {self.kwh}")
        if self.rate_vnd_per_kwh < 0:
            raise ValueError(
                f"rate_vnd_per_kwh must be >= 0, got {self.rate_vnd_per_kwh}",
            )
        if self.amount_vnd < 0:
            raise ValueError(f"amount_vnd must be >= 0, got {self.amount_vnd}")


@dataclass(frozen=True, slots=True)
class ElectricityBill:
    """A finalised invoice for one billing period.

    ``tier_breakdown`` is non-empty only for HOUSEHOLD bills (the
    flat-rate categories collapse to a single row).
    """

    customer_code: str
    category: CustomerCategory
    period_start: date
    period_end: date
    kwh_used: int
    pre_vat_amount_vnd: int
    vat_amount_vnd: int
    tier_breakdown: tuple[TierUsage, ...]

    def __post_init__(self) -> None:
        if self.pre_vat_amount_vnd < 0:
            raise ValueError("pre_vat_amount_vnd must be >= 0")
        if self.vat_amount_vnd < 0:
            raise ValueError("vat_amount_vnd must be >= 0")
        # Tier breakdown sum must equal pre-VAT amount (when present).
        if self.tier_breakdown:
            tier_sum = sum(t.amount_vnd for t in self.tier_breakdown)
            if tier_sum != self.pre_vat_amount_vnd:
                raise ValueError(
                    f"tier breakdown sums to {tier_sum} but "
                    f"pre_vat_amount_vnd={self.pre_vat_amount_vnd}",
                )
            tier_kwh = sum(t.kwh for t in self.tier_breakdown)
            if tier_kwh != self.kwh_used:
                raise ValueError(
                    f"tier kWh sums to {tier_kwh} but kwh_used={self.kwh_used}",
                )

    @property
    def total_amount_vnd(self) -> int:
        """Total bill (pre-VAT + VAT)."""
        return self.pre_vat_amount_vnd + self.vat_amount_vnd


@dataclass(frozen=True, slots=True)
class AnomalyFinding:
    """One ops-actionable meter-reading anomaly."""

    kind: AnomalyKind
    customer_code: str
    category: CustomerCategory
    detail: str
    metric: int  # signal-specific magnitude


__all__ = [
    "VAT_BPS",
    "AnomalyFinding",
    "AnomalyKind",
    "CustomerCategory",
    "ElectricityBill",
    "MeterReading",
    "TierUsage",
]
