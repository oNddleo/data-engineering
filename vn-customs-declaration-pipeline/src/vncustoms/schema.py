"""Schema for VN customs declarations (Tờ khai hải quan).

Domain model — what a Vietnamese customs declaration looks like in
structured form, post-normalisation:

* ``HSCode`` — 8-digit VN harmonized-system code (chapter, heading,
  subheading, national tariff line).
* ``Incoterm`` — Incoterms 2020 commercial term (FOB, CIF, EXW, DAP,
  DDP, …) which determines what's included in customs value.
* ``DeclarationKind`` — import (NK) or export (XK).
* ``LineItem`` — one good in a declaration with HS code, quantity,
  unit price (USD), and origin country (ISO-2).
* ``Declaration`` — header + lines (one declaration = one ``Tờ khai``).

All money fields are integer **USD cents** (avoiding float for
import value) or integer **VND** (for taxes after conversion).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class DeclarationKind(str, Enum):
    IMPORT = "import"  # NK — nhập khẩu
    EXPORT = "export"  # XK — xuất khẩu


class Incoterm(str, Enum):
    """Incoterms 2020 commercial terms relevant to VN customs.

    Customs value (``trị giá tính thuế``) is built up to the CIF
    equivalent — i.e. cost + insurance + freight at the VN border. The
    incoterm tells us how much of that the invoice already covers.
    """

    EXW = "EXW"  # Ex Works — buyer pays everything from seller's door.
    FOB = "FOB"  # Free On Board — seller pays to port-of-export.
    CFR = "CFR"  # Cost + Freight — seller pays freight, not insurance.
    CIF = "CIF"  # Cost + Insurance + Freight — fully landed.
    DAP = "DAP"  # Delivered At Place — seller delivers to named place.
    DDP = "DDP"  # Delivered Duty Paid — seller pays duties too.


@dataclass(frozen=True, slots=True)
class HSCode:
    """8-digit Vietnamese HS code.

    Structure (Hệ thống hài hòa Việt Nam, 8 digits):

    * ``code[0:2]`` chapter (01–97)
    * ``code[2:4]`` heading
    * ``code[4:6]`` subheading
    * ``code[6:8]`` national tariff line

    We don't validate against the official tariff book — that table is
    20 000+ entries — only the **shape** (8 digits, plausible chapter).
    """

    code: str

    def __post_init__(self) -> None:
        if not (self.code.isdigit() and len(self.code) == 8):
            raise ValueError(f"HS code must be 8 digits, got {self.code!r}")
        chapter = int(self.code[:2])
        if not 1 <= chapter <= 97:
            raise ValueError(f"HS chapter must be 01-97, got {chapter:02d}")

    @property
    def chapter(self) -> str:
        return self.code[:2]

    @property
    def heading(self) -> str:
        return self.code[:4]


@dataclass(frozen=True, slots=True)
class LineItem:
    """One commodity line in a declaration."""

    description: str
    hs_code: HSCode
    quantity: int
    unit_price_usd_cents: int
    origin_country: str  # ISO-2: VN, CN, JP, KR, US, …

    def __post_init__(self) -> None:
        if not self.description:
            raise ValueError("description must be non-empty")
        if self.quantity <= 0:
            raise ValueError("quantity must be > 0")
        if self.unit_price_usd_cents < 0:
            raise ValueError("unit_price_usd_cents must be >= 0")
        if not (len(self.origin_country) == 2 and self.origin_country.isalpha()):
            raise ValueError(f"origin_country must be ISO-2, got {self.origin_country!r}")
        if self.origin_country != self.origin_country.upper():
            raise ValueError("origin_country must be uppercase")

    @property
    def total_usd_cents(self) -> int:
        return self.quantity * self.unit_price_usd_cents


@dataclass(frozen=True, slots=True)
class Declaration:
    """A single customs declaration (one Tờ khai)."""

    declaration_no: str  # e.g. "10312345678/A11"
    kind: DeclarationKind
    incoterm: Incoterm
    importer_tax_code: str
    freight_usd_cents: int = 0
    insurance_usd_cents: int = 0
    usd_to_vnd: int = 25_000  # default mid-rate
    lines: tuple[LineItem, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.declaration_no:
            raise ValueError("declaration_no must be non-empty")
        if not self.importer_tax_code:
            raise ValueError("importer_tax_code must be non-empty")
        if self.freight_usd_cents < 0:
            raise ValueError("freight_usd_cents must be >= 0")
        if self.insurance_usd_cents < 0:
            raise ValueError("insurance_usd_cents must be >= 0")
        if self.usd_to_vnd <= 0:
            raise ValueError("usd_to_vnd must be > 0")


__all__ = [
    "Declaration",
    "DeclarationKind",
    "HSCode",
    "Incoterm",
    "LineItem",
]
