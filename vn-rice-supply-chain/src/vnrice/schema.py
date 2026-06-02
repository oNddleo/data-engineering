"""Core domain types for VN rice supply chain."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class RiceVariety(str, Enum):
    """Major Vietnam export rice varieties."""

    JASMINE = "JASMINE"  # Gao Jasmine / Hoa Lai
    IR50404 = "IR50404"  # High-yield, lower quality
    ST25 = "ST25"  # World's best rice 2019, premium
    OM18 = "OM18"  # Mekong Delta standard
    GLUTINOUS = "GLUTINOUS"  # Gao nep


class PaddyGrade(str, Enum):
    """Paddy (unhusked rice) quality grades."""

    GRADE_1 = "GRADE_1"  # Moisture ≤14%, broken ≤5%, immature ≤2%
    GRADE_2 = "GRADE_2"  # Moisture ≤14.5%, broken ≤10%, immature ≤5%
    GRADE_3 = "GRADE_3"  # Moisture ≤15%, broken ≤20%


class MilledRiceSpec(str, Enum):
    """Milled rice broken-grain specification (% broken)."""

    PERCENT_5 = "5%"
    PERCENT_10 = "10%"
    PERCENT_15 = "15%"
    PERCENT_25 = "25%"
    PERCENT_100 = "100%"  # broken rice


@dataclass(frozen=True, slots=True)
class PaddyLot:
    """A paddy rice lot entering the mill."""

    lot_id: str
    variety: RiceVariety
    grade: PaddyGrade
    weight_mt: float  # metric tonnes
    moisture_pct: float  # actual moisture %
    price_vnd_per_kg: float  # farmgate price

    def __post_init__(self) -> None:
        if not self.lot_id:
            raise ValueError("lot_id must be non-empty")
        if self.weight_mt <= 0:
            raise ValueError("weight_mt must be positive")
        if not (10.0 <= self.moisture_pct <= 30.0):
            raise ValueError(f"moisture_pct out of range: {self.moisture_pct}")
        if self.price_vnd_per_kg < 0:
            raise ValueError("price_vnd_per_kg must be >= 0")
