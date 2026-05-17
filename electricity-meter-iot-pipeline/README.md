# electricity-meter-iot-pipeline

EVN (Điện lực Việt Nam) smart-meter telemetry pipeline — cumulative
30-min kWh readings → per-interval consumption → 6-tier progressive
residential billing per **Quyết định 28/2014/QĐ-TTg** + 8% VAT (Nghị
quyết 43/2022) → anomaly detection (GAP / SPIKE / STUCK).

Models a realistic VN smart-meter rollout: NB-IoT carriage means
**out-of-order arrival**, packet loss / **gaps**, occasional
duplicates, and 7-digit cumulative counter **rollover**.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Validates** `Meter` and `Reading` records at the boundary —
   tz-aware datetimes, integer `cumulative_kwh_x100` in
   `[0, 999_999_999]` (the 7-digit hardware counter), quality
   ∈ `{GOOD, ESTIMATED, PARTIAL}`.
2. **Derive pass** folds cumulative readings into per-interval
   `ConsumptionInterval`s:
   * Sorts per-meter by `observed_at` (NB-IoT is out-of-order).
   * Dedupes duplicate timestamps (keeps the higher cumulative).
   * Detects 7-digit-counter **rollover** (`9_999_999 → 0`).
   * Drops faulty backward jumps that aren't rollover.
   * Splits long gaps into 30-min `is_estimated=True` chunks with
     proportionally-distributed kWh.
3. **6-tier progressive tariff** (Bậc 1 — 6) with 8% VAT and
   banker's rounding on integer VND.
4. **Anomaly detection**: GAP (long estimated run), SPIKE (≥ k×
   historical mean per hour), STUCK (long near-zero run).
5. **Monthly billing** prorates intervals that straddle the period
   boundary; bills are sparse (zero-consumption meters omitted).

## VN tariff (Nov 2023 EVN revision)

| Tier  | Range (kWh/month) | Rate (VND/kWh) |
| ----- | ----------------- | -------------- |
| Bậc 1 | 0 — 50            | 1,806          |
| Bậc 2 | 51 — 100          | 1,866          |
| Bậc 3 | 101 — 200         | 2,167          |
| Bậc 4 | 201 — 300         | 2,729          |
| Bậc 5 | 301 — 400         | 3,050          |
| Bậc 6 | 401+              | 3,151          |

VAT is **8%** for electricity (Nghị quyết 43/2022 — the Covid-era
reduced rate, extended through 2024-2026). Production callers
override the rate via `vat_bps=` when policy changes.

Worked example for 350 kWh/month:

```
50 × 1,806 + 50 × 1,866 + 100 × 2,167 + 100 × 2,729 + 50 × 3,050
= 90,300 + 93,300 + 216,700 + 272,900 + 152,500
= 825,700 VND  (subtotal)
+ 66,056 VND   (8% VAT, banker's rounding)
= 891,756 VND  (grand total)
```

## Components

| Module                | Role                                                                  |
| --------------------- | --------------------------------------------------------------------- |
| `evnmeter.schema`     | `Meter`, `Reading`, `ConsumptionInterval`, `MeterKind`, `VN_TZ`       |
| `evnmeter.derive`     | `derive(readings, max_gap_minutes)` — cumulative → per-interval kWh   |
| `evnmeter.tariff`     | 6-tier progressive table + `compute_bill(kwh)` with 8% VAT            |
| `evnmeter.anomaly`    | `find_gaps`, `find_spikes`, `find_stuck`                              |
| `evnmeter.billing`    | `bill_meters(intervals, period_start, period_end)`                    |
| `evnmeter.simulator`  | Seeded synthetic meters + readings with realistic load curve          |
| `evnmeter.io_jsonl`   | Type-checked JSONL codec for all four record types                    |
| `evnmeter.cli`        | `evnmeter info \| simulate \| derive \| anomaly \| bill \| quote \| summary` |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
evnmeter info
evnmeter simulate --meters 12 --days 7 --gap-fraction 0.05 --seed 7 --out-dir ./raw
evnmeter derive   --input ./raw/readings.jsonl --output ./intervals.jsonl
evnmeter anomaly  --input ./intervals.jsonl --show 5
evnmeter bill     --input ./intervals.jsonl \
                  --period-start "2026-05-01T00:00:00+07:00" \
                  --period-end   "2026-06-01T00:00:00+07:00" \
                  --output ./bills.jsonl --show 5
