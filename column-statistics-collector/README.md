# column-statistics-collector

Single-pass column profiler — null fraction, distinct cardinality
(with cap), top-K most-frequent values (via **Space-Saving**),
three histogram strategies (**equi-width / equi-depth / MaxDiff**),
numerically-stable **Welford** mean+std, and **PSI / KS** drift
scoring between two profiles. Foundational DE primitive used in
query optimization (cardinality estimation), data quality monitoring,
and partitioning decisions.

Pure-Python, zero dependencies.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Collects per-column profile** in one pass — null fraction,
   distinct cardinality (capped at 10 000 by default), and (depending
   on declared kind) numeric stats, string-length stats, top-K, and
   a histogram.
2. **Computes numeric stats** with **Welford's online algorithm**
   for mean + variance — numerically stable for shifted-magnitude
   inputs (no catastrophic cancellation). Percentiles via
   nearest-rank (NIST / Hyndman-Fan type 1).
3. **Computes top-K** with the **Space-Saving** algorithm
   (Metwally / Agrawal / Abbadi 2005) — O(K) space, guaranteed
   error bound exposed as the ``epsilon`` field on each entry.
4. **Builds histograms** in three flavours: equi-width (simplest),
   equi-depth (textbook query-optimizer choice), MaxDiff (cuts at
   the biggest gaps — best for skewed distributions per Poosala /
   Ioannidis 1996).
5. **Scores drift** between two profiles using **PSI** (Population
   Stability Index — banking / credit-risk default) and **KS** (max
   gap between empirical CDFs). Includes a ``reproject()`` helper
   that re-bins raw compared values into a baseline histogram's
   edges — the standard PSI workflow.

## ColumnKind taxonomy

| Kind          | Examples                          | Captured                                          |
| ------------- | --------------------------------- | ------------------------------------------------- |
| `NUMERIC`     | amount, qty, lat                  | min/max/mean/std + percentiles + histogram        |
| `CATEGORICAL` | country, status, payment_method   | top-K + cardinality                               |
| `STRING`      | name, url, free-text              | length stats + top-K + cardinality                |
| `DATE`        | created_at, dob                   | numeric stats over day-offsets + histogram        |

## Drift bands (standard PSI thresholds)

| PSI score    | Band         | Interpretation                                        |
| ------------ | ------------ | ----------------------------------------------------- |
| < 0.10       | stable       | No meaningful drift; model can stay deployed.         |
| 0.10 – 0.25  | minor        | Distribution shift — review but no immediate action.  |
| > 0.25       | significant  | Material drift — retrain / re-derive thresholds.      |

`drift` CLI exits **0** for *stable*, **2** for *minor* or
*significant* — suitable as a CI / Airflow gate.

## Components

| Module             | Role                                                                |
| ------------------ | ------------------------------------------------------------------- |
| `colstats.schema`  | `ColumnProfile`, `NumericStats`, `StringStats`, `Histogram`, `Bin`, `TopKEntry` |
| `colstats.numeric` | Welford accumulator + nearest-rank percentiles                       |
| `colstats.categorical` | Space-Saving top-K + capped cardinality                         |
| `colstats.histogram`   | `equi_width` / `equi_depth` / `maxdiff` / `reproject`           |
| `colstats.profile` | `collect_profile()` — dispatches on `ColumnKind`                    |
| `colstats.drift`   | `psi` + `ks` + `psi_band` thresholds                                |
| `colstats.simulator` | Seeded NUMERIC / CATEGORICAL / STRING / DATE generators           |
| `colstats.io_jsonl`| Type-checked JSONL codec                                            |
| `colstats.cli`     | `colstats info \| simulate \| profile \| drift \| summary`          |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
colstats info
colstats simulate  --kind NUMERIC --shape GAUSSIAN --mean 100 --std 20 --rows 1000 --seed 7 --output col.txt
colstats profile   --input col.txt --kind NUMERIC --name amount --show --output profile.json
colstats drift     --baseline profile.json --compared-values drifted_col.txt
colstats summary   --input col.txt --kind NUMERIC
```

Sample `profile --show` on a Gaussian(100, 20) sample:

```
column:           amount
kind:             NUMERIC
n_rows:           1000
n_non_null:       1000
null_fraction:    0.0%
cardinality:      1000
numeric:          min=39.58 max=170.6 mean=100.2 std=19.75
percentiles:      p25=87.15 p50=100.3 p75=113.1 p95=131.7 p99=143.7
histogram:        EQUI_DEPTH (10 bins)
```

Sample `profile --show` on a categorical Zipf(α=1.5, K=5):

```
column:           category
kind:             CATEGORICAL
n_rows:           1000
n_non_null:       1000
null_fraction:    0.0%
cardinality:      5
top_k:
  cat_0                       575
  cat_1                       165
  cat_2                       117
  cat_3                        89
  cat_4                        54
