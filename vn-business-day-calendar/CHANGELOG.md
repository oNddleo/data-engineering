# Changelog

## [0.1.0] — 2026-05-18

### Added
- `HolidayKind` enum with six values (SOLAR_FIXED / LUNAR_FIXED /
  TET / COMPENSATION / OPTIONAL / BRIDGE) covering the canonical
  Vietnamese holiday taxonomy.
- `Holiday` frozen-slots dataclass with `date`, `name_vi`, `name_en`,
  `kind`, `paid` (default `True`). Validation enforces non-empty
  names.
- `FiscalYear` frozen-slots dataclass with `label`, `start_date`,
  `end_date`, helper `contains(d)`, and `days_in_year()`.
- `VN_TZ = UTC+7` for VN-local date arithmetic.
- `vncal.lunar` — pre-computed Tết + Giỗ Tổ solar tables for
  **2020-2035 inclusive** (16 years). Cross-checked against TCTK
  official Gregorian calendar. `tet_solar(y)`, `gio_to_solar(y)`,
  `min_year()`, `max_year()`, `supported_years()` — raise
  `LookupError` outside the bundled range.
- `vncal.holidays.build_year(y)` — canonical 11-day public-holiday
  list per Article 112 of Bộ Luật Lao động 2019: 1-day Tết Dương
  Lịch + 5-day Tết Nguyên Đán block (from eve to Mùng 4) +
  Giỗ Tổ + Reunification Day + Labour Day + 2-day Quốc Khánh.
  Auto-generates compensation days when SOLAR_FIXED / LUNAR_FIXED
  fall on a weekend.
- `vncal.holidays.build_years(start, end)` — inclusive multi-year
  range.
- `vncal.calendar_ops` — business-day arithmetic:
  - `is_business_day(d)` — Mon-Fri AND not a public holiday.
  - `next_business_day(d)` / `prev_business_day(d)` — at-or-
    after / at-or-before, respectively.
  - `add_business_days(d, n)` — signed offset (positive forward,
    negative backward, `n=0` returns `d` unchanged even on weekends).
  - `business_days_between(start, end)` — half-open interval count
    `[start, end)`; negative when reversed.
  - All functions accept an optional `holidays` override set.
- `vncal.fiscal` — two FY conventions:
  - `calendar_fy(y)` — 1 Jan – 31 Dec, label `"FY<y>"`.
  - `april_march_fy(end_y)` — 1 Apr (end_y-1) – 31 Mar end_y,
    label `"FY<end_y-1>-<end_y%100>"`.
  - `fiscal_year_for(d, april_march=False)` — auto-resolve.
- `vncal.io_jsonl` — type-checked JSONL codec for `Holiday` and
  `FiscalYear`. Rejects str-as-bool sneak-ins.
- `vncal.cli` — `vncal info | holidays | is-business-day | add |
  between | fiscal-year | summary`. `is-business-day` exits **0**
  if yes, **1** if no, suitable for shell scripting.
- 89 unit tests + 11 Hypothesis properties; mypy `--strict` clean;
  ruff clean; multi-stage slim Docker image.

[0.1.0]: https://github.com/sophie-nguyenthuthuy/data-engineering/releases/tag/vn-business-day-calendar-v0.1.0
