# Changelog

## 0.1.0 — 2026-05-20

Initial production-grade release.

* **Schema** — `Employee`, `PayPeriod`, `Payslip`, `Region` (4 zones),
  `ResidencyStatus`.
* **Insurance** — BHXH/BHYT/BHTN rates per Decree 12/2025 + 58/2020;
  20× region-1 min cap for BHXH+BHYT, region-specific cap for BHTN;
  bundled 4-region min wages from Nghị định 74/2024/NĐ-CP.
* **PIT** — 7-bracket progressive resident schedule + 20% flat non-
  resident; personal/dependent deductions per Nghị quyết 954/2020.
* **Engine** — `compute_payslip(employee, period)` → full breakdown
  including employer-cost rollup.
* **Simulator** — seeded employee + period generator.
* **CLI** — `info | brackets | minwage | compute | simulate`.
* **JSONL codec** — round-trip for `Employee`, `PayPeriod`, `Payslip`.
* **Quality gate** — 66 tests with Hypothesis property tests
  (gross == net+insurance+pit, dependent monotonicity, SHUI cap
  plateau); `mypy --strict` clean; ruff lint + format clean; zero
  runtime deps.
