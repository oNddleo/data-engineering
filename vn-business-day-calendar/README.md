# vn-business-day-calendar

**Vietnamese public-holiday + working-day calendar** —
lunar-to-solar Tết conversion, the canonical 11-day public holiday
list per **Article 112 of Bộ Luật Lao động 2019** (Labour Code),
PM-announced compensation days, business-day arithmetic, and two
fiscal-year conventions. Useful across the catalogue for SLA
windows, billing cycles, working-day deltas.

Pure-Python, zero dependencies.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Bundles Tết + Giỗ Tổ solar dates** for **2020-2035** (16 years)
   — values cross-checked against the official TCTK Gregorian
   calendar publications.
2. **Builds the canonical 11-day public-holiday list** per Article
   112 of the 2019 Labour Code, with 5-day Tết block from the eve
   (giao thừa) and Quốc Khánh + 1 extension.
3. **Generates compensation days** automatically when a fixed-date
   or lunar-fixed holiday falls on a weekend (Sat/Sun → next
   Mon/Tue).
4. **Performs business-day arithmetic** — `is_business_day`,
   `next_business_day`, `prev_business_day`, `add_business_days
   (signed)`, `business_days_between (half-open)`.
5. **Resolves fiscal years** in two flavours: calendar (`FY2026`)
   and April-March (`FY2025-26`), matching VN private and
   public/JV conventions.

## Bundled holidays (Article 112)

| Date          | Holiday VI                       | EN gloss               |
| ------------- | -------------------------------- | ---------------------- |
| 1 Jan         | Tết Dương Lịch                   | New Year's Day         |
| 30/12-4/1 lunar | Tết Nguyên Đán (5 days)        | Lunar New Year         |
| 10/3 lunar    | Giỗ Tổ Hùng Vương                | Hung Kings Commemoration |
| 30 Apr        | Ngày Giải phóng miền Nam         | Reunification Day      |
| 1 May         | Ngày Quốc tế Lao động            | International Labour Day |
| 1 Sep + 2 Sep | Quốc Khánh + extension           | National Day           |

Compensation rule: any of the above falling on Sat/Sun → next
Monday is also a paid day off. The 5-day Tết block is treated
as one unit and not auto-compensated (PM announces shifts annually).

## Bundled lunar table

`vncal.lunar.tet_solar(year)` and `gio_to_solar(year)` cover
**2020-2035 inclusive** (16 years). Values verified against
TCTK, vietcalendar.vn, and en.wikipedia.org/wiki/Tết.

Spot checks:

| Year | Tết           | Giỗ Tổ          |
| ---- | ------------- | --------------- |
| 2024 | 10 Feb (Dragon)| 18 Apr         |
| 2025 | 29 Jan (Snake) | 7 Apr          |
| 2026 | 17 Feb (Horse) | 26 Apr (Sunday → comp day 27 Apr) |
| 2027 | 6 Feb (Goat)   | 16 Apr         |

Years outside the bundled range raise `LookupError` — callers
should extend the table.

## Components

| Module               | Role                                                                |
| -------------------- | ------------------------------------------------------------------- |
| `vncal.schema`       | `Holiday`, `HolidayKind`, `FiscalYear` frozen-slots dataclasses     |
| `vncal.lunar`        | `tet_solar(y)` + `gio_to_solar(y)` lookup tables (2020-2035)        |
| `vncal.holidays`     | `build_year(y)` / `build_years(start, end)` — Article 112 + comps   |
| `vncal.calendar_ops` | `is_business_day`, `next/prev_business_day`, `add_business_days`, `business_days_between` |
| `vncal.fiscal`       | `calendar_fy(y)` / `april_march_fy(end_y)` / `fiscal_year_for(d)`   |
| `vncal.io_jsonl`     | Type-checked JSONL codec for holidays + fiscal years                |
| `vncal.cli`          | `vncal info \| holidays \| is-business-day \| add \| between \| fiscal-year \| summary` |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
vncal info
vncal holidays --year 2026
vncal holidays --year 2024 --year-to 2026 --output holidays.jsonl
vncal is-business-day --date 2026-05-18    # exits 0 if yes, 1 if no
vncal add  --date 2026-04-24 --days 1       # → 2026-04-28 (skips Sat/Sun + Giỗ Tổ + comp)
vncal between --start 2026-05-18 --end 2026-05-25  # → 5
vncal fiscal-year --date 2026-05-18                 # → FY2026
vncal fiscal-year --date 2026-05-18 --april-march   # → FY2026-27
vncal summary --year 2026
```

Sample `holidays --year 2026`:

```
date         day kind          name
2026-01-01   Thu SOLAR_FIXED   Tết Dương Lịch
2026-02-16   Mon TET           Tết Nguyên Đán (30 Tết)
2026-02-17   Tue TET           Tết Nguyên Đán (Mùng 1)
2026-02-18   Wed TET           Tết Nguyên Đán (Mùng 2)
2026-02-19   Thu TET           Tết Nguyên Đán (Mùng 3)
2026-02-20   Fri TET           Tết Nguyên Đán (Mùng 4)
2026-04-26   Sun LUNAR_FIXED   Giỗ Tổ Hùng Vương
2026-04-27   Mon COMPENSATION  Bù Giỗ Tổ Hùng Vương
2026-04-30   Thu SOLAR_FIXED   Ngày Giải phóng miền Nam
2026-05-01   Fri SOLAR_FIXED   Ngày Quốc tế Lao động
2026-09-01   Tue SOLAR_FIXED   Quốc Khánh (1/9)
2026-09-02   Wed SOLAR_FIXED   Quốc Khánh
```

Sample `summary --year 2026`:

```json
{
  "year": 2026,
  "n_holidays": 12,
  "n_business_days": 251,
  "n_calendar_days": 365,
  "holidays_by_kind": {
    "COMPENSATION": 1,
    "LUNAR_FIXED": 1,
    "SOLAR_FIXED": 5,
    "TET": 5
  },
  "tet_eve": "2026-02-16"
}
```

## Library

```python
from datetime import date
from vncal.calendar_ops import (
    add_business_days, business_days_between, is_business_day,
)
from vncal.fiscal    import calendar_fy, fiscal_year_for
from vncal.holidays  import build_year
from vncal.lunar     import tet_solar

