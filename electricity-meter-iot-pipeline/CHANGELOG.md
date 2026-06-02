# Changelog

## [0.1.0] — 2026-05-17

### Added
- `Meter`, `Reading`, `ConsumptionInterval` frozen-slots dataclasses
  with validation at construction (tz-aware datetimes, integer
  `cumulative_kwh_x100` in `[0, 999_999_999]`, quality enum, monotone
  interval timestamps).
- `MeterKind` enum: `RESI_1P` (single-phase residential), `RESI_3P`
  (three-phase residential), `COMM` (commercial — uses TOU pricing,
  out of scope here).
- `derive(readings, max_gap_minutes=90)` — cumulative-counter →
  per-interval kWh fold. Handles:
  * Out-of-order arrival (sorts by `observed_at` per-meter).
  * Duplicates (same timestamp; keeps the higher cumulative).
  * 7-digit-counter rollover via plausibility heuristic
    (wrap path < backward jump AND > 50% of meter range).
  * Faulty backward jumps (dropped — no negative intervals).
  * Long gaps split into 30-min `is_estimated=True` chunks with
    proportionally-distributed kWh.
- 6-tier VN residential tariff (Bậc 1 — 6) per
  **Quyết định 28/2014/QĐ-TTg** with November-2023 rates:
  `1806 / 1866 / 2167 / 2729 / 3050 / 3151 VND/kWh`.
- `compute_bill(kwh)` returns `(breakdown, subtotal_vnd, vat_vnd,
  grand_total_vnd)` with banker's-rounding VAT (default 8% per
  Nghị quyết 43/2022).
- Anomaly detectors as pure functions:
  * `find_gaps` — runs of estimated intervals ≥ N minutes per meter.
  * `find_spikes` — intervals where per-hour kWh > k × historical mean.
    Historical mean uses only non-estimated intervals (cold-start
    tolerance: meters with < N real readings are skipped).
  * `find_stuck` — runs of ≥ N near-zero intervals per meter.
- `bill_meters(intervals, period_start, period_end)` — monthly bills
  with **pro-rata** intervals at month boundaries (a 23:30 → 00:00
  interval straddling 31 Mar / 1 Apr is split 30 min into March).
  Sparse output: meters with zero in-window consumption produce no
  bill.
- Seeded synthetic generator (`simulator.generate`) producing
  meters + 30-min cumulative readings with a smoothed diurnal load
  curve (peak ~19:00), configurable `gap_fraction`,
  `out_of_order_fraction`, and `rollover_fraction`.
- Type-checked JSONL codec with `_require_str` / `_require_int` /
  `_require_bool` decoders (rejects `bool` for `int`, string for
  `bool`, unknown enum values).
- CLI `evnmeter info | simulate | derive | anomaly | bill | quote | summary`.
  The `quote` subcommand answers "what would a bill of N kWh cost?"
  without needing any meter data — useful for ops what-if checks.
- 85 tests including 5 Hypothesis properties (total kWh preserved
  across resampling; intervals never overlap per meter; for any
  kWh value `grand_total == subtotal + vat`; bill is monotonic in
  kWh; combined bill ≥ sum-of-parts under progressive tariff).
- mypy `--strict` clean over 9 source files; ruff clean.
- Multi-stage slim Docker image, non-root `evnmeter` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- Zero runtime dependencies.

### Notes
- The initial CSS-style `pyproject.toml` used the ruff `TC`
  selector for type-checking imports. The version of ruff installed
  on this machine (`0.7.0`) uses the older `TCH` name; renamed
  in this project's config so the lint gate runs.
- The lazy-loading `__init__.py` pattern (TYPE_CHECKING imports
  rebound at runtime via `__getattr__` + `_LAZY` string lookups)
  triggers a false-positive `TCH004` from ruff because the static
  analyser can't see the string-key reflection. Added
  `[tool.ruff.lint.per-file-ignores]` exemption for
  `src/evnmeter/__init__.py` rather than disabling the rule globally.
- Rollover detection uses a **plausibility heuristic**, not just
  "next < prev". A small backward step (e.g. 100 kWh down) is
  treated as a fault and the offending reading is dropped — only
  near-full-range backward jumps qualify as wraps. This prevents
  meter-firmware glitches from generating spurious giant
  consumption deltas.
- The `find_spikes` baseline excludes estimated intervals — gap-filled
  consumption is too uncertain to be trusted as baseline. Meters
  with < 10 real readings are skipped entirely (cold-start tolerance).
- `find_stuck` ignores `CREATED`-state meters where no real reading
  has fired (the carrier never acknowledged the meter); those are
  installation-issue records, not stuck-meter records.
