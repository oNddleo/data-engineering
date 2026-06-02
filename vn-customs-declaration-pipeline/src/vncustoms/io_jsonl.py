"""JSONL codec for declarations + tax-calc results."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from vncustoms.calc import DeclarationCalc, LineCalc
from vncustoms.schema import (
    Declaration,
    DeclarationKind,
    HSCode,
    Incoterm,
    LineItem,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator


def _require_str(d: dict[str, object], key: str) -> str:
    v = d[key]
    if not isinstance(v, str):
        raise TypeError(f"{key} must be str, got {type(v).__name__}")
    return v


def _require_int(d: dict[str, object], key: str) -> int:
    v = d[key]
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int, got {type(v).__name__}")
    return v


def _opt_int(d: dict[str, object], key: str, default: int = 0) -> int:
    v = d.get(key, default)
    if not isinstance(v, int) or isinstance(v, bool):
        raise TypeError(f"{key} must be int, got {type(v).__name__}")
    return v


def line_to_dict(line: LineItem) -> dict[str, object]:
    return {
        "description": line.description,
        "hs_code": line.hs_code.code,
        "quantity": line.quantity,
        "unit_price_usd_cents": line.unit_price_usd_cents,
        "origin_country": line.origin_country,
    }


def line_from_dict(d: dict[str, object]) -> LineItem:
    return LineItem(
        description=_require_str(d, "description"),
        hs_code=HSCode(_require_str(d, "hs_code")),
        quantity=_require_int(d, "quantity"),
        unit_price_usd_cents=_require_int(d, "unit_price_usd_cents"),
        origin_country=_require_str(d, "origin_country"),
    )


def declaration_to_dict(decl: Declaration) -> dict[str, object]:
    return {
        "declaration_no": decl.declaration_no,
        "kind": decl.kind.value,
        "incoterm": decl.incoterm.value,
        "importer_tax_code": decl.importer_tax_code,
        "freight_usd_cents": decl.freight_usd_cents,
        "insurance_usd_cents": decl.insurance_usd_cents,
        "usd_to_vnd": decl.usd_to_vnd,
        "lines": [line_to_dict(line) for line in decl.lines],
    }


def declaration_from_dict(d: dict[str, object]) -> Declaration:
    raw_lines = d.get("lines", [])
    if not isinstance(raw_lines, list):
        raise TypeError("lines must be a list")
    lines: list[LineItem] = []
    for raw in raw_lines:
        if not isinstance(raw, dict):
            raise TypeError("each line must be an object")
        lines.append(line_from_dict(raw))
    return Declaration(
        declaration_no=_require_str(d, "declaration_no"),
        kind=DeclarationKind(_require_str(d, "kind")),
        incoterm=Incoterm(_require_str(d, "incoterm")),
        importer_tax_code=_require_str(d, "importer_tax_code"),
        freight_usd_cents=_opt_int(d, "freight_usd_cents"),
        insurance_usd_cents=_opt_int(d, "insurance_usd_cents"),
        usd_to_vnd=_opt_int(d, "usd_to_vnd", 25_000),
        lines=tuple(lines),
    )


def calc_to_dict(c: DeclarationCalc) -> dict[str, object]:
    return {
        "declaration_no": c.declaration_no,
        "customs_value_usd_cents": c.customs_value_usd_cents,
        "import_duty_usd_cents": c.import_duty_usd_cents,
        "vat_usd_cents": c.vat_usd_cents,
        "total_tax_vnd": c.total_tax_vnd,
        "lines": [
            {
                "description": line.description,
                "hs_code": line.hs_code,
                "quantity": line.quantity,
                "customs_value_usd_cents": line.customs_value_usd_cents,
                "import_duty_usd_cents": line.import_duty_usd_cents,
                "vat_usd_cents": line.vat_usd_cents,
            }
            for line in c.lines
        ],
    }


def calc_from_dict(d: dict[str, object]) -> DeclarationCalc:
    raw_lines = d.get("lines", [])
    if not isinstance(raw_lines, list):
        raise TypeError("lines must be a list")
    lines: list[LineCalc] = []
    for raw in raw_lines:
        if not isinstance(raw, dict):
            raise TypeError("each line must be an object")
        lines.append(
            LineCalc(
                description=_require_str(raw, "description"),
                hs_code=_require_str(raw, "hs_code"),
                quantity=_require_int(raw, "quantity"),
                customs_value_usd_cents=_require_int(raw, "customs_value_usd_cents"),
                import_duty_usd_cents=_require_int(raw, "import_duty_usd_cents"),
                vat_usd_cents=_require_int(raw, "vat_usd_cents"),
            )
        )
    return DeclarationCalc(
        declaration_no=_require_str(d, "declaration_no"),
        lines=tuple(lines),
        customs_value_usd_cents=_require_int(d, "customs_value_usd_cents"),
        import_duty_usd_cents=_require_int(d, "import_duty_usd_cents"),
        vat_usd_cents=_require_int(d, "vat_usd_cents"),
        total_tax_vnd=_require_int(d, "total_tax_vnd"),
    )


def _dump(items: Iterable[dict[str, object]]) -> str:
    return "\n".join(json.dumps(d, ensure_ascii=False) for d in items) + "\n"


def dump_declarations(items: Iterable[Declaration]) -> str:
    return _dump(declaration_to_dict(d) for d in items)


def dump_calcs(items: Iterable[DeclarationCalc]) -> str:
    return _dump(calc_to_dict(c) for c in items)


def _iter_lines(text: str) -> Iterator[dict[str, object]]:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise TypeError(
                f"expected JSON object per line, got {type(parsed).__name__}",
            )
        yield parsed


def load_declarations(text: str) -> list[Declaration]:
    return [declaration_from_dict(d) for d in _iter_lines(text)]


def load_calcs(text: str) -> list[DeclarationCalc]:
    return [calc_from_dict(d) for d in _iter_lines(text)]


__all__ = [
    "calc_from_dict",
    "calc_to_dict",
    "declaration_from_dict",
    "declaration_to_dict",
    "dump_calcs",
    "dump_declarations",
    "line_from_dict",
    "line_to_dict",
    "load_calcs",
    "load_declarations",
]