# Tết 2026 = 17 Feb (Year of the Horse)
assert tet_solar(2026) == date(2026, 2, 17)

# 2026 has 12 paid public holidays (11 + 1 compensation)
holidays = build_year(2026)
assert len(holidays) == 12

# Business-day arithmetic — automatically uses the bundled calendar
assert is_business_day(date(2026, 2, 17)) is False    # Mùng 1
assert add_business_days(date(2026, 4, 24), 1) == date(2026, 4, 28)
assert business_days_between(date(2026, 5, 18), date(2026, 5, 25)) == 5

# Fiscal year resolution
assert fiscal_year_for(date(2026, 5, 18)).label == "FY2026"
assert fiscal_year_for(date(2026, 5, 18), april_march=True).label == "FY2026-27"
```

## Key design decisions

- **Lookup-table lunar conversion.** Implementing the full Chinese-
  astronomical lunar algorithm (sun/moon longitudes, Metonic cycle,
  leap-month insertion rules) would add 500+ lines without changing
  the answer for any practical year. Bundling the pre-computed
  table for 2020-2035 is simpler, auditable, and fails loudly via
  `LookupError` outside the supported range.
- **Tết is treated as one 5-day block.** Each Tết day gets its own
  `Holiday` entry (kind=TET) but the auto-compensation loop skips
  TET — real Tết extensions are PM-announced and vary by year.
  Callers can append BRIDGE or OPTIONAL entries as needed.
- **Compensation triggers on SOLAR_FIXED + LUNAR_FIXED.** Article
  115 of the Labour Code: any paid public holiday falling on a
  weekend rolls to the next business day. This catches Giỗ Tổ
  (lunar) and the four fixed solar holidays.
- **Half-open business-day intervals.** `business_days_between(a,
  b)` counts `[a, b)` — the standard interval convention that
  makes consecutive ranges compose without double-counting. Sign
  follows `b - a` (negative when reversed).
- **Two fiscal-year flavours, no surprise behaviour.** Calendar FY
  is the VN private-sector default; April-March is for public-
  sector and many JP-VN joint ventures. `fiscal_year_for(d)`
  decides based on the `april_march` flag — no auto-detection.
- **No external deps.** Pure stdlib `datetime` + `dataclasses` +
  `enum` + `json`. Easy to vendor / embed into other catalogue
  projects.

## Quality

```bash
make test       # 89 tests + 11 Hypothesis properties
make type       # mypy --strict
make lint
```

- **89 tests**, 0 failing; 11 Hypothesis properties (weekends are
  never business days; `next_business_day` is always a business
  day; `prev_business_day` is always a business day; `add_business
  _days` always lands on a business day; `add(add(d, n), -n) == d`
  for business-day `d`; `business_days_between(a, b) == -between(b,
  a)`; between is consistent with add; `calendar_fy(d.year)`
  always contains `d`; `fiscal_year_for(d)` always contains `d`
  in both flavours; Tết block is always 5 consecutive days; Tết
  eve is one day before Mùng 1).
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `vncal` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
