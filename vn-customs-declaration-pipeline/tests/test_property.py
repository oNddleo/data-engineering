"""Hypothesis property tests."""

from __future__ import annotations

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from vncustoms.calc import compute
from vncustoms.schema import (
    Declaration,
    DeclarationKind,
    HSCode,
    Incoterm,
    LineItem,
)

_unit_price = st.integers(min_value=1, max_value=1_000_000)
_qty = st.integers(min_value=1, max_value=1_000)
_chap = st.sampled_from(["84", "85", "87", "61", "62", "39", "30"])


@st.composite
def _line(draw: st.DrawFn) -> LineItem:
    chap = draw(_chap)
    last6 = draw(st.text(alphabet="0123456789", min_size=6, max_size=6))
    return LineItem(
        description="x",
        hs_code=HSCode(chap + last6),
        quantity=draw(_qty),
        unit_price_usd_cents=draw(_unit_price),
        origin_country=draw(st.sampled_from(["CN", "KR", "JP", "US", "DE"])),
    )


@given(
    incoterm=st.sampled_from(list(Incoterm)),
    lines=st.lists(_line(), min_size=1, max_size=5),
    freight=st.integers(min_value=0, max_value=1_000_000),
    insurance=st.integers(min_value=0, max_value=100_000),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=80)
def test_taxes_non_negative(
    incoterm: Incoterm,
    lines: list[LineItem],
    freight: int,
    insurance: int,
) -> None:
    decl = Declaration(
        declaration_no="X",
        kind=DeclarationKind.IMPORT,
        incoterm=incoterm,
        importer_tax_code="0312345678",
        freight_usd_cents=freight,
        insurance_usd_cents=insurance,
        usd_to_vnd=25_000,
        lines=tuple(lines),
    )
    c = compute(decl)
    assert c.customs_value_usd_cents >= 0
    assert c.import_duty_usd_cents >= 0
    assert c.vat_usd_cents >= 0
    assert c.total_tax_vnd >= 0


@given(
    lines=st.lists(_line(), min_size=1, max_size=5),
    freight=st.integers(min_value=0, max_value=1_000_000),
    insurance=st.integers(min_value=0, max_value=100_000),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=80)
def test_cv_at_least_invoice(
    lines: list[LineItem],
    freight: int,
    insurance: int,
) -> None:
    """Customs value is always ≥ line totals for any incoterm."""
    invoice_total = sum(line.total_usd_cents for line in lines)
    for incoterm in Incoterm:
        decl = Declaration(
            declaration_no="X",
            kind=DeclarationKind.IMPORT,
            incoterm=incoterm,
            importer_tax_code="0312345678",
            freight_usd_cents=freight,
            insurance_usd_cents=insurance,
            usd_to_vnd=25_000,
            lines=tuple(lines),
        )
        c = compute(decl)
        assert c.customs_value_usd_cents >= invoice_total


@given(
    lines=st.lists(_line(), min_size=1, max_size=5),
    freight=st.integers(min_value=0, max_value=1_000_000),
    insurance=st.integers(min_value=0, max_value=100_000),
)
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=60)
def test_addon_allocation_exact(
    lines: list[LineItem],
    freight: int,
    insurance: int,
) -> None:
    """Sum of per-line customs values equals invoice total + addons exactly."""
    invoice_total = sum(line.total_usd_cents for line in lines)
    # FOB requires both addons; this is the strictest case.
    decl = Declaration(
        declaration_no="X",
        kind=DeclarationKind.IMPORT,
        incoterm=Incoterm.FOB,
        importer_tax_code="0312345678",
        freight_usd_cents=freight,
        insurance_usd_cents=insurance,
        usd_to_vnd=25_000,
        lines=tuple(lines),
    )
    c = compute(decl)
    total_per_line_cv = sum(line.customs_value_usd_cents for line in c.lines)
    assert total_per_line_cv == invoice_total + freight + insurance


@given(lines=st.lists(_line(), min_size=1, max_size=5))
@settings(suppress_health_check=[HealthCheck.too_slow], max_examples=60)
def test_export_zero(lines: list[LineItem]) -> None:
    """Exports always have zero tax in this calculator."""
    decl = Declaration(
        declaration_no="X",
        kind=DeclarationKind.EXPORT,
        incoterm=Incoterm.FOB,
        importer_tax_code="0312345678",
        lines=tuple(lines),
    )
    c = compute(decl)
    assert c.import_duty_usd_cents == 0
    assert c.vat_usd_cents == 0
    assert c.total_tax_vnd == 0
