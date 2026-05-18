# Changelog

## [0.1.0] — 2026-05-18

### Added
- `TripEvent`, `TripEventKind` (REQUEST / ACCEPT / PICKUP / DROPOFF /
  CANCEL / EXPIRE / SURGE_UPDATE), `CancelBy` (RIDER / DRIVER /
  SYSTEM), `VehicleClass` (MOTORBIKE / CAR_4 / CAR_7 / DELIVERY),
  `Trip`, `FareBreakdown`, `SurgeWindow`, `DriverShift`
  frozen-slots dataclasses with `__post_init__` validation
  (tz-aware `occurred_at`, non-negative VND amounts, surge ≥ 10000
  bps, DROPOFF requires fare > 0, CANCEL requires `cancel_by`).
- `VN_TZ = UTC+7` for VN-local shift cohorting.
- `vntrip.districts` — bundled directory of 20 VN central districts
  (HCM × 10, HN × 7, DN × 3) with VI + EN names.
- `vntrip.state.stitch()` — per-trip event-stream stitching with
  state-machine validation (REQUEST → ACCEPT → PICKUP → DROPOFF
  or CANCEL at any point; EXPIRE only post-REQUEST). Throws
  `ValueError` on illegal transitions; output sorted by
  `(requested_at, trip_id)`.
- `vntrip.fare.compute_fare()` — VN rate card (Grab consumer-app
  pricing as of May 2026): MOTORBIKE 12k base + 4k/km + 200/min,
  CAR_4 25k base + 11k/km + 400/min, etc. Surge applied as a
  basis-point multiplier with banker's (round-half-to-even)
  rounding on integer VND. Configurable rate card.
- `vntrip.analytics.eta_accuracy_pct()` + `eta_accuracy_summary()`
  — actual-over-estimated pickup ratios, with median / p90 / p99
  percentiles.
- `vntrip.analytics.surge_windows()` — district × hour-of-VN-day
  buckets with completion rate + avg surge. `is_surging` flags
  windows with surge ≥ 1.2× AND completion < 50%.
- `vntrip.analytics.driver_shifts()` — per (driver, shift_date)
  online-time, on-trip-time, trips completed, revenue. Utilization
  is on-trip / online.
- `vntrip.fraud.find_cancel_abuse()` — drivers with cancel-rate ≥
  30% AND median accept-to-cancel lag ≤ 30s. Configurable thresholds.
- `vntrip.fraud.find_phantom_trips()` — drivers with completed
  trips of distance < 200m OR duration < 30s. Surfaced per-driver
  with aggregate count.
- `vntrip.simulator.generate()` — seeded synthetic event stream
  with six trip outcomes (completed / expired / rider-cancelled /
  driver-cancelled / cancel-abuse / phantom-completion). Surge
  multipliers spike during VN rush hours (07-09 + 17-19).
- `vntrip.io_jsonl` — type-checked JSONL codec for events, trips,
  fares, surge windows, driver shifts, and fraud findings.
- `vntrip.cli` — `vntrip info | simulate | stitch | fare | surge |
  shifts | fraud | summary`. `fraud` exits **2** when findings exist.
- 110 unit tests + 7 Hypothesis properties; mypy `--strict` clean;
  ruff clean; multi-stage slim Docker image.

[0.1.0]: https://github.com/sophie-nguyenthuthuy/data-engineering/releases/tag/ride-share-trip-pipeline-v0.1.0
