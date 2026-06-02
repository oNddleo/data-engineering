"""Deterministic synthetic declaration generator."""

from __future__ import annotations

import random

from vncustoms.schema import (
    Declaration,
    DeclarationKind,
    HSCode,
    Incoterm,
    LineItem,
)

# A handful of realistic VN-import HS lines (chapter, sample 8-digit code,
# description). Skews toward what HCMC / Hai Phong ports actually see:
# electronics, garments, machinery, packaged foods.
_CATALOG: tuple[tuple[str, str, str], ...] = (
    ("85", "85176200", "smartphone module"),
    ("85", "85287200", "LCD TV panel"),
    ("84", "84713000", "laptop computer"),
    ("84", "84439990", "printer parts"),
    ("87", "87032391", "passenger car"),
    ("61", "61091000", "cotton T-shirt"),
    ("62", "62034200", "men's trousers"),
    ("64", "64041100", "sports footwear"),
    ("09", "09011110", "Robusta coffee beans"),
    ("22", "22030000", "beer"),
    ("39", "39201000", "polyethylene film"),
    ("48", "48030000", "tissue paper"),
    ("30", "30049090", "pharmaceutical preparation"),
)

_ORIGINS: tuple[str, ...] = ("CN", "KR", "JP", "TH", "US", "DE", "VN")
_INCOTERMS: tuple[Incoterm, ...] = (Incoterm.CIF, Incoterm.FOB, Incoterm.CFR)


def _gen_one(idx: int, rng: random.Random) -> Declaration:
    n_lines = rng.randint(1, 4)
    lines: list[LineItem] = []
    for _ in range(n_lines):
        chap, code, desc = rng.choice(_CATALOG)
        _ = chap  # chapter is the first two digits of code
        lines.append(
            LineItem(
                description=desc,
                hs_code=HSCode(code),
                quantity=rng.randint(1, 1000),
                unit_price_usd_cents=rng.randint(100, 500_000),
                origin_country=rng.choice(_ORIGINS),
            )
        )
    incoterm = rng.choice(_INCOTERMS)
    # Freight & insurance only meaningful for incoterms that don't include them.
    has_freight = incoterm in (Incoterm.EXW, Incoterm.FOB)
    has_insurance = incoterm in (Incoterm.EXW, Incoterm.FOB, Incoterm.CFR)
    return Declaration(
        declaration_no=f"10312{idx:06d}/A11",
        kind=DeclarationKind.IMPORT,
        incoterm=incoterm,
        importer_tax_code=f"03{rng.randint(10_000_000, 99_999_999)}",
        freight_usd_cents=rng.randint(10_000, 500_000) if has_freight else 0,
        insurance_usd_cents=rng.randint(1_000, 20_000) if has_insurance else 0,
        usd_to_vnd=25_000,
        lines=tuple(lines),
    )


def generate(n: int = 50, seed: int = 0) -> list[Declaration]:
    """Generate ``n`` synthetic VN import declarations."""
    if n < 0:
        raise ValueError("n must be >= 0")
    rng = random.Random(seed)
    return [_gen_one(i, rng) for i in range(n)]


__all__ = ["generate"]
