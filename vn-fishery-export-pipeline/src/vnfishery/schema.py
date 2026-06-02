"""VN seafood export schema.

VN is one of the world's top seafood exporters — VASEP tracks ~5
flagship species (tra/basa pangasius, white-leg shrimp, black tiger
shrimp, squid, tuna) into ~5 anchor markets (US, EU, Japan, China,
South Korea). Anti-dumping orders from the US (DOC) and EU
periodically hit specific species + exporter combinations.

* ``Species`` — short enum of the species we care about (pangasius,
  shrimp varieties, squid, tuna).
* ``Market`` — destination ISO-2 country code, with EU as a special
  block aggregate.
* ``Grade`` — quality tier (A/B/C); affects benchmark price.
* ``Form`` — product form (whole/fillet/peeled/frozen/dried).
* ``ExportRecord`` — one shipment line: species, market, grade, form,
  weight (kg), FOB unit price (USD/kg in cents), exporter tax code,
  shipped date.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import date


class Species(str, Enum):
    PANGASIUS = "pangasius"  # cá tra/basa — top freshwater export
    WHITE_SHRIMP = "white_shrimp"  # tôm thẻ chân trắng
    BLACK_TIGER = "black_tiger"  # tôm sú
    SQUID = "squid"  # mực
    TUNA = "tuna"  # cá ngừ
    OTHER = "other"


class Market(str, Enum):
    """Top VN seafood destinations (matches VASEP grouping)."""

    US = "US"
    EU = "EU"
    JP = "JP"
    CN = "CN"
    KR = "KR"
    OTHER = "OTHER"


class Grade(str, Enum):
    A = "A"  # premium — pristine, no defects
    B = "B"  # standard — minor defects allowed
    C = "C"  # processing-only — visible defects, going into surimi etc.


class Form(str, Enum):
    WHOLE = "whole"  # nguyên con
    FILLET = "fillet"  # phi-lê
    PEELED = "peeled"  # tôm bóc vỏ
    FROZEN = "frozen"  # đông lạnh (block)
    DRIED = "dried"  # khô


@dataclass(frozen=True, slots=True)
class ExportRecord:
    """One shipment line."""

    shipment_id: str
    exporter_tax_code: str
    species: Species
    market: Market
    grade: Grade
    form: Form
    weight_kg: int
    fob_price_usd_cents_per_kg: int
    shipped_on: date

    def __post_init__(self) -> None:
        if not self.shipment_id:
            raise ValueError("shipment_id must be non-empty")
        if not self.exporter_tax_code:
            raise ValueError("exporter_tax_code must be non-empty")
        if self.weight_kg <= 0:
            raise ValueError("weight_kg must be > 0")
        if self.fob_price_usd_cents_per_kg < 0:
            raise ValueError("fob_price_usd_cents_per_kg must be >= 0")

    @property
    def fob_value_usd_cents(self) -> int:
        """Total FOB value in USD cents."""
        return self.weight_kg * self.fob_price_usd_cents_per_kg


__all__ = [
    "ExportRecord",
    "Form",
    "Grade",
    "Market",
    "Species",
]
