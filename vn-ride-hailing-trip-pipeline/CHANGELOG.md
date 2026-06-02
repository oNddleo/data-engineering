# Changelog

## 0.1.0 — 2026-05-20

Initial production-grade release.

* **Schema** — `Trip` (frozen-slots) with 7-state `TripState` lifecycle,
  3-flavour `ServiceType` (CAR / BIKE / DELIVERY), 5-method
  `PaymentMethod` (CASH / EWALLET / BANK_CARD / CORPORATE / VOUCHER),
  `FareBreakdown` with surge-multiplier in basis points,
  `DriverSettlement` daily rollup.
* **Operator directory** — 4 active commission-based platforms in VN
  (Grab 68%, Be 24%, Xanh SM 6%, Maxim 2%) with per-service commission
  rates in basis points. Gojek (exited 2024-09-16) is intentionally
  excluded.
* **City directory** — 6 tier-1 / tier-2 cities (HCMC, Hanoi, Da Nang,
  Hai Phong, Can Tho, Nha Trang) with population + city-default peak
  surge.
* **Pricing engine** — `quote(service, distance_cm, duration_seconds,
  surge_bps)` returns `FareBreakdown` honouring per-service minimum
  fare floors. Booking fee is exempt from surge multiplication.
  `commission_split(fare, comm_bps)` separates ride revenue (subject
  to commission) from booking fee (operator keeps in full).
  Surge bounded ``[1.0×, 3.0×]`` per Bộ Công Thương soft-cap.
* **State machine** — `validate_transition(old, new)` enforces the
  trip lifecycle graph; `validate_history(states)` validates a full
  event log. Three terminal states: COMPLETED, CANCELLED, NO_DRIVER.
* **Settlement** — `aggregate_daily(trips)` groups by
  `(driver, operator, date)` and computes gross revenue, commission,
  cash collected (CASH trips), and net payable (which may be negative
  when driver collected more cash than they earned).
* **Fraud detection** — `find_ghost_rides` (distance < 100 m AND
  duration < 30 s on COMPLETED), `find_cancellation_abuse` (≥ 50%
  cancel rate over ≥ 20 trips), `find_surge_gaming` ((rider, driver)
  pair sharing ≥ 5 trips, all in surge windows).
* **Simulator** — `generate(n_riders, n_drivers, n_days, seed)` with
  configurable fraud-positive cohorts (ghost / cancel-abuse / surge-
  gaming fractions).
* **CLI** — `info | operators | cities | quote | simulate | settle |
  fraud | summary`; `fraud` exits 2 when any finding fires.
* **JSONL codec** — round-trip for `Trip`, `DriverSettlement`,
  `FraudFinding`.
* **Quality gate** — 145 tests with Hypothesis property tests;
  `mypy --strict` clean; ruff lint + format clean; zero runtime deps.
