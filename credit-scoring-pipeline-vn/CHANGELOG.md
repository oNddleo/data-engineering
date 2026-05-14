# Changelog

## [0.1.0] — 2026-05-14

### Added
- `CICGroup` IntEnum (1–5) + `PROVISION_RATE` mapping (0 / 5 / 20 /
  50 / 100 %) per Thông tư 11/2021/TT-NHNN Điều 12.
- `VN_NAMES` mapping using the canonical Vietnamese names from the
  Thông tư ("Nợ đủ tiêu chuẩn" … "Nợ có khả năng mất vốn").
- `group_from_days_past_due` with strict cutoffs at 10 / 90 / 180 /
  360 days; negative input treated as zero.
- Frozen, slot-backed dataclasses with strict invariants:
  `CreditContract` (positive amount; `closed_at >= opened_at`),
  `GroupAssessment` (`as_of_month` must be the 1st; non-negative
  principal / interest / DPD), `Inquiry`, `Borrower` (cross-validates
  contract / assessment / inquiry IDs).
- Six product types: `TERM_LOAN`, `MORTGAGE`, `AUTO_LOAN`,
  `CREDIT_CARD`, `OVERDRAFT`, `BUSINESS_LOAN`.
- Month helpers: `first_of_month`, `add_months`, `months_between`
  with leap-safe day clamping.
- `extract(borrower, observation_date)` — produces a 23-field
  `FeatureVector` with strict point-in-time filtering. Implements
  the Điều 11 borrower-level cascade by taking max group across
  active contracts.
- Monthly-payment estimator per product type (36-month
  amortisation for term/auto/business loans; 240-month for
  mortgages; 5 % minimum for credit cards; 2 % for overdrafts).
- `baseline_score(features)` — transparent 300–900 scorecard with
  every penalty / bonus labelled in `Score.reasons`. Anchors:
  group 2 = −50; group 5 = −400; each group-2+ month = −5; each
  inquiry/6m = −10; 5y history = +30; DTI > 50/70 % = −50/−100;
  5+ lenders = −30.
- Seeded synthetic generator with three risk profiles (`clean` /
  `watch` / `distressed`) that produce reproducible borrowers with
  controlled CIC-group escalation and credit-shopping inquiries.
- JSONL codec — `dump_borrowers` / `load_borrowers` / `dump_features` /
  `dump_scores` with type-checked decoders so malformed payloads
  fail loud at the boundary.
- `cicscore` CLI: `info`, `simulate`, `extract`, `score`, `inspect`.
- **99 tests** including 5 Hypothesis properties:
  - `group_from_days_past_due` always returns a `CICGroup`
  - provision amount is monotonic non-decreasing in group severity
  - `baseline_score` always returns a value in `[300, 900]`
  - group-5 provision equals 100 % of principal
  - group-1 provision equals 0 regardless of principal
- mypy `--strict` clean over 8 source files; ruff + ruff-format
  clean.
- Multi-stage slim Docker image, non-root `cic` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

### Notes
- The DPD cutoffs are **strict** ("<10 / <90 / <180 / <360" rather
  than "≤"). This matches the canonical reading of the Thông tư
  and means a 10-day-overdue contract is firmly Group 2, not 1.
- The 24-month window is `[obs_month − 23, obs_month]` inclusive —
  the obs month counts as month 1 of the window so the window
  contains exactly 24 distinct months. This is the same convention
  CIC uses on their B-Score report.
- `current_max_group` is the borrower-level effective group per
  Điều 11 (worst contract's group cascades), not a single
  contract's classification. `worst_group_ever` is the all-time
  high across the visible history.
- Baseline scoring is intentionally **clipped** at 300 / 900. The
  test suite exercises both clips: a group-5 borrower lands at
  exactly 300 even though the raw sum would be 295.
- `provision_estimate_vnd` sums `outstanding × provision_rate` per
  active contract using each contract's *own* group, not the
  cascaded borrower-level group — to match how banks compute their
  actual loan-loss provisions for regulatory reporting.
- Closed contracts (`closed_at <= observation_date`) are dropped
  from active-contract features but still feed
  `worst_group_ever` and `months_since_first_credit`.
