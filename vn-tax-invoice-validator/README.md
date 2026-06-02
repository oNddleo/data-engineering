# vn-tax-invoice-validator

Vietnamese e-invoice (hóa đơn điện tử) validator implementing the
rules from **Nghị định 123/2020/NĐ-CP** and **Thông tư 78/2021/TT-BTC**.
Validates the MST (Mã số thuế) checksum, line-item arithmetic, VAT
rate consistency, header-vs-line totals, and template/kind pairing —
the exact checks GDT (General Department of Taxation) runs against
every submitted invoice.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Validates Invoice records at the boundary** — tz-aware
   datetimes, positive money, contiguous line numbers, exactly-VND
   currency.
2. **MST checksum** — implements the weighted-sum-mod-11 algorithm
   GDT uses. Handles both 10-digit (legal entity) and 13-digit
   (with branch suffix) forms. Validated against real public MSTs:
   Vietcombank, FPT Corp, Mobile World, Vietjet.
3. **Line-item math**: `line_total == quantity × unit_price`;
   `vat_amount == round(line_total × rate_bps / 10_000)` using
   banker's (round-half-to-even).
4. **Header reconciliation**: `subtotal`, `vat_total`, `grand_total`
   each match the sum of the lines.
5. **Decree-123 required fields per `InvoiceKind`** — VAT invoices
   may omit buyer MST (B2C retail; WARNING); EXPORT invoices must
   name the foreign counterparty (ERROR if missing).
6. **EXPORT invoices must be 0% VAT** on every line.
7. **Template/kind consistency** — `template_code` first character
   encodes the invoice kind (1 = VAT, 2 = sales, 6 = export);
   pairing mismatched is rejected.
8. **MST lookup** against a TaxRegistry Protocol — bundled in-memory
   mock seeded with 7 real public Vietnamese entities for demos /
   tests; production callers plug in their GDT API client behind
   the same interface.

## VN VAT rates (per Thông tư 78 + Nghị quyết 43/2022)

| Rate    | When                                                                  |
| ------- | --------------------------------------------------------------------- |
| **0%**  | Exports, international transport, services to foreign zones           |
| **5%**  | Essential goods (clean water, fertilizer, medical equipment, …)       |
| **8%**  | Reduced rate per **Nghị quyết 43/2022/QH15** Covid-era stimulus, extended through 2024-2026 for most goods otherwise at 10% (with carve-outs for luxury, finance, telecom, IT) |
| **10%** | Standard rate — everything else                                       |
| EXEMPT  | VAT-exempt goods (rice, salt, healthcare) — **different from 0%**     |

The 8% / 10% split is the most error-prone in production — the
exemption carve-outs require product-classification metadata that
lives outside the invoice. This validator catches **math** mistakes
(wrong vat_amount for the claimed rate) but not **classification**
mistakes (8% applied to a product that should have stayed at 10%).
That check belongs in a separate product-master service.

## Components

| Module                | Role                                                                  |
| --------------------- | --------------------------------------------------------------------- |
| `vntax.schema`        | `Invoice`, `InvoiceItem`, `TaxCode`, `InvoiceKind`, `VATRate`         |
| `vntax.taxcode`       | `compute_check_digit`, `is_valid`, `normalise` — MST algorithm        |
| `vntax.validator`     | 7 checks: tax-code format, line math, totals, required fields, export rules, template consistency |
| `vntax.registry`      | `TaxRegistry` Protocol + `InMemoryRegistry` mock (7 seed entities)    |
| `vntax.simulator`     | Seeded synthetic invoices with configurable `bad_fraction`            |
| `vntax.io_jsonl`      | Type-checked JSONL codec for invoices + findings                       |
| `vntax.cli`           | `vntax info \| simulate \| validate \| lookup \| summary`              |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
vntax info
vntax simulate --n 100 --bad-fraction 0.30 --seed 7 --output ./invoices.jsonl
vntax validate --input ./invoices.jsonl --output ./findings.jsonl --show 10 --summary
vntax lookup   0100109106
vntax lookup   0100109107       # mutated check digit → exit 1
vntax summary  --input ./invoices.jsonl
```

Sample `lookup` output:

```json
{
  "mst": "0100109106",
  "name": "Vietcombank",
  "address": "198 Trần Quang Khải, Hoàn Kiếm, Hà Nội",
  "status": "ACTIVE",
  "registered_at": "1993-04-01"
}
```

Sample `validate` output:

```
invoice        sev      code                         detail
INV-00000000   ERROR    TAX_CODE_BUYER_INVALID       buyer MST '0100686979' fails checksum
INV-00000002   ERROR    HEADER_GRAND_MISMATCH        header grand_total=212,680 ≠ subtotal + vat = 211,680
INV-00000004   ERROR    LINE_TOTAL_MISMATCH          line 1: line_total=4,491,001 ≠ qty × unit_price = 4,491,000
INV-00000012   ERROR    VAT_AMOUNT_MISMATCH          line 1: vat_amount=19,700 ≠ expected 19,600 at rate FIVE
INV-00000016   ERROR    TEMPLATE_KIND_MISMATCH       template_code '6/001' encodes EXPORT_INVOICE but invoice.kind is VAT_INVOICE

