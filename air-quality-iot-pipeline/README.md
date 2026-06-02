# air-quality-iot-pipeline

VN air-quality monitoring pipeline — **PM2.5 / PM10 / NO2 / SO2 / O3 / CO**
sensor stream → 1h / 8h / 24h window averages → station AQI per
**Quyết định 1459/QĐ-TCMT 2019** + concentration breakpoints from
**QCVN 05:2023/BTNMT** → health-warning alerts split by general public
vs sensitive-group cohorts.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Validates** sensor readings at the boundary — tz-aware
   timestamps, non-negative concentrations, VN-bounding-box lat/lon
   (8°N – 24°N, 102°E – 110°E), `quality ∈ {GOOD, CALIBRATING, STALE}`.
2. **Aggregates** raw readings into fixed window averages (1h / 8h
   / 24h) aligned to the **VN_TZ epoch** (a 24-h bar starts at
   `00:00 VN`, not UTC midnight). CALIBRATING / STALE readings are
   excluded from the mean — calibration-drift alerts belong on a
   separate channel.
3. **Computes per-pollutant AQI** via piecewise-linear interpolation
   on the QĐ 1459 breakpoint table (different cuts for each
   pollutant); composes **station AQI** as `max(per-pollutant)` —
   the worst pollutant drives the public-health message.
4. **Emits alerts** at two cohort tiers: PUBLIC (general public,
   default threshold `UNHEALTHY_SENSITIVE`) and SENSITIVE (children,
   elderly, respiratory cohort, escalated one band earlier).

## VN AQI bands per QĐ 1459

| Band                              | AQI range | Color  | Public message                                  |
| --------------------------------- | --------- | ------ | ----------------------------------------------- |
| Good (Tốt)                        | 0 – 50    | green  | no alert                                        |
| Moderate (Trung bình)             | 51 – 100  | yellow | no alert (sensitive groups: watch)              |
| Unhealthy for Sensitive Groups    | 101 – 150 | orange | sensitive groups limit outdoor time             |
| Unhealthy (Xấu)                   | 151 – 200 | red    | everyone limit outdoor time                     |
| Very Unhealthy (Rất xấu)          | 201 – 300 | purple | avoid outdoor activity; close windows           |
| Hazardous (Nguy hại)              | 301 – 500 | maroon | stay indoors; air purifiers; N95 if outside     |

## VN networks supported

| Network               | Cadence | Stations | Calibration               |
| --------------------- | ------- | -------- | ------------------------- |
| State (Bộ TNMT)       | 15 min  | ~30      | Regulated, low drift      |
| PAM Air (private)     | 5 min   | ~150     | Higher drift, denser data |

The `StationKind` enum distinguishes them so downstream callers can
weight readings appropriately.

## Components

| Module              | Role                                                                  |
| ------------------- | --------------------------------------------------------------------- |
| `aqipipe.schema`    | `Station`, `Pollutant`, `Reading`, `WindowAverage`, `StationKind`     |
| `aqipipe.qcvn`      | `aqi_for(pollutant, value_x10)`, `station_aqi`, `AQIBand`, `band_for_aqi` |
| `aqipipe.aggregate` | `aggregate(readings, window)` + `latest_per_station`                  |
| `aqipipe.alerts`    | `find_public_alerts`, `find_sensitive_alerts`, `band_distribution`    |
| `aqipipe.simulator` | Seeded synthetic stations + readings with VN-realistic baselines       |
| `aqipipe.io_jsonl`  | Type-checked JSONL codec for all record types                          |
| `aqipipe.cli`       | `aqipipe info \| simulate \| aggregate \| aqi \| alerts \| quote \| summary` |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
aqipipe info
aqipipe simulate  --stations 10 --hours 24 --seed 7 --out-dir ./raw
aqipipe aggregate --input ./raw/readings.jsonl --window 1h --output ./avg_1h.jsonl
aqipipe aqi       --input ./avg_1h.jsonl --n 10
aqipipe alerts    --input ./avg_1h.jsonl --min-band UNHEALTHY_SENSITIVE --show 5
aqipipe quote     PM25 500              # 50 µg/m³ → AQI 100 (MODERATE boundary)
aqipipe summary   --input ./raw/readings.jsonl
```

Sample `aqi` output for 8 stations / 24h:

```
station      aqi band                   dominant
AQ-00007     102 UNHEALTHY_SENSITIVE    PM25
AQ-00001      92 MODERATE               PM25
AQ-00005      92 MODERATE               PM25
AQ-00003      75 MODERATE               PM25
AQ-00002      47 GOOD                   PM10
```

Sample `alerts` output:

```
Band distribution (8 stations):
  GOOD                       2
  MODERATE                   5
  UNHEALTHY_SENSITIVE        1
  UNHEALTHY                  0

