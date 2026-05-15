# vn-stock-market-tick-pipeline

VN equity tick-data pipeline covering the three Vietnamese exchanges
(**HOSE**, **HNX**, **UPCoM**). Ticks → OHLCV bars at standard
intervals (1m / 5m / 15m / 1h / 1d) → technical indicators (SMA,
EMA, RSI, MACD, Bollinger) + circuit-breaker anomaly detection +
market-cap-weighted indices (VN-Index, VN30, HNX-Index).

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Validates** `Tick` records at the boundary — tz-aware
   timestamps, positive price + volume, side ∈ {`B`, `S`}, ASCII
   uppercase ticker codes.
2. **Resamples** the tick stream into left-closed OHLCV bars whose
   boundaries are aligned to the `VN_TZ` epoch (a 5-minute bar
   always starts on `:00 / :05 / :10`, a 1-day bar on `00:00 VN_TZ`).
3. **Computes indicators** over the close-price series — SMA, EMA,
   Wilder RSI, MACD (12/26/9), Bollinger Bands (20-period × 2σ).
4. **Detects anomalies**: circuit-breaker hits (HOSE ±7%, HNX ±10%,
   UPCoM ±15% off prev-day close), unusual volume (3σ vs trailing-N
   history).
5. **Computes indices** as market-cap-weighted sums — VN-Index (all
   HOSE), VN30 (caller-supplied 30 codes), HNX-Index (all HNX).

## VN exchange rules baked in

| Exchange | Daily band | Lot size | Index    |
| -------- | ---------- | -------- | -------- |
| HOSE     | ±7%        | 100      | VN-Index, VN30 |
| HNX      | ±10%       | 100      | HNX-Index      |
| UPCoM    | ±15%       | 100      | UPCoM-Index    |

Trading sessions (in `VN_TZ` = `UTC+7`):

* **Morning**: 09:00 — 11:30
* **Afternoon**: 13:00 — 14:45 (HOSE/HNX close 14:30, ATC 14:30 — 14:45)

`is_in_session(ts)` accepts any tz-aware timestamp and checks both
windows after converting to `VN_TZ` — so a UTC 02:30 timestamp is
correctly identified as in-session (09:30 VN).

## Components

| Module               | Role                                                                  |
| -------------------- | --------------------------------------------------------------------- |
| `vntick.schema`      | `Exchange`, `Symbol`, `Tick`, `OHLCVBar`, `ceiling_price`, `floor_price`, `is_in_session` |
| `vntick.resampler`   | `resample(ticks, interval) → list[OHLCVBar]` at 1m/5m/15m/1h/1d        |
| `vntick.indicators`  | `sma`, `ema`, `rsi` (Wilder), `macd`, `bollinger` — pure float math   |
| `vntick.anomaly`     | `find_circuit_breaker_hits`, `find_unusual_volume`                    |
| `vntick.index`       | `vn_index`, `vn30_index`, `hnx_index`, `compute_index`                |
| `vntick.simulator`   | Seeded synthetic ticks for 11 real VN blue-chips (VIC, VHM, HPG, VCB, …)|
| `vntick.io_jsonl`    | Type-checked JSONL codec for symbols / ticks / bars                    |
| `vntick.cli`         | `vntick info \| simulate \| resample \| indicators \| anomalies \| index \| summary` |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
vntick info
vntick simulate   --ticks-per-symbol 200 --seed 7 --ceiling VIC,HPG --out-dir ./raw
vntick resample   --input ./raw/ticks.jsonl --interval 5m --output ./bars_5m.jsonl
vntick indicators --bars ./bars_5m.jsonl --code VCB --sma 20 --ema 20 --rsi 14
vntick anomalies  --bars ./bars_5m.jsonl --symbols ./raw/symbols.jsonl \
                  --previous-close ./raw/previous_close.json
