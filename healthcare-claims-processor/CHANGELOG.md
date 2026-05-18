# Changelog

## [0.1.0] — 2026-05-17

### Added
- `Patient`, `BHYTCard`, `Claim`, `ClaimItem`, `Diagnosis`,
  `Reimbursement` frozen-slots dataclasses with validation at
  construction (tz-aware datetimes, non-negative VND amounts,
  primary-diagnosis exactly-one rule, half-open card validity).
- `ExemptionCategory` enum for the five "diện" per Article 22 of the
  2014 Law on Health Insurance: UU_TIEN_1 (children + ethnic
  minorities), UU_TIEN_2 (war veterans), UU_TIEN_3 (poor / near-poor),
  UU_TIEN_4 (employer-paid), UU_TIEN_5 (voluntary).
- `CareLevel` enum: TU / TINH / HUYEN / XA / OTHER mapping to the
  VSS-published referral chain.
- `Patient.age_years_at(asof)` helper computing completed years
  for child-coverage rules.
- BHYT card-number format validation per VSS Decision 1351/QĐ-BHXH
  2015: 1 scheme letter + 1 priority digit (1-5) + 13 digits. Six
  scheme letters: D / H / T / C / G / X.
- `decode_prefix(card_number) → PrefixInfo` resolving the 2-char
  prefix to a scheme name + category enum.
- Bundled ICD-10-VN lookup with ~40 common diagnoses across 11
  chapters (A-Z). Sub-code → parent fallback (`E11.9` → `E11`) for
  billing aggregation matching VSS back-end behaviour.
- Coverage rate table per Nghị định 146/2018/NĐ-CP Article 14 + 22.
  Base rates: 100% / 100% / 95% / 80% / 80% by category.
- Referral-penalty multiplier: 40% at TU without referral, 60% at
  TINH without referral, 100% (no penalty) at HUYEN / XA / OTHER.
  Cross-province visits trigger the penalty even with a referral,
  unless emergency.
- `calculate(claim, emergency=False) → Reimbursement` with banker's
  (round-half-to-even) integer-VND math.
- Discrepancy notes (without rejection) for line-math mismatches,
  header subtotal disagreements, and invalid card formats —
  matching VSS's real-world tolerance for noisy hospital billing.
- Seeded synthetic generator producing patients + cards + claims
  with realistic distribution across the 5 categories × 5 care
  levels, with referral status correlated to care level (70% at
  TU/TINH, 100% at HUYEN/XA/OTHER) and 15% cross-province visits.
- Type-checked JSONL codec for all record types.
- CLI `bhyt info | simulate | decode | icd | calc | summary` with
  three-way exit codes for `decode` and `icd` (0 = found, 1 =
  not found / invalid).
- 89 tests + 7 Hypothesis properties:
  - any valid-format card always decodes
  - any unknown scheme letter is rejected
  - base rates always in `[0, 10000]` bps
  - effective rate components always in `[0, 10000]` bps
  - `insurer + patient == subtotal` for any claim
  - insurer pay always in `[0, subtotal]`
  - emergency calc always pays ≥ non-emergency for the same claim
- mypy `--strict` clean over 9 source files; ruff clean.
- Multi-stage slim Docker image, non-root `bhyt` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- Zero runtime dependencies.

### Notes
- The first draft of the BHYT card validator assumed "2 letters +
  13 digits" but the real VSS format (Decision 1351/QĐ-BHXH 2015)
  has 1 letter + 1 priority digit + 13 digits. Caught when the
  simulator emitted `D40179...` and the schema validator rejected
  the digit `4`. Fixed in both `schema.py` and `card.py`.
- The bundled ICD-10-VN subset (~40 codes) covers the most common
  outpatient diagnoses per VSS aggregate stats. Production callers
  with access to the full Bộ Y tế 2020 publication (~14,400 codes)
  can extend via the same `lookup` API.
- K-DRG (Diagnostic Related Group) inpatient bundling **is not
  modelled** here beyond the basic line-item calculator. Production
  callers using K-DRG layer their bundle prices upstream (typically
  via the VSS-published `cn_drg_2024.csv` table) and feed the
  bundled rate in as a single line.
- The 95% rate for `UU_TIEN_3` represents the near-poor band; the
  100% rate for strictly-poor households is modelled by using
  `UU_TIEN_1` instead, matching what VSS publishes as the
  practical encoding.
