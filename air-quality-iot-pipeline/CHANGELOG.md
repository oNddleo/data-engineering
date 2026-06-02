# Changelog

## [0.1.0] — 2026-05-17

### Added
- `Station`, `Reading`, `WindowAverage` frozen-slots dataclasses
  with validation at construction (tz-aware datetimes, non-negative
  concentrations, VN-bounding-box lat/lon, quality ∈ GOOD /
  CALIBRATING / STALE).
- `Pollutant` enum (PM25, PM10, NO2, SO2, O3, CO) and `StationKind`
  enum (STATE — Bộ TNMT; PRIVATE — PAM Air & friends).
- `aqi_for(pollutant, value_x10) → PollutantAQI` — piecewise-linear
  interpolation on QĐ 1459/QĐ-TCMT breakpoints; concentrations above
  the top breakpoint clamp to AQI 500 (HAZARDOUS).
- `station_aqi(station_id, readings_x10) → StationAQI` — composite
  AQI as the **max** over per-pollutant contributions, with
  `dominant_pollutant` recording which one drove the score.
- `band_for_aqi(aqi) → AQIBand` — total mapping over `[0, 500]` to
  the six VN bands.
- `aggregate(readings, window) → list[WindowAverage]` —
  out-of-order tolerant; windows aligned to the **VN_TZ epoch**
  (24-h bars start at 00:00 VN, not UTC midnight). CALIBRATING /
  STALE readings excluded from the mean.
- `latest_per_station(averages)` — `{station_id: {pollutant: latest}}`
  view, drives station-AQI computation.
- `find_public_alerts(aqis, now, min_band=UNHEALTHY_SENSITIVE)` and
  `find_sensitive_alerts(aqis, now)` — two cohort tiers with
  sensitive groups escalated one band earlier (children, elderly,
  respiratory cohort).
- `band_distribution(aqis)` — count per band, zero-filled for all
  six VN bands.
- Seeded synthetic generator producing 6-pollutant 15-min readings
  with diurnal NO2/CO/O3 curves, province-baseline differences (HN
  PM2.5 baseline higher than DN), occasional CALIBRATING quality
  for PRIVATE stations, and out-of-order arrival to exercise the
  aggregator's resort step.
- Type-checked JSONL codec for Station / Reading / WindowAverage / Alert.
- CLI `aqipipe info | simulate | aggregate | aqi | alerts | quote | summary`.
- `quote PM25 500` shows AQI 100 (top of MODERATE);
  `quote PM25 1500` shows AQI 200 (top of UNHEALTHY) — exact boundary
  values that validate the interpolation math.
- 83 tests + 6 Hypothesis properties (AQI in `[0, 500]` for any
  concentration; `band` field consistent with `band_for_aqi(aqi)`;
  AQI monotonic in concentration per pollutant; station AQI ≥ each
  contribution; station AQI equals max contribution; `band_for_aqi`
  total over `[0, 500]`).
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `aqipipe` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- Zero runtime dependencies.

### Notes
- The `value_x10` integer-storage convention matches the existing
  catalogue convention (rating × 100, kWh × 100, money × 1). One
  decimal place is the precision every VN AQI publication actually
  uses, and integer math eliminates the float-drift bug that haunts
  environmental databases over multi-year time series.
- An earlier draft of `test_band_distribution_counts_by_band` used
  PM25 value_x10 = 1800 expecting UNHEALTHY band, but 180 µg/m³
  actually falls in `(1501, 2500)` → VERY_UNHEALTHY. Caught and
  corrected — the breakpoint table reflects the QĐ 1459 cuts
  faithfully, not the US EPA cuts. Tightened to value_x10 = 1000
  (= 100 µg/m³, in `(801, 1500)` → UNHEALTHY).
- The QĐ 1459 PM2.5 breakpoints are tighter than the US EPA — top
  of MODERATE at 50 µg/m³ vs 35.4 µg/m³ (US). This reflects WHO 2021
  guidance integrated into the VN methodology. Production code that
  uses this module to mirror a US-AQI dashboard needs a separate
  breakpoint table — don't reuse this one for US-context display.
