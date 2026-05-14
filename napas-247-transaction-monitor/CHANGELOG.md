# Changelog

## [0.1.0] — 2026-05-14

### Added
- `Transaction` dataclass (NAPAS 247-shaped) with frozen, slot-backed
  invariants: positive VND amount, 6-digit NAPAS BIN codes,
  timezone-aware `occurred_at`.
- `Channel` enum (MOBILE_APP / INTERNET_BANKING / ATM / BRANCH).
- Curated NAPAS BIN registry (`970418` → BIDV, `970436` →
  Vietcombank, …) with `bank_name()` lookup and `is_valid_bin()`
  validator.
- Four bundled monitoring rules with a shared `Rule` Protocol:
  - **BiometricRule** — encodes Decision 2345/QĐ-NHNN exactly:
    txn > 10M VND without biometric → `BIO_REQUIRED_SINGLE_TXN`;
    txn ≤ 10M that pushes daily cumulative > 20M without biometric →
    `BIO_REQUIRED_CUMULATIVE`. Daily counter scoped per `(account, date)`,
    so resets at the UTC+7 day boundary.
  - **VelocityRule** — sliding event-time window per initiator,
    fires when `len(window) > threshold`. Default 60s / 10 txns.
  - **StructuringRule** — tracks the just-under-10M smurfing
    pattern (default range 9.5M–10M VND, ≥ 3 hits within an hour).
  - **BlacklistRule** — O(1) `frozenset` membership check on
    `beneficiary_account`; whitespace-stripped on load.
- `MonitorEngine` orchestrator with running `EngineStats`
  (txns seen, alerts fired, breakdowns by kind + severity).
- JSONL codec (`dump_txns` / `load_txns` / `dump_alerts` /
  `load_alerts`) with type-checked decoders (`_require_int`,
  `_require_str`) so malformed payloads fail loud at the boundary.
- Seeded synthetic generator (`simulator.generate`) with 5
  anomaly-injection kinds: `bio_single`, `bio_cumulative`,
  `velocity`, `structuring`, `blacklist`.
- `n247mon` CLI: `info`, `simulate`, `monitor`. Stdin/stdout
  pipe-friendly; optional `--summary` writes stats to stderr.
- **93 tests** including 6 Hypothesis properties.
- mypy `--strict` clean over 9 source files; ruff clean.
- Multi-stage slim Docker image, non-root `n247` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

### Notes
- Decision 2345 uses **strict** ">" thresholds — a txn of *exactly*
  10M VND does **not** require biometric, even though many bank
  apps round-up trigger this conservatively. The rule is faithful
  to the regulation wording; ops can wrap it if they want
  belt-and-braces behaviour.
- BiometricRule **never** double-alerts a single txn — the
  cumulative branch is gated on `amount <= 10M` so the large-txn
  single-rule path doesn't compete with it.
- StructuringRule uses `(threshold - margin, threshold]` (open
  lower, closed upper) — so 10,000,000 VND is in-range but
  9,500,000 is not.
- The engine's `rules` property returns a defensive copy so callers
  can't mutate the internal list.
