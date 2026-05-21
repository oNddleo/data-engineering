"""Core domain types for VN coffee export."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CoffeeSpecies(str, Enum):
    ROBUSTA = "ROBUSTA"  # Coffea canephora — ~95% of VN production
    ARABICA = "ARABICA"  # Coffea arabica — Da Lat highlands


class CoffeeGrade(str, Enum):
    """ICO/TCVN export grades."""

    # Robusta grades (defect count per 300g)
    R1 = "R1"  # Grade 1: ≤8 defects
    R2 = "R2"  # Grade 2: ≤16 defects
    R3 = "R3"  # Grade 3: ≤30 defects
    # Arabica grades
    A1 = "A1"  # Specialty: <5 defects
    A2 = "A2"  # Premium: ≤12 defects


class ContractType(str, Enum):
    """ICO coffee contract pricing basis."""

    DIFFERENTIAL = "DIFFERENTIAL"  # London/NY futures + differential (USD/tonne)
    FIXED_PRICE = "FIXED_PRICE"  # All-in FOB price agreed upfront
    OUTRIGHT = "OUTRIGHT"  # Same as FIXED_PRICE but priced at time of shipment


class Incoterm(str, Enum):
    FOB = "FOB"  # Free on Board — VN port
    CIF = "CIF"  # Cost Insurance Freight — buyer's port
    EXW = "EXW"  # Ex Works — at processing plant


@dataclass(frozen=True, slots=True)
class ExportLot:
    """A coffee export lot to be priced."""

    lot_id: str
    species: CoffeeSpecies
    grade: CoffeeGrade
    contract: ContractType
    incoterm: Incoterm
    volume_mt: float  # metric tonnes
    # For DIFFERENTIAL contracts:
    futures_price_usd_mt: float = 0.0  # London LIFFE / ICE futures
    differential_usd_mt: float = 0.0  # +/- differential
    # For FIXED_PRICE / OUTRIGHT:
    fixed_price_usd_mt: float = 0.0
    # Logistics
    freight_usd_mt: float = 0.0  # only relevant for CIF
    insurance_rate_pct: float = 0.0  # % of FOB value

    def __post_init__(self) -> None:
        if not self.lot_id:
            raise ValueError("lot_id must be non-empty")
        if self.volume_mt <= 0:
            raise ValueError("volume_mt must be positive")
        if self.contract == ContractType.DIFFERENTIAL and self.futures_price_usd_mt <= 0:
            raise ValueError("DIFFERENTIAL contract requires futures_price_usd_mt > 0")
        if (
            self.contract in (ContractType.FIXED_PRICE, ContractType.OUTRIGHT)
            and self.fixed_price_usd_mt <= 0
        ):
            raise ValueError("FIXED_PRICE/OUTRIGHT requires fixed_price_usd_mt > 0")
        if self.incoterm == Incoterm.CIF and self.freight_usd_mt <= 0:
            raise ValueError("CIF requires freight_usd_mt > 0")
