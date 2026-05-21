"""Core domain types for VN petroleum pricing.

Reference: Decree 95/2021/ND-CP on petroleum business management.
The retail price is set every 10 days by the Ministry of Industry and Trade.

Retail price = Base price + Special Consumption Tax + Environmental Protection Tax
               + VAT + Dealer profit margin + Price stabilisation fund contribution
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FuelType(str, Enum):
    """Vietnam retail petroleum products."""

    RON95_III = "RON95-III"  # 95 octane gasoline (most common)
    RON92_II = "RON92-II"  # 92 octane gasoline (regular)
    DIESEL_005 = "DO0.05S"  # 0.05% sulfur diesel
    KEROSENE = "KEROSENE"  # lamp oil / jet fuel blend
    E5_RON92 = "E5-RON92"  # 5% ethanol blend


class PriceRegion(str, Enum):
    """Vietnam petroleum pricing regions (reflects transport cost)."""

    NORTH = "NORTH"  # Hanoi and northern provinces
    CENTRAL = "CENTRAL"  # Da Nang and central provinces
    SOUTH = "SOUTH"  # Ho Chi Minh City and southern provinces
    HIGHLANDS = "HIGHLANDS"  # Tay Nguyen / mountainous areas (higher transport)


@dataclass(frozen=True, slots=True)
class PriceInput:
    """Inputs for a single petroleum price calculation cycle."""

    fuel_type: FuelType
    region: PriceRegion
    # CIF price at Vietnamese port (USD/barrel) - from Platts Singapore
    cif_price_usd_per_barrel: float
    usd_to_vnd: float  # exchange rate
    # Optional overrides (if 0, use defaults)
    stabilisation_fund_vnd_per_litre: float = 0.0  # PSF adjustment (can be negative)

    def __post_init__(self) -> None:
        if self.cif_price_usd_per_barrel <= 0:
            raise ValueError("cif_price_usd_per_barrel must be positive")
        if self.usd_to_vnd <= 0:
            raise ValueError("usd_to_vnd must be positive")
