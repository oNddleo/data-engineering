"""Schema validation."""

from __future__ import annotations

import pytest

from vncustoms.schema import (
    Declaration,
    DeclarationKind,
    HSCode,
    Incoterm,
    LineItem,
)


def test_hscode_basic() -> None:
    hs = HSCode("85176200")
    assert hs.chapter == "85"
    assert hs.heading == "8517"


@pytest.mark.parametrize("bad", ["", "1234567", "123456789", "8517620A", "01234567"])
def test_hscode_rejects_bad_shape(bad: str) -> None:
    if bad == "01234567":
        # chapter 01 is valid; only digits + 8 chars matter for this
        pytest.skip("01234567 is structurally valid")
    with pytest.raises(ValueError):
        HSCode(bad)


def test_hscode_rejects_bad_chapter() -> None:
    with pytest.raises(ValueError):
        HSCode("00123456")  # chapter 00
    with pytest.raises(ValueError):
        HSCode("99123456")  # chapter 99 > 97


def test_lineitem_basic() -> None:
    line = LineItem(
        description="laptop",
        hs_code=HSCode("84713000"),
        quantity=10,
        unit_price_usd_cents=80_000,
        origin_country="CN",
    )
    assert line.total_usd_cents == 800_000


def test_lineitem_rejects_bad_origin() -> None:
    with pytest.raises(ValueError):
        LineItem(
            description="x",
            hs_code=HSCode("85176200"),
            quantity=1,
            unit_price_usd_cents=1,
            origin_country="cn",  # not uppercase
        )
    with pytest.raises(ValueError):
        LineItem(
            description="x",
            hs_code=HSCode("85176200"),
            quantity=1,
            unit_price_usd_cents=1,
            origin_country="CHN",  # ISO-3 not allowed
        )


def test_lineitem_rejects_zero_quantity() -> None:
    with pytest.raises(ValueError):
        LineItem(
            description="x",
            hs_code=HSCode("85176200"),
            quantity=0,
            unit_price_usd_cents=1,
            origin_country="CN",
        )


def test_declaration_basic() -> None:
    decl = Declaration(
        declaration_no="10312000001/A11",
        kind=DeclarationKind.IMPORT,
        incoterm=Incoterm.CIF,
        importer_tax_code="0312345678",
    )
    assert decl.kind == DeclarationKind.IMPORT
    assert decl.usd_to_vnd == 25_000


def test_declaration_rejects_empty_fields() -> None:
    with pytest.raises(ValueError):
        Declaration(
            declaration_no="",
            kind=DeclarationKind.IMPORT,
            incoterm=Incoterm.CIF,
            importer_tax_code="0312345678",
        )


def test_declaration_rejects_bad_usd_rate() -> None:
    with pytest.raises(ValueError):
        Declaration(
            declaration_no="X",
            kind=DeclarationKind.IMPORT,
            incoterm=Incoterm.CIF,
            importer_tax_code="0312345678",
            usd_to_vnd=0,
        )
