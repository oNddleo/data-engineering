# Changelog

## [0.1.0] — 2026-05-15

### Added
- `TaxCode` dataclass for VN MST (Mã số thuế) — accepts 10- or
  13-digit forms; `primary` / `branch_suffix` accessors split the
  two halves of a 13-digit code.
- `Invoice`, `InvoiceItem`, `InvoiceKind`, `VATRate` frozen-slots
  dataclasses with validation at construction (tz-aware datetimes,
  non-negative amounts, contiguous line numbers, VND-only currency,
  at-least-one item).
- `VATRate` enum covers the four legal Vietnamese rates plus
  EXEMPT (rice / salt / healthcare — different from 0%) — values
  stored in basis points (1% = 100 bps) for integer math.
- `compute_check_digit(first_nine)` — MST weighted-sum-mod-11
  algorithm using GDT's weight vector `[31, 29, 23, 19, 17, 13, 7, 5, 3]`.
  Special-cases `mod == 0 → 0`; otherwise `10 - mod`.
- `is_valid(digits)` validates 10- or 13-digit MSTs (branch suffix
  not independently checksum-validated; primary checksum must pass).
- `normalise(raw)` strips `-` and whitespace separators commonly
  found on printed invoices.
- 7-check validator: `check_tax_code_format`, `check_line_math`,
  `check_totals`, `check_required_fields`, `check_export_invoice`,
  `check_template_consistency` — each returns a list of `Finding`s.
- `validate(invoice)` runs all checks; `has_errors(findings)` returns
  True if any is severity ERROR.
- `Severity` enum: ERROR (would block GDT submission), WARNING
  (allowed but ops should review — e.g. B2C VAT invoice without
  buyer MST).
- VAT rounding uses banker's (round-half-to-even) on integer-VND
  inputs to match GDT's published rounding rule.
- `TaxRegistry` Protocol + `InMemoryRegistry` mock seeded with 7
  real public Vietnamese entities (Vietcombank, FPT, Mobile World,
  Vietjet, …). Production callers plug in their GDT API client.
- 13-digit branch lookup falls back to the 10-digit primary — matches
  how the real GDT registry handles unregistered branches.
- Seeded synthetic invoice generator (`simulator.generate`) with
  configurable `bad_fraction` and 5 injected bug types:
  line-total off, vat off, header off, wrong template, bad buyer MST.
- Type-checked JSONL codec for `Invoice` + `Finding` with
  `_require_str` / `_require_int` decoders.
- CLI `vntax info | simulate | validate | lookup | summary` with
  three-way exit codes for `lookup`: 0 (registered), 1 (checksum
  failed), 2 (checksum valid but not in registry).
- 85 tests including 6 Hypothesis properties (any computed check
  digit validates, any non-canonical check digit invalidates, any
  branch suffix on a valid primary is valid, clean invoices never
  produce math findings, VAT rounding is within 1 VND of exact
  division, check digit is always a single digit 0-9).
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `vntax` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- Zero runtime dependencies.

### Notes
- The first cut of the MST checksum had a `mod == 1 → invalid`
  carve-out that rejected FPT Corp's real MST (`0301442379`).
  GDT has no such carve-out — every value of `mod` in `[0, 10]`
  maps to a legal single-digit check digit. Verified against four
  real public MSTs: Vietcombank `0100109106`, FPT `0301442379`,
  Mobile World `0301448243`, Vietjet `0309532909`.
- `InMemoryRegistry(entities=[])` originally used `entities or
  _bundled_entities()` which silently substituted the bundled list
  for an explicit empty seed. Fixed with `is None` check so callers
  who want a truly empty registry get one.
- The 8% VAT-rate carve-outs (luxury / finance / telecom stay at
  10% even when other goods drop to 8% per Nghị quyết 43) are
  **not** validated here — they require product-classification
  metadata that doesn't exist at the invoice layer. That check
  belongs in a separate product-master service.
- Bundled registry entries marked "(mock)" — for those, the name
  is a real VN entity but the MST has been adjusted to a
  checksum-valid value (the actual published MSTs may rely on
  algorithm variants we don't model). Pure-real MSTs are
  Vietcombank, FPT, Mobile World, Vietjet.