```

Sample `drift` on a 30-unit-shifted Gaussian:

```
PSI: 2.0277  (significant)
KS:  0.5580
```

(exit code **2**, ready for shell scripting / Airflow.)

## Library

```python
from colstats.profile import collect_profile
from colstats.drift   import psi, ks, psi_band
from colstats.histogram import reproject
from colstats.schema  import ColumnKind

baseline = collect_profile("amount", baseline_values, kind=ColumnKind.NUMERIC)
print(baseline.numeric)           # NumericStats(min=…, max=…, mean=…, std=…, ...)
print(baseline.histogram.n_bins)  # 10
print(baseline.top_k[:3])         # for categorical/string columns

# Drift detection — re-bin compared values into baseline's histogram edges.
from dataclasses import replace
compared_hist = reproject(compared_values, baseline.histogram)
compared = replace(baseline,
    n_rows=len(compared_values), n_non_null=len(compared_values),
    histogram=compared_hist)

print(f"PSI = {psi(baseline, compared):.3f} ({psi_band(psi(baseline, compared))})")
print(f"KS  = {ks(baseline, compared):.3f}")
```

## Key design decisions

- **Welford for std-dev.** Single-pass, O(1) memory, numerically
  stable. Naive sum-of-squares loses precision when values are
  shifted (e.g. timestamps in seconds-since-epoch). Property test
  verifies match with `statistics.stdev` on shifted-magnitude inputs.
- **Space-Saving for top-K.** O(K) memory, guaranteed
  ``count ≥ true_count ≥ count - epsilon`` per entry. Real DE
  workloads (cardinality > K, often >> K) make exact counting
  unfeasible; Space-Saving is the standard CS-textbook answer.
- **Three histograms, not one.** Equi-width is fine for uniform
  distributions; equi-depth is the default because it bounds
  per-bin frequency (which is what query optimizers need for
  cardinality estimation); MaxDiff wins when the distribution is
  obviously skewed (e.g. log-normal revenue, Zipf categorical).
- **Reproject before drift.** PSI and KS only make sense when both
  histograms share bin **edges**. Two equi-depth profiles built
  from different data have different edges → PSI = 0 even with
  obvious drift. `reproject()` solves this by re-binning raw values
  into the baseline's edges (the standard PSI workflow).
- **Capped cardinality.** Exact distinct-count is unbounded memory.
  We cap at 10 000 by default and flag `cardinality_capped` —
  consumers know to treat the value as "many" rather than precise.
- **CI exit codes:** `colstats drift` exits **0** on stable PSI,
  **2** on minor or significant.

## Quality

```bash
make test       # 108 tests + 13 Hypothesis properties
make type       # mypy --strict
make lint
```

- **108 tests**, 0 failing; 13 Hypothesis properties (Welford
  matches stdlib stdev within float precision; Welford mean
  matches naïve sum÷n; all three histograms preserve total_count;
  reproject preserves count + bin edges; top-K returns at most K;
  cardinality ≤ distinct input; SpaceSaving n_seen matches add()
  calls; numeric profile min/max match input min/max; top-K counts
  sum ≤ non_null; PSI(p, p) = 0; PSI always ≥ 0).
- mypy `--strict` clean over 10 source files; ruff clean.
- Multi-stage slim Docker image, non-root `colstats` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
