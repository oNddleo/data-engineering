"""JSONL codec round-trips."""

from __future__ import annotations

import pytest

from vncustoms.calc import compute
from vncustoms.io_jsonl import (
    declaration_from_dict,
    declaration_to_dict,
    dump_calcs,
    dump_declarations,
    load_calcs,
    load_declarations,
)
from vncustoms.schema import (
    Declaration,
    DeclarationKind,
    HSCode,
    Incoterm,
    LineItem,
)


def _sample() -> Declaration:
    return Declaration(
        declaration_no="10312000001/A11",
        kind=DeclarationKind.IMPORT,
        incoterm=Incoterm.CIF,
        importer_tax_code="0312345678",
        freight_usd_cents=0,
        insurance_usd_cents=0,
        usd_to_vnd=25_000,
        lines=(
            LineItem(
                description="laptop",
                hs_code=HSCode("84713000"),
                quantity=10,
                unit_price_usd_cents=80_000,
                origin_country="CN",
            ),
        ),
    )


def test_declaration_roundtrip() -> None:
    d = _sample()
    assert declaration_from_dict(declaration_to_dict(d)) == d


def test_declarations_dump_load() -> None:
    ds = [_sample()]
    assert load_declarations(dump_declarations(ds)) == ds


def test_calc_roundtrip() -> None:
    cs = [compute(_sample())]
    assert load_calcs(dump_calcs(cs)) == cs


def test_load_rejects_non_object() -> None:
    with pytest.raises(TypeError):
        load_declarations("[1,2,3]\n")


def test_load_rejects_bad_field_type() -> None:
    with pytest.raises(TypeError):
        load_declarations(
            '{"declaration_no":"X","kind":"import","incoterm":"CIF",'
            '"importer_tax_code":"0","freight_usd_cents":"x","lines":[]}\n'
        )