Summary: 32/100 invoices have ≥1 ERROR (32 total findings)
```

Sample `summary` JSON:

```json
{
  "n_invoices": 100,
  "n_with_errors": 32,
  "by_severity": {"ERROR": 32},
  "by_code": {
    "TAX_CODE_BUYER_INVALID": 10,
    "HEADER_GRAND_MISMATCH": 10,
    "LINE_TOTAL_MISMATCH": 6,
    "VAT_AMOUNT_MISMATCH": 3,
    "TEMPLATE_KIND_MISMATCH": 3
  }
}
```

## Library

```python
from vntax.simulator import generate
from vntax.validator import validate, has_errors
from vntax.taxcode  import is_valid
from vntax.registry import InMemoryRegistry

# 1) MST checks
assert is_valid("0100109106")           # Vietcombank — passes
assert not is_valid("0100109107")       # mutated check digit

# 2) Validate a batch of invoices
invoices = generate(n_invoices=200, bad_fraction=0.25, seed=42)
n_with_errors = sum(1 for inv in invoices if has_errors(validate(inv)))

# 3) Plug in a production GDT client behind the Protocol
class GDTApiClient:                      # satisfies TaxRegistry
    def lookup(self, mst: str):
        ...                              # call out to https://api.tct.gov.vn/...
```

## Key design decisions

- **MST formula special-cases `mod == 0` to check digit 0**, with
  every other ``mod ∈ [1, 10]`` mapping to ``10 - mod``. The first
  cut of this module had a ``mod == 1 → invalid`` carve-out that
  rejected FPT Corp's real MST (`0301442379`) — there is no such
  carve-out in the actual GDT algorithm.
- **Integer VND, banker's rounding.** VAT amounts are integer-VND
  computed as `round_half_even(line_total × rate_bps / 10_000)`.
  Matches GDT's published rounding rule.
- **Findings, not exceptions.** Every validator returns a list — the
  caller sees the full punch list, not one-issue-at-a-time. Ops
  fixing a bad invoice wants the complete picture so they don't
  resubmit only to find the next issue.
- **WARNING vs ERROR.** A B2C retail VAT invoice without a buyer
  MST is **legal** (Decree 123 Article 9), so it's flagged as
  WARNING — not ERROR — and the operator decides. Export invoices
  *must* name the buyer (ERROR if missing).
- **TaxRegistry Protocol.** Production callers integrate the real
  GDT submission API behind the Protocol; the bundled
  `InMemoryRegistry` is for tests and the demo CLI.
- **13-digit branch fallback.** An unregistered branch suffix
  resolves to its 10-digit primary — matches how the real GDT
  registry handles branch lookups for unregistered units.

## Quality

```bash
make test       # 85 tests + 6 Hypothesis properties
make type       # mypy --strict
make lint
```

- **85 tests**, 0 failing; 6 Hypothesis properties (any computed
  check digit validates; any non-canonical check digit invalidates;
  any branch suffix on a valid primary is valid; clean invoices
  never produce math findings; VAT rounding is within 1 VND of
  exact division; check digit is always a single digit 0-9).
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `vntax` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
