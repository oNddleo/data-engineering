# vietcombank-bidv-techcombank-fx-rate-aggregator

Aggregate tỷ giá ngoại tệ từ top-10 NHTM Việt Nam (Vietcombank,
BIDV, Techcombank, MB, VPBank, ACB, VietinBank, Agribank, HDBank,
TPBank), normalise về một schema chung, build time-series
warehouse, phát hiện spread + outlier anomaly so sánh chéo giữa
các bank.

[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](#)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## What it does

1. **Parse** từng bank theo định dạng riêng:
   - **Vietcombank XML** — `<ExrateList>` feed với `<Exrate>` elements
   - **BIDV HTML** — bảng `<table>` rows với amount có dấu phẩy nghìn
   - **Techcombank JSON** — REST API shape `{data: {datetime, rates: [...]}}`
   - **Generic CSV** — bất kỳ bank nào publish được CSV
     `currency,buy_cash,buy_transfer,sell`
2. **Normalise** thành `Quote` (integer VND, tz-aware UTC+7), tách
   `buy_cash` / `buy_transfer` / `sell` riêng biệt.
3. **Store** vào in-memory TSDB (`TimeSeriesStore`) sorted by
   timestamp, hỗ trợ `latest()`, `history()`, `as_of()`.
4. **Analyze** cross-bank cho 1 currency tại 1 thời điểm:
   - Tính peer median (`buy_transfer`, `sell`, bid-ask spread).
   - Detect 4 anomaly kinds:

| Alert kind        | Trigger                                                        | Severity |
| ----------------- | -------------------------------------------------------------- | -------- |
| `INVERTED_SPREAD` | `sell < buy_transfer` (broken row)                             | CRIT     |
| `BUY_OUTLIER`     | `|buy − peer_median_buy| ≥ outlier_pct` (default 1 %)         | WARN     |
| `SELL_OUTLIER`    | `|sell − peer_median_sell| ≥ outlier_pct`                     | WARN     |
| `STALE_QUOTE`     | bank's latest quote is older than `stale_threshold_min`        | INFO     |

Ordering rules:

* `INVERTED_SPREAD` **short-circuits** outlier detection — once the
  row is structurally broken, peer comparison isn't meaningful.
* Outlier rule requires ≥ 3 banks (otherwise the median is too
  thin to be useful).

## Components

| Module               | Role                                                                  |
| -------------------- | --------------------------------------------------------------------- |
| `fxagg.schema`       | `Bank`, `Currency`, `Quote`, `Snapshot`, `VN_TZ`                      |
| `fxagg.parsers`      | 4 vendor parsers + `ParseError`                                        |
| `fxagg.storage`      | `TimeSeriesStore` + JSONL `dump_quotes`/`load_quotes`/`save_store`    |
| `fxagg.spread`       | `analyze()` + `Alert`/`AlertKind`/`Severity`/`CurrencyAnalysis`       |
| `fxagg.simulator`    | seeded synthetic generator + anomaly injection                        |
| `fxagg.cli`          | `fxagg info | parse | analyze | simulate`                             |

## Install

```bash
pip install -e ".[dev]"
```

Python 3.10+. **Zero runtime dependencies.**

## CLI

```bash
fxagg info

# 1) Parse a vendor payload to verify the parser.
fxagg parse --format vcb-xml   --file vcb-2026-05-14.xml
fxagg parse --format bidv-html --file bidv-2026-05-14.html --quoted-at 2026-05-14T09:30:00+07:00
fxagg parse --format tcb-json  --file tcb-2026-05-14.json

# 2) Generate a synthetic store (5 banks × 3 currencies × 3 snapshots).
fxagg simulate \
  --banks VCB,BIDV,TCB,MB,VPB \
  --currencies USD,EUR,JPY \
  --snapshots 3 \
  --seed 42 \
  --inject outlier_buy,inverted \
  --output store.jsonl

# 3) Run cross-bank analysis at the latest timestamp.
fxagg analyze --store store.jsonl --currency USD --outlier-pct 1.0
```

Sample analysis output (6 banks, anomalies injected):

```
=== USD cross-bank analysis @ 2026-05-14T09:10:00+07:00 ===
banks: 6   median buy=24,917   median sell=25,097   median spread=0.78%
  ACB   buy=25,250  sell=24,750  spread=-2.00%  ts=2026-05-14T09:10:00+07:00
  BIDV  buy=24,886  sell=25,113  spread=0.91%   ts=2026-05-14T09:10:00+07:00
  MB    buy=24,917  sell=25,082  spread=0.66%   ts=2026-05-14T09:10:00+07:00
  TCB   buy=24,917  sell=25,082  spread=0.66%   ts=2026-05-14T09:10:00+07:00
  VCB   buy=26,250  sell=26,750  spread=1.89%   ts=2026-05-14T09:10:00+07:00
  VPB   buy=24,881  sell=25,118  spread=0.95%   ts=2026-05-14T09:10:00+07:00

Alerts:
  [WARN] BUY_OUTLIER  VCB: buy_transfer=26,250 vs peer median 24,917 (+5.35%)
  [CRIT] INVERTED_SPREAD ACB: sell=24,750 < buy_transfer=25,250 — broken row
  [WARN] SELL_OUTLIER VCB: sell=26,750 vs peer median 25,097 (+6.59%)
```

## Library

```python
from fxagg import (
    parse_vietcombank_xml, parse_bidv_html, parse_techcombank_json,
    TimeSeriesStore, Currency, analyze,
)

store = TimeSeriesStore()
store.append_snapshot(parse_vietcombank_xml(open("vcb.xml").read()))
store.append_snapshot(parse_techcombank_json(open("tcb.json").read()))

usd_snapshot = store.all_latest(Currency.USD)
analysis = analyze(usd_snapshot, outlier_pct=1.0)
for alert in analysis.alerts:
    print(alert.severity.value, alert.kind.value, alert.bank.value, alert.detail)
```

## Production deployment

Each piece is intentionally narrow so the production version can
swap implementations:

* **Scraping** — wrap an `aiohttp`/`httpx` client around the parsers.
  HTTP fetch + retry + back-off lives outside this package; the
  parsers stay pure.
* **Storage** — replace `TimeSeriesStore` with InfluxDB or
  TimescaleDB. The four read shapes (`latest`, `history`,
  `all_latest`, `as_of`) map 1:1 to standard TSDB queries.
* **Alerting** — pipe `analysis.alerts` to PagerDuty for
  `INVERTED_SPREAD`, Slack for outliers, the data warehouse for
  `STALE_QUOTE`.

## Quality

```bash
make test       # 88 tests, 4 Hypothesis properties
make type       # mypy --strict
make lint
```

- **88 tests** including 4 Hypothesis properties (Quote round-trips
  through JSONL for any int amounts; any inverted-spread input
  always fires; TimeSeriesStore append is idempotent; history stays
  sorted regardless of insertion order).
- mypy `--strict` clean over 7 source files; ruff clean.
- Multi-stage slim Docker image, non-root `fxagg` user.
- Python 3.10 / 3.11 / 3.12 CI matrix.
- **Zero runtime dependencies.**

## License

MIT — see [LICENSE](LICENSE).
