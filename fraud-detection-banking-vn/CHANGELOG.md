# Changelog

## [0.1.0] — 2026-05-14

### Added
- `TransactionRequest` data type with strict invariants: positive
  amount, tz-aware datetimes, OTP issued/verified must be both-set
  or both-None, verified can't precede issued.
- `Decision` enum with three tiers (`ALLOW`, `REVIEW`, `BLOCK`)
  and `FraudDecision` carrying score + sorted signal trail +
  measured `latency_ms` for observability.
- Vietnamese-text normaliser (`normalize_vn_text`) that handles
  both NFD-decomposable diacritics **and** the special letter
  `đ`/`Đ` which NFD doesn't decompose.
- Five scam-keyword categories with curated dictionaries from
  the State Bank of Vietnam fraud-warning advisories:
  - `CONG_AN_IMPERSONATION` (55 pts)
  - `CRYPTO_FOREX_SCAM` (40 pts)
  - `WRONG_TRANSFER_SCAM` (35 pts)
  - `JOB_SCAM` (30 pts)
  - `LOAN_SCAM` (25 pts)
- Eight independent signal detectors:
  - `signal_keyword` — emits one hit per matched scam category
  - `signal_blacklist_beneficiary` (100 pts, instant BLOCK)
  - `signal_new_beneficiary_large` (25 pts when amount > 5M VND
    AND first-time beneficiary)
  - `signal_night_transfer` (10 pts, 23:00–05:00 local)
  - `signal_otp_race` (35 pts, OTP verified < 10s after issuance)
  - `signal_round_amount_below` (15 pts, 9.5M–10M structuring band)
  - `signal_velocity_burst` (25 pts, > 5 outgoing in 5 min)
  - `signal_beneficiary_hot` (35 pts, ≥ 5 distinct sources in 1h)
- `StateStore` with per-account `AccountState` (prior beneficiaries
  + bounded deques of recent outgoing / incoming sources). Lookups
  O(1); deques have `maxlen=200` to cap memory.
- `FraudEngine.evaluate(req)` — orchestrator that runs all 8 signal
  detectors, sums points, maps to `Decision`, updates state, and
  measures latency via `time.perf_counter`.
- JSONL codec for `TransactionRequest` and `FraudDecision` with
  type-checked decoders.
- Seeded synthetic simulator with 7 injection knobs covering every
  scam category + blacklist + velocity + OTP race + round-amount
  patterns.
- `fraudvn` CLI: `info`, `simulate`, `evaluate` (`--summary`
  reports decision counts + p50/p95/max latency).
- **106 tests** including 6 Hypothesis properties.
- mypy `--strict` clean over 9 source files; ruff + ruff-format
  clean.
- Multi-stage slim Docker image, non-root `fraud` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

### Notes
- Latency budget is 200 ms; measured p95 in CI is ~0.04 ms. The
  budget is intentionally generous so production deployments have
  headroom for KMS-key fetches, Redis lookups, and a per-account
  ML-score side call.
- The Vietnamese keyword matcher's `đ`-replacement happens BEFORE
  NFD because NFD doesn't decompose `đ` into `d` + combining
  characters — it's treated as an atomic Latin Extended letter.
  Missing this is the most common Vietnamese-text-handling bug
  I've seen in production codebases.
- Single-CRIT signals (BLACKLIST_BENEFICIARY at 100 pts) reach the
  block threshold on their own. Mid-weight signals (KEYWORD_CONG_AN
  at 55 pts) land in REVIEW alone but combine with any other
  signal to push past 100 and BLOCK.
- State is updated **after** the decision is computed, but **always**
  — even blocked transactions age the velocity counter so the next
  retry hits VELOCITY_BURST sooner.
- The "complementary structuring" relationship between this project
  and `anti-money-laundering-graph`: this one is real-time
  per-initiator; that one is batch per-recipient. Together they
  cover both ends of a smurfing operation.