PUBLIC alerts (1):
  AQ-00007   AQI 102 (UNHEALTHY_SENSITIVE) — sensitive groups should limit outdoor time [dominant: PM25]

SENSITIVE-GROUP alerts (6):
  AQ-00007   AQI 102 (UNHEALTHY_SENSITIVE)
  AQ-00001   AQI  92 (MODERATE)
  ...
```

Sample `quote PM25 1500` (= 150 µg/m³, top of UNHEALTHY band):

```json
{
  "pollutant": "PM25",
  "value_x10": 1500,
  "aqi": 200,
  "band": "UNHEALTHY"
}
```

## Library

```python
from aqipipe.simulator import generate
from aqipipe.aggregate import aggregate, latest_per_station
from aqipipe.qcvn      import station_aqi
from aqipipe.alerts    import find_public_alerts, find_sensitive_alerts
from datetime          import datetime, timezone, timedelta

VN_TZ = timezone(timedelta(hours=7))

stations, readings = generate(n_stations=20, n_hours=48, seed=42)
averages = aggregate(readings, window="1h")
latest = latest_per_station(averages)
aqis = {
    sid: station_aqi(sid, {p: w.value_x10 for p, w in polls.items()})
    for sid, polls in latest.items()
    if polls
}

now = datetime(2026, 5, 17, 9, 0, tzinfo=VN_TZ)
for alert in find_public_alerts(aqis, now)[:5]:
    print(alert.station_id, alert.aqi, alert.detail)
```

## Key design decisions

- **Integer storage everywhere** — `value × 10` matches every VN AQI
  publication and avoids the float-drift bug that haunts environmental
  databases.
- **VN-specific concentration breakpoints**, not US EPA. QĐ 1459 has
  similar bands but tighter PM2.5 cuts (top-of-MODERATE at 50 µg/m³,
  not 35.4 µg/m³ like the US) reflecting WHO 2021 guidance.
- **VN_TZ-aligned window boundaries.** A 24-h bar starts at
  `00:00 VN`, not UTC midnight — the recurring bug in non-VN-aware
  environmental tools.
- **CALIBRATING and STALE readings excluded from the mean.** A drifting
  sensor that reports 99% lower than reality would skew a station to
  a falsely-Good band. Drift is a separate alert channel.
- **Station AQI is the max over pollutants**, with `dominant_pollutant`
  recording which one drove the score. This matches QĐ 1459 + every
  other AQI methodology globally — geometric means would mask hot
  pollutants.
- **Two cohort tiers in alerts.** Sensitive groups (children, elderly,
  respiratory cohorts) react one band earlier — VN-MoH guidance
  consistently escalates them, so the toolkit has two dedicated
  detectors instead of forcing callers to re-band.
- **Tunable `min_band`** on public alerts. Production dashboards pick
  their own threshold; the default `UNHEALTHY_SENSITIVE` matches what
  VN-MoH sends to the public-warning channels.

## Quality

```bash
make test       # 83 tests + 6 Hypothesis properties
make type       # mypy --strict
make lint
```

- **83 tests**, 0 failing; 6 Hypothesis properties (AQI is always
  in `[0, 500]`, the `band` field is consistent with `band_for_aqi(aqi)`,
  AQI is monotonic non-decreasing in concentration per pollutant,
  station AQI ≥ each pollutant contribution, station AQI equals
  the max contribution, `band_for_aqi` is total over `[0, 500]`).
- mypy `--strict` clean over 8 source files; ruff clean.
- Multi-stage slim Docker image, non-root `aqipipe` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
