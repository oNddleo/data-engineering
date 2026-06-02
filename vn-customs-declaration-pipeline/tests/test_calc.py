"""Tax-calculation end-to-end."""

from __future__ import annotations

from vncustoms.calc import compute
from vncustoms.schema import (
    Declaration,
    DeclarationKind,
    HSCode,
    Incoterm,
    LineItem,
)


def _decl(
    incoterm: Incoterm = Incoterm.CIF,
    freight: int = 0,
    insurance: int = 0,
    lines: tuple[LineItem, ...] = (),
    kind: DeclarationKind = DeclarationKind.IMPORT,
) -> Declaration:
    return Declaration(
        declaration_no="10312000001/A11",
        kind=kind,
        incoterm=incoterm,
        importer_tax_code="0312345678",
        freight_usd_cents=freight,
        insurance_usd_cents=insurance,
        usd_to_vnd=25_000,
        lines=lines,
    )


_LAPTOP = LineItem(
    description="laptop",
    hs_code=HSCode("84713000"),  # chap 84: duty 3%
    quantity=10,
    unit_price_usd_cents=80_000,  # $800 each
    origin_country="CN",
)


def test_cif_no_addons() -> None:
    """CIF: freight and insurance already in invoice."""
    decl = _decl(incoterm=Incoterm.CIF, freight=100_000, insurance=10_000, lines=(_LAPTOP,))
    c = compute(decl)
    # CIF means no freight/insurance added — customs value == line total.
    assert c.customs_value_usd_cents == 800_000
    # duty = 800_000 * 0.03 = 24_000
    assert c.import_duty_usd_cents == 24_000
    # vat = (800_000 + 24_000) * 0.08 = 65_920
    assert c.vat_usd_cents == 65_920


def test_fob_adds_freight_and_insurance() -> None:
    """FOB: invoice excludes freight + insurance — both added."""
    decl = _decl(incoterm=Incoterm.FOB, freight=100_000, insurance=10_000, lines=(_LAPTOP,))
    c = compute(decl)
    # CV = 800_000 + 100_000 + 10_000 = 910_000
    assert c.customs_value_usd_cents == 910_000


def test_cfr_adds_only_insurance() -> None:
    """CFR: invoice covers freight but not insurance."""
    decl = _decl(incoterm=Incoterm.CFR, freight=100_000, insurance=10_000, lines=(_LAPTOP,))
    c = compute(decl)
    assert c.customs_value_usd_cents == 810_000  # 800_000 + 10_000 insurance


def test_exw_adds_both() -> None:
    """EXW: buyer pays everything."""
    decl = _decl(incoterm=Incoterm.EXW, freight=100_000, insurance=10_000, lines=(_LAPTOP,))
    c = compute(decl)
    assert c.customs_value_usd_cents == 910_000


def test_export_zero_tax() -> None:
    decl = _decl(kind=DeclarationKind.EXPORT, incoterm=Incoterm.FOB, lines=(_LAPTOP,))
    c = compute(decl)
    assert c.import_duty_usd_cents == 0
    assert c.vat_usd_cents == 0
    assert c.total_tax_vnd == 0


def test_empty_lines_yields_zero() -> None:
    decl = _decl(lines=())
    c = compute(decl)
    assert c.customs_value_usd_cents == 0
    assert c.import_duty_usd_cents == 0
    assert c.vat_usd_cents == 0


def test_freight_pro_rated_across_lines() -> None:
    """Freight is allocated proportionally to each line's value."""
    line_a = LineItem(
        description="a",
        hs_code=HSCode("84713000"),
        quantity=1,
        unit_price_usd_cents=100_000,  # $1000
        origin_country="CN",
    )
    line_b = LineItem(
        description="b",
        hs_code=HSCode("84713000"),
        quantity=1,
        unit_price_usd_cents=300_000,  # $3000
        origin_country="CN",
    )
    decl = _decl(incoterm=Incoterm.FOB, freight=40_000, insurance=0, lines=(line_a, line_b))
    c = compute(decl)
    # Line A gets 25% of freight = 10_000 → CV 110_000
    # Line B gets 75% of freight = 30_000 → CV 330_000
    assert c.lines[0].customs_value_usd_cents == 110_000
    assert c.lines[1].customs_value_usd_cents == 330_000
    assert c.customs_value_usd_cents == 440_000


def test_vnd_conversion() -> None:
    """total_tax_vnd = total_tax_usd_cents * usd_to_vnd / 100."""
    decl = _decl(incoterm=Incoterm.CIF, lines=(_LAPTOP,))
    c = compute(decl)
    expected = (c.import_duty_usd_cents + c.vat_usd_cents) * 25_000 // 100
    assert c.total_tax_vnd == expected


def test_high_duty_chapter_pays_more() -> None:
    """A car (chap 87, 30%) pays more duty than a laptop (chap 84, 3%) of equal value."""
    car = LineItem(
        description="car",
        hs_code=HSCode("87032391"),
        quantity=1,
        unit_price_usd_cents=800_000,  # match laptop total value
        origin_country="JP",
    )
    decl_car = _decl(incoterm=Incoterm.CIF, lines=(car,))
    decl_laptop = _decl(incoterm=Incoterm.CIF, lines=(_LAPTOP,))
    assert compute(decl_car).import_duty_usd_cents > compute(decl_laptop).import_duty_usd_cents


def test_addon_allocation_exact_sum() -> None:
    """Sum of pro-rated addons equals total addons (no drift)."""
    lines = tuple(
        LineItem(
            description=f"l{i}",
            hs_code=HSCode("84713000"),
            quantity=1,
            unit_price_usd_cents=10_000 + i * 100,
            origin_country="CN",
        )
        for i in range(7)
    )
    decl = _decl(incoterm=Incoterm.FOB, freight=12_345, insurance=678, lines=lines)
    c = compute(decl)
    total_line_values = sum(line.total_usd_cents for line in lines)
    total_cv = sum(line.customs_value_usd_cents for line in c.lines)
    assert total_cv == total_line_values + 12_345 + 678
