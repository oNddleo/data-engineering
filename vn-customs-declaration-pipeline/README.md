# vn-customs-declaration-pipeline

Normalize and tax-calculate Vietnamese customs declarations (Tờ khai
hải quan) — HS codes, incoterms, import duty, and VAT.

## What it does

* **Schema** — `Declaration` (header + lines), `LineItem` (HS code,
  quantity, unit price, origin), 8-digit `HSCode` with chapter
  validation, `Incoterm` (EXW/FOB/CFR/CIF/DAP/DDP) enum.
* **Tariff** — rate lookup keyed by HS chapter (illustrative table,
  not the full 20 000-line schedule). VAT defaults to the current
  reduced 8 % standard rate with a short essentials list at 5 %.
* **Calc** — full landed-cost build-up (line value + pro-rated
  freight & insurance to CIF equivalent), then duty + VAT, then VND
  conversion.

## Quick start

```bash
pip install vn-customs-declaration-pipeline
vncustoms info
vncustoms tariff 85
vncustoms simulate --n 100 --seed 0 --output decls.jsonl
vncustoms calc --input decls.jsonl --output calcs.jsonl
```

## Library

```python
from vncustoms import (
    Declaration, DeclarationKind, HSCode, Incoterm, LineItem, compute,
)

decl = Declaration(
    declaration_no="10312000001/A11",
    kind=DeclarationKind.IMPORT,
    incoterm=Incoterm.FOB,
    importer_tax_code="0312345678",
    freight_usd_cents=100_000,
    insurance_usd_cents=10_000,
    usd_to_vnd=25_000,
    lines=(
        LineItem(
            description="laptop",
            hs_code=HSCode("84713000"),
            quantity=10,
            unit_price_usd_cents=80_000,  # $800 each
            origin_country="CN",
        ),
    ),
)
c = compute(decl)
print(c.customs_value_usd_cents)  # 910_000 cents (CIF = 800k + 100k + 10k)
print(c.total_tax_vnd)            # converted at 25 000 VND/USD
```

## Customs value build-up

| Incoterm  | What's in invoice                       | Add to CV          |
| --------- | --------------------------------------- | ------------------ |
| EXW       | goods only                              | freight + insurance |
| FOB       | goods + on-board export                 | freight + insurance |
| CFR       | goods + freight                         | insurance           |
| CIF / DAP / DDP | goods + freight + insurance       | nothing            |

Freight & insurance are **pro-rated across lines** proportional to
line invoice value, with the last line absorbing rounding remainder
so totals stay exact.

## Caveats

* This is an **illustrative** rate table — production use must plug
  in the official ``Biểu thuế xuất nhập khẩu`` from the Ministry of
  Finance (updated yearly, ~20 000 tariff lines, FTA preferential
  rates, etc.).
* Special consumption tax (TTĐB) is out of scope.
* Exports are zero-rated in this calculator; the natural-resources
  export-duty list is not modeled.

## License

MIT.