evnmeter quote 350    # what-if tariff for any kWh value
evnmeter summary  --input ./intervals.jsonl
```

Sample `quote 350` output:

```
tier    kwh       rate           cost
1        50      1,806         90,300
2        50      1,866         93,300
3       100      2,167        216,700
4       100      2,729        272,900
5        50      3,050        152,500
subtotal                      825,700
vat (8%)                       66,056
grand total                   891,756
```

Sample `bill --show` output:

```
meter        kwh     subtotal        vat   grand_total  est_iv
M-000010     102      187,934     15,035       202,969       0
M-000011      82      150,012     12,001       162,013       0
M-000000      78      142,548     11,404       153,952       0
```

Sample `anomaly` output (with `find_stuck` firing on the 4 AM dip):

```
GAPS (0):
SPIKES (0):
STUCK (16):
  M-000006   2026-05-01T08:30:00+07:00  17 consecutive near-zero intervals
```

## Library

```python
from evnmeter.simulator import generate
from evnmeter.derive    import derive
from evnmeter.anomaly   import find_gaps, find_spikes, find_stuck
from evnmeter.billing   import bill_meters
from datetime import datetime, timedelta, timezone

# 1) Synthesise + fold
meters, readings = generate(n_meters=50, n_days=30, seed=42)
intervals = derive(readings, max_gap_minutes=90)

# 2) Bill the month
period_start = datetime(2026, 5, 1, tzinfo=timezone(timedelta(hours=7)))
bills = bill_meters(intervals, period_start, period_start + timedelta(days=30))

# 3) Surface anomalies
gaps   = find_gaps(intervals, min_minutes=120)
spikes = find_spikes(intervals, multiplier=5.0)
stuck  = find_stuck(intervals, min_zero_intervals=12)
```

## Key design decisions

- **Integer `kWh × 100`** throughout. Floats drift; meter readings
  are legally billable so the precision must be exact. Two decimal
  places of resolution matches what EVN's CT-2014 / ECM-7510 meters
  report on the wire.
- **Banker's rounding** on VAT (round-half-to-even), same as
  [`vn-tax-invoice-validator`](../vn-tax-invoice-validator/).
- **Rollover detection by plausibility.** A backward step is treated
  as rollover only if the wrap path is shorter than the backward
  jump *and* the gap covers > 50% of the meter range. Otherwise
  it's a fault and the offending reading is dropped — no negative
  intervals ever leak through.
- **Gap-splitting into 30-min chunks**, not one big bridge interval.
  EVN's natural interval is 30 minutes; a 4-hour gap becomes 8
  estimated intervals with proportionally-distributed kWh. Bills
  that span the gap still get the right total, but ops can see
  exactly which 30-min windows were estimated.
- **`now` is never `datetime.now()`** — all clocks injected by the
  caller. Tests pin time deterministically.
- **Bill rows are sparse.** A meter with zero in-window consumption
  produces no bill — dashboards don't need empty rows.
- **Anomaly detectors are pure functions** of `(intervals, thresholds)` —
  no I/O, no global state, easy to unit-test.

## Quality

```bash
make test       # 85 tests + 5 Hypothesis properties
make type       # mypy --strict
make lint
```

- **85 tests**, 0 failing; 5 Hypothesis properties (total delta
  preserved across resampling, intervals never overlap per meter,
  `grand_total == subtotal + vat` for any kWh, bill is monotonic in
  kWh, combined bill ≥ sum-of-parts under progressive tariff).
- mypy `--strict` clean over 9 source files; ruff clean.
- Multi-stage slim Docker image, non-root `evnmeter` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
