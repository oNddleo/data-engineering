# Changelog

## [0.1.0] — 2026-05-18

### Added
- `ColumnKind` enum with four detected kinds (NUMERIC / STRING /
  CATEGORICAL / DATE).
- `HistogramKind` enum with three construction strategies
  (EQUI_WIDTH / EQUI_DEPTH / MAXDIFF).
- `Bin` frozen-slots dataclass — half-open `[lower, upper)` with
  a count, validation on inverted ranges and negative counts.
- `Histogram` frozen-slots dataclass with `kind`, `bins`, `total_count`,
  cross-validation that bin counts sum to total_count.
- `TopKEntry` with `value`, `count`, and `epsilon` (Space-Saving's
  over-count error bound).
- `NumericStats` — min/max/mean/std + p25/p50/p75/p95/p99.
- `StringStats` — min/max/mean length.
- `ColumnProfile` — top-level result type, sub-profiles dispatched
  on `ColumnKind`. Computed `null_fraction` property.
- `colstats.numeric.WelfordAccumulator` — online mean + variance
  with Welford's algorithm (Knuth TAOCP §4.2.2). Numerically stable
  for shifted-magnitude inputs.
- `colstats.numeric.numeric_stats()` — full NumericStats with
  nearest-rank percentiles (NIST / Hyndman-Fan type 1, using
  `math.ceil(p/100 * n)`).
- `colstats.categorical.SpaceSaving` — Metwally/Agrawal/Abbadi 2005
  top-K algorithm with O(K) space and `epsilon` over-count bound.
  `top_k()` and `cardinality()` helpers (with capped distinct count).
- `colstats.histogram.equi_width()` — equal-width bins between
  min and max; degenerate (all-equal) input collapses to a single
  zero-width bin.
- `colstats.histogram.equi_depth()` — equal-depth bins each holding
  ~ N/B values.
- `colstats.histogram.maxdiff()` — cuts at the (B-1) largest gaps
  between adjacent sorted distinct values (Poosala/Ioannidis 1996).
  Falls back to one-bin-per-distinct-value when distinct count < B.
- `colstats.histogram.reproject()` — re-bins raw values into another
  histogram's bin edges. Clamps out-of-range values to the extremes.
  Required for cross-profile PSI / KS scoring.
- `colstats.profile.collect_profile()` — single entry point.
  Dispatches on `ColumnKind`; null values (empty strings) counted
  toward `n_rows` but excluded from stats.
- `colstats.drift.psi()` — Population Stability Index. Requires
  aligned bin counts; ε-smoothed to avoid `ln(0)`.
- `colstats.drift.ks()` — Kolmogorov-Smirnov max-gap between
  empirical CDFs derived from histograms.
- `colstats.drift.psi_band()` — categorise PSI as stable (< 0.1) /
  minor (< 0.25) / significant (>= 0.25). Standard credit-risk thresholds.
- `colstats.simulator.generate_numeric()` (UNIFORM / GAUSSIAN /
  LOGNORMAL), `generate_categorical()` (Zipf-weighted),
  `generate_string()`, `generate_date()`.
- `colstats.io_jsonl` — type-checked JSONL codec for
  `ColumnProfile` and all sub-records. Rejects bool-as-int and
  other type confusions.
- `colstats.cli` — `colstats info | simulate | profile | drift | summary`.
  `drift` exits **2** on minor/significant PSI band (CI gate).
  `--compared-values` flag re-bins raw values into baseline edges.
- 108 unit tests + 13 Hypothesis properties; mypy `--strict` clean;
  ruff clean; multi-stage slim Docker image.

[0.1.0]: https://github.com/sophie-nguyenthuthuy/data-engineering/releases/tag/column-statistics-collector-v0.1.0
