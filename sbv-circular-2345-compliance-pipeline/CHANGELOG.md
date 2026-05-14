# Changelog

## [0.1.0] — 2026-05-14

### Added
- `TransactionEvent` + `AuditEvent` data model with frozen,
  slot-backed invariants: positive VND, tz-aware datetimes, and
  consistency between `auth_method=BIOMETRIC` and the
  `biometric_method` field.
- Four-trigger `TriggerKind` enum (`SINGLE_TXN_OVER_10M`,
  `DAILY_CUMULATIVE_OVER_20M`, `HIGH_RISK_BENEFICIARY`,
  `INTERNATIONAL_TRANSFER`) with statically-mapped legal bases
  (`LEGAL_BASIS` dict). Single-vs-cumulative are mutually
  exclusive by construction.
- `Classifier` — stateful per-account daily-total tracker with
  `classify(txn) → AuditEvent | None`. Daily counter is keyed on
  `(account, occurred_at.date())` so it resets at the UTC+7 day
  boundary. Exposes `daily_total(account, day)` for audits.
- `AuditLedger` — append-only, hash-chained in-memory store:
  - `record_hash = SHA-256(prev_hash || seq_be8 || sealed_at_iso || canonical_json(event))`
  - `verify()` walks the chain end-to-end; mismatch raises
    `TamperDetected(sequence_number, reason)`.
  - `query(since, until, account, triggered_kind)` filters in O(n).
- `seal_day(day, sealed_at)` — Merkle root of all records whose
  `event.txn.occurred_at.date()` equals the seal day. Bitcoin-style
  odd-leaf duplication. Empty day → `EMPTY_ROOT = "0" * 64`.
- Standalone `merkle_root(leaves)` + `hash_pair(a, b)` over 64-char
  hex SHA-256 leaves. Rejects non-hex / wrong-length inputs.
- 5-year retention enforcement (`RETENTION_YEARS = 5`):
  `retention_cutoff(today)` with Feb-29 leap-year fallback,
  `status(record, today) → RetentionStatus`,
  `summarise(records, today=today) → RetentionSummary`,
  `archive_candidates`.
- Regulator-format CSV exporter with the canonical 17-column
  schema (`REGULATOR_CSV_COLUMNS`) including triggered_kinds joined
  by `|`, biometric_method (blank when not biometric), and the
  hash-chain coordinates (record_hash + prev_hash) for auditor
  traceability.
- JSON `ReportSummary` aggregating totals + breakdowns by trigger,
  channel, and auth method, plus `total_value_vnd` and
  `biometric_verified_count`.
- `io_jsonl` codec — round-trippable TransactionEvent JSONL and
  ledger JSONL. `load_ledger()` automatically calls `verify()` on
  reload, so on-disk tampering of the persisted file is caught
  immediately.
- Seeded synthetic generator with 5 controllable mix parameters:
  small / large / cumulative-triples / cross-border / high-risk
  beneficiary. Each cumulative bucket emits **three** 8–9.9M-VND
  txns from the same account so the third reliably crosses the
  20M-VND daily threshold (a 2-txn group would only reach 19.8M
  max and never fire CUMULATIVE).
- `sbv2345` CLI with seven subcommands: `info`, `simulate`,
  `ingest`, `verify`, `seal-day`, `report` (CSV or JSON),
  `retention`.
- **104 tests** including 5 Hypothesis properties.
- mypy `--strict` clean over 10 source files; ruff + ruff-format
  clean.
- Multi-stage slim Docker image, non-root `sbv` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

### Notes
- Decision 2345's "tổng giao dịch trong ngày vượt 20 triệu" is
  read with strict `>`: a daily total of exactly 20M doesn't fire
  the cumulative trigger. Matches `test_exactly_10m_does_not_fire_single`'s
  reasoning applied to the cumulative bucket.
- Single-vs-cumulative mutual exclusion is encoded in the `elif`
  in `Classifier.classify` — a 30M-VND txn fires SINGLE only, never
  also CUMULATIVE. Test
  `test_single_does_not_also_fire_cumulative` pins this.
- `cccd_index_hash`-style searchable hashes are deliberately not
  part of this pipeline — the eKYC pipeline already handles that.
  Here we keep account numbers in plaintext within the ledger
  because regulators need to inspect them in audit responses.
- The persisted ledger format is JSONL one-record-per-line by
  design: `tail -f` works, `jq` works, and corruption of one line
  fails closed via the chain check rather than silently dropping a
  block.