vntick index      --bars ./bars_5m.jsonl --symbols ./raw/symbols.jsonl
vntick summary    --input ./raw/ticks.jsonl
```

Sample `indicators` output:

```
bar_start                     close       sma       ema    rsi
2026-05-04T09:00:00+07:00     89535        --        --     --
2026-05-04T09:20:00+07:00     94695   93458.8   93458.8     --
2026-05-04T09:25:00+07:00     94695   94490.8   93870.9     --
2026-05-04T09:30:00+07:00     94695   94695.0   94145.6   84.2
```

Sample `anomalies` output:

```
CIRCUIT-BREAKER HITS (79):
  ACB    CEILING_HIT    2026-05-04T09:35:00+07:00 high=26510 hit ceiling=26510 (prev close=24100, HNX)
  FPT    FLOOR_HIT      2026-05-04T09:20:00+07:00 low=115320 hit floor=115320 (prev close=124000, HOSE)
```

Sample `index` output:

```json
{
  "vn_index_total_cap_vnd": 1532867700000000,
  "vn30_total_cap_vnd": 1532867700000000,
  "vn30_codes": ["FPT", "HPG", "MSN", "MWG", "VCB", "VHM", "VIC", "VNM"]
}
```

## Library

```python
from vntick.simulator   import generate
from vntick.resampler   import resample
from vntick.indicators  import sma, rsi, macd, bollinger
from vntick.anomaly     import find_circuit_breaker_hits
from vntick.index       import vn30_index

symbols, ticks, prev_close = generate(n_ticks_per_symbol=300, seed=42)
bars = resample(ticks, interval="5m")

vcb_bars = [b for b in bars if b.code == "VCB"]
sma20    = sma(vcb_bars, period=20)
rsi14    = rsi(vcb_bars, period=14)
macd_pts = macd(vcb_bars, fast=12, slow=26, signal=9)
bb       = bollinger(vcb_bars, period=20, n_std=2.0)

exchanges = {s.code: s.exchange for s in symbols}
hits = find_circuit_breaker_hits(bars, prev_close, exchanges)

last_prices = {b.code: b.close_vnd for b in bars}  # late wins
vn30 = vn30_index(
    last_prices,
    {s.code: s for s in symbols},
    {"VIC", "VHM", "HPG", "VCB", "VNM", "FPT", "MSN", "MWG"},
)
```

## Key design decisions

- **Integer VND**, no `Decimal`, no `float` drift. VN prices trade
  at whole-dong granularity, so `int` is the natural type — and
  joins between tick, indicator, and index outputs stay exact.
- **Rating × 100 schema convention** (matches every other repo in
  this catalogue: `seller-performance-data-mart`,
  `shopee-product-scraper-warehouse`, `review-sentiment-vietnamese`).
- **Bars are sparse.** A 5-minute bucket with zero ticks is omitted
  from the output, so the bar stream is proportional to actual
  trading activity — not to `n_symbols × n_minutes`.
- **`is_in_session` is tz-aware.** Accepts any timezone, converts
  to `VN_TZ`, then checks both windows. UTC inputs work correctly.
- **Halted-symbol tolerance.** A symbol present in the index
  universe but missing from `last_prices` contributes 0 (matches
  the official methodology of substituting the last known print).
- **`unusual_volume` has a min-history floor.** Symbols with fewer
  than 5 historical days are skipped — z-score on 2 observations
  is meaningless and would generate alerts for every IPO.
- **Wilder RSI**, not the naive ratio. The first usable index is
  `period`, not `period - 1`, because Wilder's averaging needs
  one extra bar to seed.

## Quality

```bash
make test       # 93 tests + 5 Hypothesis properties
make type       # mypy --strict
make lint
```

- **93 tests**, 0 failing; 5 Hypothesis properties (OHLC bar
  invariants always hold, total volume / trade-count preserved
  across resampling, SMA bounded by window min/max, Bollinger
  upper ≥ middle ≥ lower for any input).
- mypy `--strict` clean over 9 source files; ruff clean.
- Multi-stage slim Docker image, non-root `vntick` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
