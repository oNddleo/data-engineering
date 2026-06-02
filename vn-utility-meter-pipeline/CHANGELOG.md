# Changelog

## 0.1.0 — 2026-05-20

Initial production-grade release.

* **Schema** — frozen-slots `MeterReading` (customer + period + kWh),
  `TierUsage` (one tariff-band slice), `ElectricityBill` (pre-VAT +
  VAT + per-tier breakdown), `AnomalyFinding`. Validates billing-period
  ordering and breakdown-sum invariants on construction.
* **Tariff** — `HouseholdTariff` (6-tier progressive), `FlatTariff`,
  and `TariffSchedule` with date-effective lookup. Two bundled
  schedules: 2023-11-09 (Decision 1416/QĐ-EVN) and 2024-10-11
  (Decision 2699/QĐ-BCT, default).
* **Customer** — bundled directory of EVN's 5 regional corporations
  (EVNHANOI, EVNNPC, EVNCPC, EVNSPC, EVNHCMC) with 2-letter prefixes
  PA-PE. Customer-code validator enforces 13 characters: prefix +
  11 digits.
* **Billing engine** — `compute_bill` slices household usage across
  the 6 tier bands; flat categories use a single rate. VAT is 10%
  per Decree 209/2013/NĐ-CP (ceil-style integer math).
* **Aggregator** — `aggregate_annual` rolls up bills to per-customer
  totals. Rejects mixed categories per customer.
* **Anomaly detection** — `find_zero_usage` (0 kWh after non-zero
  history; excludes true vacancies), `find_sudden_drops` (> 80%
  default drop vs trailing 3-month baseline), `find_unrealistic_spikes`
  (> 5× default jump vs baseline).
* **Simulator** — `generate(n_customers, n_months, seed)` produces a
  realistic 12-month per-customer stream allocated across the 5
  provincial units and 5 customer categories. Configurable cohorts
  inject SUDDEN_DROP and UNREALISTIC_SPIKE anomalies in the final
  month.
* **CLI** — `info | units | tariff | simulate | bill | summary |
  anomaly`; `anomaly` exits 2 when any finding fires.
* **JSONL codec** — round-trip for `MeterReading`, `ElectricityBill`,
  `AnnualSummary`, `AnomalyFinding`. Tier-breakdown rows are nested
  in the bill JSON.
* **Quality gate** — 134 tests with Hypothesis property tests
  (bill amounts non-negative, tier sums conserve, monotone in kWh,
  JSONL round-trip, aggregator kWh conservation); `mypy --strict`
  clean; ruff lint + format clean; zero runtime deps.
