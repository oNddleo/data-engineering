# vn-stock-ticker-pipeline

End-to-end **Vietnamese stock exchange data pipeline** — three-board
directory (HOSE / HNX / UPCoM), 45-ticker registry (VN30 + HNX
leaders + UPCoM leaders), regulator-set pricing rules (price band,
tick size, lot size), OHLC bar aggregation, multi-day rollups
(VWAP, moving averages), and three anomaly detectors (band breach,
volume spike, price gap).

Pure Python 3.10+, zero runtime dependencies, 157 tests including
Hypothesis property tests, `mypy --strict` clean.

## What's in the box

| Module             | Purpose                                          |
| ------------------ | ------------------------------------------------ |
| `vnstock.schema`   | `Exchange`, `Ticker`, `OHLCBar`, `Order`, `OrderKind` |
| `vnstock.exchanges`| 3-exchange directory + trading-rule profiles     |
| `vnstock.tickers`  | VN30 + HNX + UPCoM registries with industry tags |
| `vnstock.pricing`  | `ceiling_floor`, `tick_size`, `is_valid_lot`, `is_within_band` |
| `vnstock.bars`     | `Trade` + `aggregate_bar` (intraday → daily)     |
| `vnstock.aggregator`| `TickerStats`, `moving_average_close`, `volume_weighted_avg_price` |
| `vnstock.anomaly`  | Band-breach, volume-spike, price-gap detectors   |
| `vnstock.simulator`| Seeded OHLC stream with anomaly-injection cohorts |
| `vnstock.io_jsonl` | JSONL codec for every record type                |
| `vnstock.cli`      | `info | exchanges | tickers | band | tick | simulate | summary | anomaly` |

## Quick start

```bash
# Inspect the bundled exchanges with their trading rules
python -m vnstock.cli exchanges

# List the bundled tickers (filter by exchange if you like)
python -m vnstock.cli tickers --exchange HOSE

# Compute today's ceiling/floor for a reference price
python -m vnstock.cli band --reference 50000 --exchange HOSE
# → ceiling 53,500 (+7%), floor 46,500 (−7%), snapped to 100 VND tick

# Tick size at a given price
python -m vnstock.cli tick --price 5000 --exchange HOSE
# → 10 VND (HOSE tier-1: < 10,000 VND)

# Simulate a month of bars and detect anomalies
python -m vnstock.cli simulate --tickers 20 --days 30 --seed 11 \
  --output bars.jsonl
python -m vnstock.cli summary --input bars.jsonl --show 5
python -m vnstock.cli anomaly --input bars.jsonl --show 5
```

```python
from datetime import date
from vnstock import (
    Exchange, OHLCBar,
    ceiling_floor, tick_size, is_within_band,
    find_band_breaches, find_volume_spikes,
)

# Regulator-set price band on HOSE = ±7%
ceiling, floor = ceiling_floor(50_000, Exchange.HOSE)
assert ceiling == 53_500 and floor == 46_500

# Tiered tick on HOSE — 100 VND above 50,000
assert tick_size(75_000, Exchange.HOSE) == 100

# A 7.5% close move on HOSE breaches the band
assert not is_within_band(54_000, 50_000, Exchange.HOSE)
```

## VN exchanges (2025 rules)

| Exchange | Code   | Band   | IPO band | Lot | Tick           |
| -------- | ------ | ------ | -------- | --- | -------------- |
| HOSE     | HOSE   | ±7%    | ±20%     | 100 | 10 / 50 / 100  |
| HNX      | HNX    | ±10%   | ±30%     | 100 | 100 (flat)     |
| UPCoM    | UPCOM  | ±15%   | ±40%     | 100 | 100 (flat)     |

HOSE tick is *price-dependent*:

| Price range (VND)  | Tick (VND) |
| ------------------ | ---------- |
| < 10 000           | 10         |
| 10 000 – 49 950    | 50         |
| ≥ 50 000           | 100        |

## VN30 (Q1 2025)

ACB · BCM · BID · BVH · CTG · FPT · GAS · GVR · HDB · HPG · MBB · MSN ·
MWG · PLX · POW · SAB · SHB · SSB · SSI · STB · TCB · TPB · VCB · VHM ·
VIB · VIC · VJC · VNM · VPB · VRE

Effective from 2025-02-03 per Decision 1/2025/QĐ-SGDCK; rebalanced
quarterly. The bundled set also includes 10 HNX leaders (PVI, PVS,
SHS, MBS, ...) and 5 UPCoM leaders (BSR, ACV, MCH, VEA, QNS).

## Anomaly detection

* **Price-band breach** — a bar whose high > ceiling or low < floor
  for its exchange's band. In healthy markets, the matching engine
  prevents this; surfacing it indicates feed bugs or regulatory events.
* **Volume spike** — bar volume ≥ N× (default 5×) the trailing
  ``window``-day average (default 5 days). Signals news, block trades,
  or potential market manipulation.
* **Price gap** — open ≥ ``min_gap_bps`` (default 500 bps = ±5%) away
  from the previous close. Common on illiquid tickers around earnings.

## Quality gate

```
ruff check src tests          # 0 issues
ruff format --check src tests # 0 diffs
mypy --strict src             # 11 source files clean
pytest                        # 157 tests, all green
```

Property tests verify: tick-size positive, round-to-tick monotonicity,
reference price inside its own band, IPO band wider than normal,
OHLC ordering, VWAP bounded by min/max close.

## License

MIT
