# Changelog

## 0.1.0 — 2026-05-19

Initial production-grade release.

* **Schema** — frozen-slots `CDR`/`RatedCDR`/`MonthlyBill`/`FraudFinding`
  dataclasses with kind-specific validation (VOICE requires
  `duration_seconds > 0`; SMS requires `n_messages > 0`; DATA requires
  `bytes_used > 0`; each kind rejects the other kinds' metrics).
* **Carrier directory** — 5 VN mobile operators (Viettel, VinaPhone,
  MobiFone, Vietnamobile, Reddi) with prefix tables from
  Decision 2730/QĐ-BTTTT 2018 + helpers (`normalise_msisdn`,
  `carrier_for`, `is_premium_msisdn`, `profile_for`).
* **Rating engine** — on-net/off-net × peak/off-peak voice (1,580 /
  1,780 / 1,280 / 1,480 VND/min), SMS (290 / 390), data (50 VND/MB),
  premium-voice override (8,000 VND/min), roaming overrides; Block-6
  rounding (calls < 6s free; calls 6–60s = 1 min; > 60s rounds up to
  next minute); 10% VAT per VN VAT Law.
* **Billing** — `aggregate_bills(rated_cdrs)` groups by
  `(subscriber, YYYY-MM)`; late-arriving CDRs bill into their original
  month; output sorted by `(billing_month, msisdn)`.
* **Fraud detection** — `find_premium_rate_spikes` (≥30 min/day),
  `find_foreign_roaming` (≥100,000 VND), `find_sim_swap` (Jaccard
  < 0.10 between 24h suspect window and 30d baseline).
* **Simulator** — `generate(n_subscribers, n_days, seed)` deterministic
  CDR stream; SIM-swap victims switch peer set on the final day so the
  detector cleanly separates baseline from suspect.
* **CLI** — `info | simulate | rate | bill | fraud | summary`; `fraud`
  exits 2 when any finding fires (CI-friendly).
* **JSONL codec** — round-trip for `CDR`, `RatedCDR`, `MonthlyBill`,
  `FraudFinding` with typed decoders.
* **Quality gate** — 153 tests including Hypothesis property tests;
  `mypy --strict` clean; ruff lint + format clean; zero runtime deps.
