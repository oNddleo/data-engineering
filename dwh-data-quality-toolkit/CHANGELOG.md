# Changelog

## [0.1.0] — 2026-05-17

### Added
- `Check` Protocol — anything callable as
  `(rows, column) → CheckResult` with a `name` and `severity`
  attribute is a check; production callers add in-house validators
  without subclassing.
- `Severity` enum (`ERROR`, `WARNING`) — ERROR quarantines the row +
  exits CI with code 2; WARNING logs only and exits 0.
- `CheckSpec` + `Suite` — JSON-serialisable bundles of
  `(check_name, column, severity, args)` triples that live in source
  control alongside DDL.
- `CheckResult` with row-level `FailedRow` records (row_index +
  column + value + reason) so dashboards can deep-link to the
  offending row.
- Seven **generic** checks: `not_null`, `unique`, `in_set`, `regex`,
  `range_int`, `dtype_int`, `dtype_str`. ``None`` and empty-string
  handling is uniform — only `not_null` flags them; everything else
  skips silently.
- Five **VN-specific** checks: `cccd` (12-digit format + province
  registry), `mst` (10/13-digit + checksum, matches the
  `vn-tax-invoice-validator` algorithm), `vn_phone`
  (03/05/07/08/09 mobile + 02x landline + optional +84), `vn_bank_account`
  (8 – 19 digits), `vn_postal_code` (5-digit VietPost + valid
  province prefix).
- `run_suite(rows, suite)` — registry-driven dispatcher; unknown
  check names raise immediately rather than silently no-op.
- `quarantine_rows(rows, results)` — splits the rowset into
  `(good, bad)` based on ERROR-severity failures. WARNING failures
  don't quarantine.
- `summarise(results)` + `render_summary` — JSON-friendly roll-up
  with per-severity counts and per-check detail.
- `dtype_int` explicitly rejects `bool` values (even though they're
  `int` subclasses) — catches a real DW bug where JSON booleans get
  silently loaded into integer columns.
- Seeded synthetic generator producing a customer rowset with 10
  injectable defect types (cccd_short, mst_mutated, phone_bad,
  tier_unknown, credit_out_of_range, postal_short, duplicate_id,
  cccd_null, mst_null, bank_too_short).
- Type-checked JSONL codec for rows + results; JSON codec for Suites
  (suite_to_json / suite_from_json).
- CLI `dqkit info | checks | simulate | make-suite | run` with
  CI-friendly exit codes (0 = no ERROR; 2 = ≥1 ERROR).
- 87 tests + 6 Hypothesis properties (not_null failure count
  matches null + empty-string count; unique failure count equals
  duplicate count; range_int failure count matches out-of-band
  count; computed MST check digit is always accepted; any valid VN
  mobile prefix passes; non-mobile prefixes are rejected).
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `dqkit` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- Zero runtime dependencies.

### Notes
- The MST checksum algorithm is the corrected version from
  `vn-tax-invoice-validator` (no `mod == 1 → invalid` carve-out),
  verified against real public MSTs: Vietcombank `0100109106`, FPT
  `0301442379`, Mobile World `0301448243`, Vietjet `0309532909`.
- The bundled CCCD province-code registry is the 2024 snapshot.
  Production callers override via the simulator / registry abstraction
  when provinces merge or rename (VN restructures provinces every
  few years per Resolution 1211/2016/UBTVQH13 + amendments).
- The VN postal-code check enforces the 2018 5-digit format
  (VietPost adopted per Decision 2475/QĐ-BTTTT). Pre-2018 numeric
  codes had variable length — production callers loading historical
  data may need to skip this check on the legacy column.
- Suite JSON files are intentionally hand-editable. The CLI emits
  pretty-printed JSON with indent=2 so diffs in source control read
  cleanly. Caller adoption pattern: commit the suite next to the
  DDL, then run `dqkit run` in CI on every PR that touches the
  rowset.
